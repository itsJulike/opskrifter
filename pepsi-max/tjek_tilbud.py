#!/usr/bin/env python3
"""Find Pepsi Max på dåse i tilbudsaviserne (eTilbudsavis/Tjek) og regn stykprisen ud.

Skriver:
  pepsi-max/OVERSIGT.md        – overblik sorteret efter pris pr. dåse
  pepsi-max/pepsi-max.ics      – kalender, der kan abonneres på
  pepsi-max/data/tilbud.json   – alle tilbud, der er set (historik)
  pepsi-max/data/nye.md        – kun når der er nye tilbud under alarmgrænsen (bruges til alarmen,
                                 sammen med data/nye_titel.txt; begge committes ikke)

Kun standardbiblioteket bruges, så scriptet kan køre direkte i GitHub Actions.
"""

import json
import re
import sys
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

MAPPE = Path(__file__).resolve().parent
DATA = MAPPE / "data"
TZ = ZoneInfo("Europe/Copenhagen")
API = "https://squid-api.tjek.com/v2/offers/search"
AVIS_LINK = "https://etilbudsavis.dk/"

UGEDAGE = ["man", "tir", "ons", "tor", "fre", "lør", "søn"]

# "24x33 cl", "24 x 0,33 l", "24 X 33 CL"
PAKKE_RE = re.compile(r"(\d{1,2})\s*[x×]\s*(\d+(?:[.,]\d+)?)\s*(cl|l|liter)\b", re.I)
DAASE_RE = re.compile(r"\b(ds|dåse|dåser)\b", re.I)
FLASKE_RE = re.compile(r"\b(pet|fl|flaske|flasker|plast)\b", re.I)
MAX_RE = re.compile(r"ma(?:x|ks)\.?\s*(\d+)\s*(rammer|ramme|pakker|pakke|ks|kasser|stk)\.?", re.I)


# ---------------------------------------------------------------- hent data

def hent(config):
    pos = config["position"]
    alle = {}
    for ord_ in config["soegeord"]:
        offset = 0
        while True:
            params = {
                "query": ord_,
                "r_lat": pos["lat"],
                "r_lng": pos["lng"],
                "r_radius": pos["radius_meter"],
                "limit": 100,
                "offset": offset,
            }
            url = API + "?" + urllib.parse.urlencode(params)
            req = urllib.request.Request(url, headers={"Accept": "application/json",
                                                       "User-Agent": "pepsi-max-tilbud/1.0"})
            with urllib.request.urlopen(req, timeout=30) as svar:
                side = json.load(svar)
            for o in side:
                alle[o["id"]] = o
            if len(side) < 100:
                break
            offset += 100
    return list(alle.values())


# ---------------------------------------------------------------- fortolkning

def til_cl(tal, enhed):
    v = float(tal.replace(",", "."))
    return round(v * 100) if enhed.lower() in ("l", "liter") else round(v)


def lokal_dato(iso):
    return datetime.strptime(iso, "%Y-%m-%dT%H:%M:%S%z").astimezone(TZ).date()


def fortolk(o, config):
    """Returnér et tilbud som dict, eller None hvis det slet ikke handler om Pepsi."""
    overskrift = o.get("heading") or ""
    beskrivelse = o.get("description") or ""
    tekst = f"{overskrift} {beskrivelse}"
    lav = tekst.lower()
    if "pepsi" not in lav:
        return None

    # Er det Pepsi Max?
    if "pepsi max" in lav:
        max_status = "ja"
    elif "flere varianter" in lav:
        max_status = "måske"   # "Pepsi eller Faxe Kondi – flere varianter"
    else:
        max_status = "nej"

    # Find den del af beskrivelsen, der handler om Pepsi (tilbud kan dække flere varer)
    match = list(PAKKE_RE.finditer(beskrivelse))
    antal = stoerrelse = None
    afsnit = tekst
    if match:
        dele = []
        for i, m in enumerate(match):
            slut = match[i + 1].start() if i + 1 < len(match) else len(beskrivelse)
            dele.append((m, beskrivelse[m.start():slut]))
        valgt = next((d for d in dele if "pepsi" in d[1].lower()), None)
        if valgt is None:
            # Pepsi står kun i overskriften; brug pakningen hvis der kun er én slags
            slags = {(m.group(1), til_cl(m.group(2), m.group(3))) for m, _ in dele}
            if len(slags) == 1:
                valgt = dele[0]
        if valgt:
            m, afsnit = valgt
            antal = int(m.group(1))
            stoerrelse = til_cl(m.group(2), m.group(3))
            afsnit = afsnit + " " + overskrift

    q = o.get("quantity") or {}
    if antal is None:
        stk = (q.get("pieces") or {})
        if stk.get("from") and stk.get("from") == stk.get("to"):
            antal = int(stk["from"])
    if stoerrelse is None:
        s = q.get("size") or {}
        faktor = ((q.get("unit") or {}).get("si") or {}).get("factor")
        si = ((q.get("unit") or {}).get("si") or {}).get("symbol")
        if s.get("from") and s.get("from") == s.get("to") and si == "l" and faktor:
            stoerrelse = round(s["from"] * faktor * 100)

    # Dåse eller flaske?
    if FLASKE_RE.search(afsnit):
        beholder = "flaske"
    elif DAASE_RE.search(afsnit):
        beholder = "dåse"
    else:
        beholder = "ikke angivet"

    pris = float(o["pricing"]["price"])
    dealer = o.get("dealer") or {}
    butik = (o.get("branding") or {}).get("name") or dealer.get("name") or "?"
    markeder = [m.get("country_code") for m in dealer.get("markets") or []]
    graense = butik in config["graensebutikker"] or "DE" in markeder

    noter = []
    m = MAX_RE.search(tekst)
    if m:
        noter.append(f"max {m.group(1)} {m.group(2).lower()}")
    if "afhentningspris" in lav:
        noter.append("afhentningspris")
    if "medlem" in lav:
        noter.append("medlemspris")
    if "+ pant" in lav or "+pant" in lav or "ekskl. embl" in lav:
        noter.append("+ pant")
    if "ingen pant" in lav:
        noter.append("ingen pant")
    if max_status == "måske":
        noter.append("Pepsi, flere varianter")

    return {
        "id": o["id"],
        "butik": butik,
        "overskrift": overskrift.strip(),
        "beskrivelse": " ".join(beskrivelse.split()),
        "pris": pris,
        "antal": antal,
        "stoerrelse_cl": stoerrelse,
        "pr_daase": round(pris / antal, 2) if antal else None,
        "beholder": beholder,
        "pepsi_max": max_status,
        "graensehandel": graense,
        "fra": lokal_dato(o["run_from"]).isoformat(),
        "til": lokal_dato(o["run_till"]).isoformat(),
        "side": o.get("catalog_page"),
        "katalog_id": o.get("catalog_id"),
        "billede": (o.get("images") or {}).get("view"),
        "noter": noter,
    }


def relevant(t, config):
    """Pepsi Max-dåser i multipak."""
    if t is None or t["pepsi_max"] == "nej":
        return False
    if t["pepsi_max"] == "måske" and not config["medtag_pepsi_flere_varianter"]:
        return False
    if t["beholder"] == "flaske":
        return False
    if t["stoerrelse_cl"] not in config["daase_stoerrelse_cl"]:
        return False
    return bool(t["antal"]) and t["antal"] >= config["min_antal_i_pakke"]


# ---------------------------------------------------------------- formattering

def kr(v):
    return f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def kort_dato(iso):
    d = date.fromisoformat(iso)
    return f"{UGEDAGE[d.weekday()]} {d.day}/{d.month}"


def periode(t):
    return f"{kort_dato(t['fra'])} – {kort_dato(t['til'])}"


def beholder_tekst(t):
    return "dåse" if t["beholder"] == "dåse" else "dåse/flaske ikke angivet"


def tabel(tilbud):
    linjer = ["| Kr/dåse | Butik | Pris | Pakke | Dåse | Periode | Noter |",
              "|---:|---|---:|---|:-:|---|---|"]
    for t in tilbud:
        pakke = f"{t['antal']} × {t['stoerrelse_cl']} cl"
        daase = "ja" if t["beholder"] == "dåse" else "?"
        noter = ", ".join(t["noter"])
        linjer.append(f"| **{kr(t['pr_daase'])}** | {t['butik']} | {kr(t['pris'])} | {pakke} "
                      f"| {daase} | {periode(t)} | {noter} |")
    return "\n".join(linjer)


def oversigt(relevante, fravalgt, i_dag, nu):
    dk = [t for t in relevante if not t["graensehandel"]]
    graense = [t for t in relevante if t["graensehandel"]]
    gaelder = lambda t: t["fra"] <= i_dag.isoformat() <= t["til"]
    kommer = lambda t: t["fra"] > i_dag.isoformat()
    sorter = lambda lst: sorted(lst, key=lambda t: (t["pr_daase"], t["fra"]))

    ud = ["# Pepsi Max på dåse – tilbud", "",
          f"Opdateret {nu.strftime('%d/%m/%Y kl. %H:%M')}. Priser er pr. dåse uden pant "
          "(pant får du igen). Data fra eTilbudsavis.", ""]

    billigste = sorter([t for t in dk if gaelder(t)])
    if billigste:
        b = billigste[0]
        ud += [f"> **Billigst lige nu:** {kr(b['pr_daase'])} kr/dåse hos {b['butik']} "
               f"({b['antal']} stk for {kr(b['pris'])} kr, {periode(b)})  "]
    billigste_g = sorter([t for t in graense if gaelder(t)])
    if billigste_g:
        b = billigste_g[0]
        ud += [f"> **Grænsehandel:** {kr(b['pr_daase'])} kr/dåse hos {b['butik']} "
               f"({b['antal']} stk for {kr(b['pris'])} kr, {periode(b)})"]
    ud += ["", "_Dåse „?“ betyder, at avisen ikke skriver dåse eller flaske. Tilbud, der "
           "nævner PET/flaske, er sorteret fra._", ""]

    ud += ["## Dag for dag – billigste i Danmark", "",
           "| Dag | Billigst | Kr/dåse | Næstbedst |", "|---|---|---:|---|"]
    for n in range(14):
        d = (i_dag + timedelta(days=n)).isoformat()
        paa_dagen = sorter([t for t in dk if t["fra"] <= d <= t["til"]])
        if paa_dagen:
            a = paa_dagen[0]
            naest = (f"{paa_dagen[1]['butik']} {kr(paa_dagen[1]['pr_daase'])}"
                     if len(paa_dagen) > 1 else "")
            ud.append(f"| {kort_dato(d)} | {a['butik']} | **{kr(a['pr_daase'])}** | {naest} |")
        else:
            ud.append(f"| {kort_dato(d)} | – | | |")
    ud.append("")

    ud += ["## Gælder nu – Danmark", "", tabel(billigste) if billigste else "_Ingen lige nu._", ""]
    kommende = sorter([t for t in dk if kommer(t)])
    ud += ["## Kommende – Danmark", "", tabel(kommende) if kommende else "_Ingen kendte endnu._", ""]
    g = sorter([t for t in graense if gaelder(t) or kommer(t)])
    ud += ["## Grænsehandel", "", "Ingen pant på dåserne her.", "",
           tabel(g) if g else "_Ingen._", ""]

    if fravalgt:
        ud += ["## Sorteret fra", "",
               "Pepsi-tilbud, der ikke tæller med (flasker, andre størrelser eller ikke Pepsi Max). "
               "Så kan du se, om noget er sorteret forkert fra.", ""]
        for t in sorted(fravalgt, key=lambda t: t["butik"]):
            pakke = (f"{t['antal'] or '?'} × {t['stoerrelse_cl'] or '?'} cl, {t['beholder']}")
            ud.append(f"- {t['butik']}: {t['overskrift']} – {kr(t['pris'])} kr ({pakke}, "
                      f"Pepsi Max: {t['pepsi_max']})")
        ud.append("")

    ud += ["## Kalender", "",
           "Abonnér på `pepsi-max.ics` i din kalender (se `LÆS MIG.md`), så står tilbudsperioderne "
           "der automatisk.", ""]
    return "\n".join(ud)


def ics_tekst(s):
    return s.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def kalender(tilbud, nu):
    stempel = nu.astimezone(ZoneInfo("UTC")).strftime("%Y%m%dT%H%M%SZ")
    ud = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//pepsi-max-tilbud//DA",
          "CALSCALE:GREGORIAN", "METHOD:PUBLISH", "X-WR-CALNAME:Pepsi Max tilbud",
          "X-WR-TIMEZONE:Europe/Copenhagen", "REFRESH-INTERVAL;VALUE=DURATION:PT6H",
          "X-PUBLISHED-TTL:PT6H"]
    for t in sorted(tilbud, key=lambda t: t["fra"]):
        slut = date.fromisoformat(t["til"]) + timedelta(days=1)
        titel = f"🥤 {kr(t['pr_daase'])} kr/dåse – {t['butik']}"
        if t["graensehandel"]:
            titel += " (grænse)"
        beskrivelse = (f"{t['antal']} × {t['stoerrelse_cl']} cl for {kr(t['pris'])} kr "
                       f"({beholder_tekst(t)}).\n{t['overskrift']}: {t['beskrivelse']}")
        if t["noter"]:
            beskrivelse += "\nNoter: " + ", ".join(t["noter"])
        ud += ["BEGIN:VEVENT",
               f"UID:{t['id']}@pepsi-max-tilbud",
               f"DTSTAMP:{stempel}",
               f"DTSTART;VALUE=DATE:{t['fra'].replace('-', '')}",
               f"DTEND;VALUE=DATE:{slut.isoformat().replace('-', '')}",
               f"SUMMARY:{ics_tekst(titel)}",
               f"DESCRIPTION:{ics_tekst(beskrivelse)}",
               f"URL:{AVIS_LINK}",
               "TRANSP:TRANSPARENT",
               "END:VEVENT"]
    ud.append("END:VCALENDAR")
    # Fold lange linjer (RFC 5545: max 75 bytes)
    foldet = []
    for linje in ud:
        b = linje.encode("utf-8")
        while len(b) > 75:
            cut = 75
            while (b[cut] & 0xC0) == 0x80:  # klip ikke midt i et tegn
                cut -= 1
            foldet.append(b[:cut].decode("utf-8"))
            b = b" " + b[cut:]
        foldet.append(b.decode("utf-8"))
    return "\r\n".join(foldet) + "\r\n"


# ---------------------------------------------------------------- main

def main():
    config = json.loads((MAPPE / "config.json").read_text(encoding="utf-8"))
    nu = datetime.now(TZ)
    i_dag = nu.date()

    historik_fil = DATA / "tilbud.json"
    historik = json.loads(historik_fil.read_text(encoding="utf-8")) if historik_fil.exists() else {}

    if len(sys.argv) > 1:  # test med gemte API-svar: tjek_tilbud.py fil1.json fil2.json
        raa = {o["id"]: o for f in sys.argv[1:] for o in json.loads(Path(f).read_text())}.values()
    else:
        raa = hent(config)

    alle = [t for t in (fortolk(o, config) for o in raa) if t]
    relevante = [t for t in alle if relevant(t, config)]
    fravalgt = [t for t in alle if not relevant(t, config)
                and t["til"] >= i_dag.isoformat()
                and (t["stoerrelse_cl"] in config["daase_stoerrelse_cl"] or t["pepsi_max"] != "nej")
                and (t["antal"] or 0) >= config["min_antal_i_pakke"]]

    # Nye tilbud (ikke set før) under alarmgrænsen
    nye = [t for t in relevante if t["id"] not in historik
           and t["til"] >= i_dag.isoformat()
           and t["pr_daase"] <= config["alarm_max_pris_pr_daase"]]

    for t in relevante:
        t["foerst_set"] = historik.get(t["id"], {}).get("foerst_set", i_dag.isoformat())
        historik[t["id"]] = t

    # Behold tilbud i kalender/oversigt så længe de er højst 60 dage gamle
    graense_dato = (i_dag - timedelta(days=60)).isoformat()
    historik = {k: v for k, v in historik.items() if v["til"] >= graense_dato}
    aktuelle = [t for t in historik.values() if t["til"] >= i_dag.isoformat()]

    DATA.mkdir(exist_ok=True)
    historik_fil.write_text(json.dumps(historik, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
                            encoding="utf-8")
    (MAPPE / "OVERSIGT.md").write_text(oversigt(aktuelle, fravalgt, i_dag, nu), encoding="utf-8")
    (MAPPE / "pepsi-max.ics").write_text(kalender(historik.values(), nu), encoding="utf-8",
                                         newline="")

    nye_fil = DATA / "nye.md"
    if nye:
        nye.sort(key=lambda t: t["pr_daase"])
        tekst = (f"Nye Pepsi Max-tilbud til højst {kr(config['alarm_max_pris_pr_daase'])} kr/dåse:\n\n"
                 + tabel(nye) + "\n\nSe hele overblikket i `pepsi-max/OVERSIGT.md`.\n")
        nye_fil.write_text(tekst, encoding="utf-8")
        b = nye[0]
        (DATA / "nye_titel.txt").write_text(
            f"🥤 Pepsi Max: {kr(b['pr_daase'])} kr/dåse hos {b['butik']} ({periode(b)})"
            + (f" + {len(nye) - 1} andre nye tilbud" if len(nye) > 1 else ""), encoding="utf-8")
    else:
        for f in (nye_fil, DATA / "nye_titel.txt"):
            if f.exists():
                f.unlink()

    print(f"{len(raa)} tilbud hentet, {len(relevante)} med Pepsi Max-dåser, {len(nye)} nye under grænsen.")
    for t in sorted(aktuelle, key=lambda t: t["pr_daase"])[:10]:
        print(f"  {kr(t['pr_daase']):>6} kr/dåse  {t['butik']:<20} {periode(t)}")


if __name__ == "__main__":
    main()

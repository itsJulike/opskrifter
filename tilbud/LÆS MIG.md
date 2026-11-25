# Tilbud

Holder øje med udvalgte varer i tilbudsaviserne (data fra eTilbudsavis) og sammenligner dem på
**literpris**, så 24 × 33 cl, 20 × 33 cl og 0,5 l kan stå i samme liste. Stykprisen står ved siden af.
Lige nu holdes der øje med Pepsi Max.

- **Webapp** – `index.html`, se nedenfor.
- **[OVERSIGT.md](OVERSIGT.md)** – pr. vare: billigst lige nu, dag for dag de næste 14 dage, hvad der
  gælder nu, og hvad der kommer.
- **aktuelle.json** – de aktuelle tilbud som data, som appen og Home Assistant læser.
- **tilbud.ics** – kalender med ét heldagsarrangement pr. tilbud, fx
  „🥤 Pepsi Max 8,21 kr/l · 2,71 kr/stk – 365discount“ fra torsdag til onsdag.
- **Alarm** – når et nyt tilbud dukker op under alarmgrænsen, opretter GitHub et issue, og du får en
  mail.

Det kører af sig selv to gange i døgnet via GitHub Actions (`.github/workflows/tilbud.yml`). Du kan
også starte det i hånden under *Actions → Tilbud → Run workflow*.

## Webappen

Når GitHub Pages er slået til (se nedenfor), ligger appen på

```
https://itsjulike.github.io/opskrifter/tilbud/
```

Den viser, hvad der er billigst i dag, en tidslinje over de næste 14 dage og alle tilbud. Du kan skifte
mellem kr pr. liter og kr pr. stk. På telefonen kan siden lægges på hjemmeskærmen (iPhone: Del →
Føj til hjemmeskærm; Android: menu → Føj til startskærm), så den åbner som en app.

**Slå GitHub Pages til (én gang):** repoets *Settings → Pages → Build and deployment*, vælg
*Deploy from a branch*, branch `main` og mappe `/ (root)`, og tryk *Save*. Efter et par minutter
virker adressen ovenfor.

## Home Assistant

Tre muligheder, som kan kombineres:

**1. Hele appen i et dashboard.** Tilføj et *Webside*-kort (Webpage card) med adressen til appen
ovenfor.

**2. Sensor med den billigste pris.** I `configuration.yaml`:

```yaml
rest:
  - resource: https://raw.githubusercontent.com/itsJulike/opskrifter/main/tilbud/aktuelle.json
    scan_interval: 3600
    sensor:
      - name: "Pepsi Max billigst"
        unique_id: tilbud_pepsi_max_billigst
        unit_of_measurement: "kr/l"
        value_template: "{{ value_json.varer[0].billigst_nu.literpris if value_json.varer[0].billigst_nu else none }}"
        json_attributes_path: "$.varer[0]"
        json_attributes:
          - billigst_nu
          - tilbud
```

Så kan du lave automationer (fx en besked, når prisen kommer under 9 kr/l) og vise listen med et
Markdown-kort:

```yaml
type: markdown
title: 🥤 Pepsi Max
content: |
  {% set b = state_attr('sensor.pepsi_max_billigst', 'billigst_nu') %}
  {% if b %}**Billigst nu:** {{ b.butik }} – {{ b.literpris }} kr/l ({{ b.stykpris }} kr/stk),
  {{ b.pakning }} for {{ b.pris }} kr, til {{ b.til }}{% endif %}

  {% for t in state_attr('sensor.pepsi_max_billigst', 'tilbud') or [] %}
  - {{ t.literpris }} kr/l · {{ t.stykpris }} kr/stk – {{ t.butik }} ({{ t.fra[8:] }}/{{ t.fra[5:7] }}–{{ t.til[8:] }}/{{ t.til[5:7] }})
  {% endfor %}
```

**3. Kalenderen.** *Indstillinger → Enheder og tjenester → Tilføj integration → Remote Calendar*
(Fjernkalender) med adressen til `tilbud.ics` nedenfor.

## Kalenderen

Google Kalender på computeren: *Andre kalendere → + → Fra webadresse*, og indsæt

```
https://raw.githubusercontent.com/itsJulike/opskrifter/main/tilbud/tilbud.ics
```

På iPhone: *Indstillinger → Kalender → Konti → Tilføj konto → Andet → Tilføj abonnerede kalender*.

Google henter abonnerede kalendere et par gange i døgnet, så nye tilbud kan være lidt om at dukke op.

## Push-besked på telefonen (valgfrit)

1. Installér appen **ntfy** og abonnér på et emne med et navn, som ingen kan gætte, fx
   `tilbud-k8f3q9`.
2. På GitHub: *Settings → Secrets and variables → Actions → New repository secret*, navn
   `NTFY_TOPIC`, værdi = emnets navn.

## Sådan læses tallene

- Priserne er uden pant. Til sammenligning er Pepsi Max' normalpris omkring 118 kr for 24 dåser,
  ca. 14,90 kr/l.
- **Type** er dåse, flaske eller „?“, hvis avisen ikke skriver det.
- „Flere varianter, Pepsi Max ikke nævnt“ betyder, at avisen skriver fx „Pepsi eller Faxe Kondi, flere
  varianter“. Pepsi Max er næsten altid med i de tilbud.
- „Flere størrelser: 50 cl–150 cl“ betyder, at prisen gælder flere størrelser. Literprisen er regnet
  for den største størrelse inden for grænserne (1,5 l tæller ikke med).
- Grænsebutikker er ikke med.

## Tilføj en vare

Tilføj en blok under `"varer"` i `config.json`, fx:

```json
{
  "navn": "Faxe Kondi",
  "emoji": "🍋",
  "soegeord": ["faxe kondi"],
  "skal_indeholde": ["faxe kondi"],
  "ogsaa_flere_varianter_af": [],
  "min_cl": 20,
  "max_cl": 100,
  "alarm_max_literpris": 12.0,
  "kalender_max_literpris": 15.0
}
```

| Felt | Betydning |
|---|---|
| `soegeord` | Hvad der søges efter i eTilbudsavis |
| `skal_indeholde` | Tilbuddet tæller med, hvis overskrift eller tekst indeholder et af disse ord |
| `ogsaa_flere_varianter_af` | Tæller også med (markeret), hvis et af disse ord står sammen med „flere varianter“ |
| `min_cl` / `max_cl` | Størrelser pr. stk, der tæller med (100 = 1 l; 1,5 l er dermed udelukket) |
| `alarm_max_literpris` | Alarm ved nye tilbud til højst denne literpris (12 kr/l ≈ 4 kr pr. 33 cl) |
| `kalender_max_literpris` | Kun tilbud til højst denne literpris kommer i kalenderen |

Øverst i `config.json`: `position` (midtpunkt og radius for søgningen, standard hele Danmark),
`udeluk_graensehandel` og `udeluk_butikker`.

Literpris passer til drikkevarer. Skal der på et tidspunkt holdes øje med fx kaffe eller vaskepulver,
skal scriptet lære kilopris; sig til.

Køres lokalt med `python3 tilbud/tjek_tilbud.py` (kræver kun Python 3.9+).

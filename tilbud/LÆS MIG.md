# Tilbud

Holder øje med udvalgte varer i tilbudsaviserne (data fra eTilbudsavis) og sammenligner dem på
**literpris**, så 24 × 33 cl, 20 × 33 cl og 0,5 l kan stå i samme liste. Stykprisen står ved siden af.
Lige nu holdes der øje med Pepsi Max.

- **[OVERSIGT.md](OVERSIGT.md)** – pr. vare: billigst lige nu, dag for dag de næste 14 dage, hvad der
  gælder nu, og hvad der kommer.
- **tilbud.ics** – kalender med ét heldagsarrangement pr. tilbud, fx
  „🥤 Pepsi Max 8,21 kr/l · 2,71 kr/stk – 365discount“ fra torsdag til onsdag.
- **Alarm** – når et nyt tilbud dukker op under alarmgrænsen, opretter GitHub et issue, og du får en
  mail.

Det kører af sig selv to gange i døgnet via GitHub Actions (`.github/workflows/tilbud.yml`). Du kan
også starte det i hånden under *Actions → Tilbud → Run workflow*.

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

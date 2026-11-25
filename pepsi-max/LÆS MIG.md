# Pepsi Max-tilbud

Holder øje med Pepsi Max på dåse i tilbudsaviserne (data fra eTilbudsavis) og regner prisen pr. dåse
ud, så 18-, 20- og 24-pakker kan sammenlignes direkte.

- **[OVERSIGT.md](OVERSIGT.md)** – billigst lige nu, dag for dag de næste 14 dage, kommende tilbud og
  grænsehandel for sig.
- **pepsi-max.ics** – kalender med ét heldagsarrangement pr. tilbud, fx
  „🥤 2,71 kr/dåse – 365discount“ fra torsdag til onsdag.
- **Alarm** – når et nyt tilbud dukker op til højst 4,00 kr/dåse, opretter GitHub et issue, og du får
  en mail. Grænsen ændres i `config.json` (`alarm_max_pris_pr_daase`).

Det kører af sig selv to gange i døgnet via GitHub Actions (`.github/workflows/pepsi-max.yml`). Du kan
også starte det i hånden under *Actions → Pepsi Max-tilbud → Run workflow*.

## Kalenderen

Google Kalender på computeren: *Andre kalendere → + → Fra webadresse*, og indsæt

```
https://raw.githubusercontent.com/itsJulike/opskrifter/main/pepsi-max/pepsi-max.ics
```

På iPhone: *Indstillinger → Kalender → Konti → Tilføj konto → Andet → Tilføj abonnerede kalender*.

Google henter abonnerede kalendere et par gange i døgnet, så nye tilbud kan være lidt om at dukke op.

## Push-besked på telefonen (valgfrit)

1. Installér appen **ntfy** og abonnér på et emne med et navn, som ingen kan gætte, fx
   `pepsi-max-k8f3q9`.
2. På GitHub: *Settings → Secrets and variables → Actions → New repository secret*, navn
   `NTFY_TOPIC`, værdi = emnets navn.

## Sådan læses tallene

- Prisen pr. dåse er uden pant. Danske butikker lægger 1 kr pant oven i, som du får igen.
  Grænsebutikkerne har ingen pant.
- Tilbud, der nævner PET eller flaske, er sorteret fra. Står der hverken dåse eller flaske i avisen,
  vises tilbuddet med „?“ i kolonnen *Dåse*.
- „Pepsi, flere varianter“ betyder, at avisen skriver „Pepsi eller Faxe Kondi, flere varianter“
  uden at nævne Max. Pepsi Max er næsten altid med i de tilbud.
- Tilbud, der blev sorteret fra, står nederst i oversigten, så du kan se, om noget er røget forkert ud.

## Indstillinger (`config.json`)

| Felt | Betydning |
|---|---|
| `soegeord` | Hvad der søges efter i eTilbudsavis |
| `position` | Midtpunkt og radius for søgningen (standard: hele Danmark) |
| `daase_stoerrelse_cl` | Dåsestørrelser, der tæller med |
| `min_antal_i_pakke` | Mindste antal dåser i en pakke/ramme |
| `medtag_pepsi_flere_varianter` | Medtag „Pepsi eller Faxe Kondi, flere varianter“ |
| `alarm_max_pris_pr_daase` | Alarm ved nye tilbud til højst denne pris pr. dåse |
| `graensebutikker` | Butikker, der vises under grænsehandel |

Køres lokalt med `python3 pepsi-max/tjek_tilbud.py` (kræver kun Python 3.9+).

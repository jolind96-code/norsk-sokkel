# Norsk sokkel — produksjon felt for felt

Interaktivt dashboard over produksjonen på norsk kontinentalsokkel, 1971–2026.
Alle data er åpne. Uavhengig prosjekt, ikke tilknyttet Sokkeldirektoratet.

## Kom i gang

**Bare se på den:** åpne `norsk-sokkel.html` — alt er bakt inn i én fil.

**Utvikle videre:** `index.html` leser datafilene ved siden av seg. Den må
serveres over HTTP, ikke åpnes som fil, fordi nettleseren blokkerer `fetch()`
fra `file://`:

```powershell
python -m http.server 8765
# apne http://127.0.0.1:8765/index.html
```

Når du er ferdig, bygg delefila på nytt:

```powershell
python build_single.py     # -> norsk-sokkel.html
```

## Filene

| Fil | Hva |
|---|---|
| `index.html` | Hele applikasjonen. Utviklingsversjon. |
| `norsk-sokkel.html` | Selvstendig enkeltfil til deling. Genereres. |
| `data.json` | 132 felt, produksjon og reserver 1971–2026 |
| `partners.json` | Rettighetshavere og eierandeler, 128 felt |
| `facilities.json` | Innretninger per felt, 113 felt |
| `prices.json` | Brent, europeisk gasspris, USD/NOK |
| `power.json` | 1 316 kraftverk på land: 1 253 vannkraft, 63 vindkraft |
| `cities.json` | 83 norske kystbyer over 5 000 innbyggere |
| `ncs.geojson` | Yttergrense for norsk sokkel |

## Byggeskriptene

Kjør disse for å hente ferske data. Hver av dem skriver én JSON-fil.

```powershell
python build_data.py         # produksjon + reserver + feltgrenser
python build_partners.py     # rettighetshavere
python build_facilities.py   # innretninger
python build_prices.py       # priser og valutakurs
python build_power.py        # vann- og vindkraft på land
python build_cities.py       # byer (endres sjelden)
python build_single.py       # pakk alt til én fil
```

`verify.py` kjører en headless nettlesertest og skriver ut konsollfeil,
tilstand og et skjermbilde. Bruk den etter endringer — den fanger feil som
ikke synes i koden.

## Datakilder

| Hva | Kilde | Lisens |
|---|---|---|
| Produksjon, reserver, feltgrenser, innretninger, rettighetshavere | Sokkeldirektoratet | NLOD 2.0 |
| Brent råolje | Verdensbanken Pink Sheet + EIA | Offentlige data |
| Europeisk gasspris | Verdensbanken Pink Sheet | — |
| USD/NOK | Norges Bank | — |
| Folketall | SSB tabell 04859 | NLOD |
| Kartgrunnlag | OpenStreetMap via OpenFreeMap | ODbL / MIT |

NLOD krever kildehenvisning **og** at det opplyses at data er bearbeidet.
Begge deler står i toppen av siden. Vi aggregerer måned til år og regner
volum om til fat.

## Omregningsfaktorer

Fra Sokkeldirektoratets egen tabell (*Fakta*, Vedlegg 5):

```
1 Sm³ olje       = 1,0 Sm³ o.e.
1 Sm³ kondensat  = 1,0 Sm³ o.e.
1000 Sm³ gass    = 1,0 Sm³ o.e.
1 tonn NGL       = 1,9 Sm³ o.e.
1 Sm³ råolje     = 6,29 fat
```

**Felle:** NGL oppgis i **mill Sm³** i produksjonstabellen, men i
**mill tonn** i reservetabellen. Bekreftet empirisk mot SODIRs egen
o.e.-kolonne — faktoren 1,9 treffer eksakt på alle felt.

## Inntektsanslaget

Produsert mengde ganget med årets gjennomsnittspris: Brent for olje og
kondensat, europeisk gasspris for gass, NGL sjablongmessig til halv oljepris.
Omregnet til kroner med Norges Banks årskurs.

Dette er **bruttoverdien av det som ble produsert** — ikke salgsinntekt og
ikke fortjeneste. Kostnader, skatt, langsiktige kontrakter og prissikring er
ikke med. Modellen gir 1 085 mrd kr for 2025, som ligger nær Norges faktiske
petroleumseksportverdi, men er ikke avstemt mot noen offisiell publisert sum.

## Kjente begrensninger

- **Mobil er ikke testet.** Layouten er et tre-kolonners skrivebordsoppsett.
- **To felt bommer ved klikk** i kartet: Breidablikk velger Ringhorne Øst,
  Hyme velger Bauge. Begge ligger tett inntil et større felt.
- **Gasspris for 2026** er fjorårets, siden Verdensbanken stopper des. 2025.
- **Tilgjengelighet er påbegynt**, ikke fullført. Se `BACKLOG.md`.
- `norsk-sokkel.html` henter fortsatt MapLibre og ECharts fra unpkg.com og
  kartfliser fra openfreemap.org. Blokkeres disse, blir kartet grått.

## Teknisk

MapLibre GL **5.9.0** — ikke nyere. Versjon 6 er ESM-only og har ingen
UMD-bygg på CDN. ECharts for grafene. Ingen byggesteg, ingen avhengigheter
utover Python for datauthenting.

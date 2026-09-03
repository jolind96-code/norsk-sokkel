# Backlog

Status per 2. september 2026. Alle kilder er verifisert med faktiske HTTP-kall
der ikke annet er nevnt.

---

## Pågår

### Tilgjengelighet (WCAG)
**Gjort:** synlig fokusmarkering (`:focus-visible`), `prefers-reduced-motion`,
`aria-label` på kart, søk, årslider, play-knapp, operatørvelger og
legendeknapp, `aria-live` på KPI-panelet.

**Gjenstår:**
- Kontrastsjekk av den mørke paletten. `--tx3` mot `--bg` er trolig under 4,5:1.
- Full tastaturnavigasjon. Kartet kan ikke betjenes uten mus i dag.
- Skjermlesertest.
- Fargeblindhet: grønn/rød for olje/gass er problematisk ved deuteranopi.
  Vurder form eller mønster i tillegg til farge.

Målgruppen inkluderer skoleelever, så dette betyr noe.

---

## Feil som bør fikses

### Klikkbarhet i kartet
2 av 94 felt bommer: **Breidablikk** velger Ringhorne Øst, **Hyme** velger
Bauge. Begge ligger tett inntil et større felt. Johan Castberg er fikset.

Årsak trolig at nabofeltets boble eller polygon dekker punktet, eller at
polygonsentrene nesten faller sammen.

*Mulig løsning:* prioriter minste boble ved overlapp, eller legg klikkflaten
på selve feltpolygonet med z-rekkefølge etter feltstørrelse, minste øverst.

### Legenden dekker felt i Nordsjøen
Legenden nederst til venstre ligger over deler av sørlige Nordsjøen. Den er
sammenleggbar, men står åpen som standard.

*Mulig løsning:* start sammenlagt, flytt den, eller gjør kartet bredere.

### Lesbarhet i tette områder
I Tampen-området (Statfjord, Gullfaks, Snorre, Visund) overlapper bobler,
polygoner, ikoner og navn. Ikoner vises nå kun fra zoom 6,8.

*Mulig løsning:* klynging ved lav zoom, eller demp polygonene når bobler vises.

### Ferskere gasspris
Verdensbankens Pink Sheet stopper des. 2025, så 2026 bruker fjorårets
gasspris (11,96 $/MMBtu). Brent er oppdatert til juli 2026 via EIA.

Trenger en nøkkelfri kilde for fersk europeisk gasspris. FRED var
utilgjengelig herfra (timeout, både via PowerShell og curl).

---

## Ny funksjonalitet

### Inntekter over tid
`revenue()` regner allerede per år. En graf over anslått verdi gjennom
historien vil vise 2008-toppen og 2022-energikrisen tydelig.
Lavthengende — dataene finnes allerede.

### MarineTraffic / skip og rigger i sanntid
Vis fartøy og rigger slik `minoffshore.no` gjør.

**Merk:** MarineTraffic krever betalt API-nøkkel. Det passer dårlig i en
selvstendig HTML-fil, og nøkkelen kan ikke ligge i klientkoden hvis siden
publiseres.

*Undersøk først:* Kystverkets åpne AIS-data (`kystdatahuset.no`,
`ais.kystverket.no`), AISHub, `aisstream.io` (gratis nøkkel, websocket).
Avklar lisens for videredistribusjon.

### Mobilvisning
Layouten er tre-kolonners skrivebordsoppsett og aldri testet på telefon.
Anslag 3–6 timer. Kun nødvendig hvis siden deles bredt.

---

## Publisering

### GitHub Pages og eget domene
`gh` CLI er installert og innlogget som `jolind96-code` med `repo`- og
`workflow`-scope. Krever offentlig repo på gratisplanen.

Domenekandidater vurdert: `sokkelen.no` (ledig per 1. sept.), `feltkart.no`,
`fatperdag.no`. Norid tar 65 kr + mva per år, forhandleren legger på sitt.
Privatperson må opprette person-ID hos Norid først.

### Automatisk dataoppdatering
GitHub Actions som kjører `build_data.py`, `build_prices.py`,
`build_partners.py` og `build_single.py` månedlig og committer nye datafiler.
SODIR publiserer produksjonstall månedlig. Ca. 15 linjer YAML.

### Bake inn bibliotekene lokalt
`norsk-sokkel.html` henter MapLibre 5.9.0 og ECharts fra unpkg.com, og
kartfliser fra tiles.openfreemap.org. Blokkeres unpkg av bedriftsnettverk,
blir siden ubrukelig. Å bake inn bibliotekene koster ca. 2 MB.
Kartfliser krever uansett nett.

---

## Ferdig

- Datapipeline mot Sokkeldirektoratet, sanity-sjekket mot offisielle tall
- MapLibre + OpenFreeMap (fjernet CARTO-nøkkelfeilen)
- Kumulativ visning som standard
- Kart låst til norsk sokkel
- Partnere og eierandeler per felt (128 felt, alle summerer til 100 %)
- Inntektsanslag per felt
- Skolevennlig hjelpeboks med enhetsforklaringer
- Innretningsikoner med dybde og hover-forklaring
- Legende med navngitte størrelsesklasser
- Avspillingsfart ned til 850 ms per år
- Strømkartlag (vann- og vindkraft på land) med eier, effekt, årsproduksjon
- Spotpris per prisområde + sammenligningsboks offshore vs. land
- Detaljpanel for kraftanlegg (samme sted som feltdetaljer), inkl. "verdi ved
  full produksjon nå"
- Rolig teller: oppdateres 4x/sek i stedet for hver frame, ingen desimaler på
  store tall (mrd/mill kr)
- Prisområdegrenser (NO1–NO5) som eget valgfritt kartlag, bygget av
  fylkesgrenser (se forbehold under)

---

## Kjente forenklinger / gjenstår

### Prisområdegrenser er fylkesbaserte, ikke offisiell nettopologi
`build_omrader.py` grupperer 2024-fylkesgrenser til NO1–NO5. Ekte elspot-
grenser følger ikke alltid fylkesgrenser eksakt (enkelte fylker er reelt delt
av en grense). Fant ingen resolverbar kilde herfra for NVEs egen
Elspot-lag (`nve.geodataonline.no` løste ikke DNS i dette miljøet).
*Neste steg om nøyaktighet trengs:* hent ekte geometri via
`nve.geodataonline.no/.../Mapservices/Elspot/MapServer/0` fra et miljø med
tilgang, eller konverter NVEs shapefile med QGIS/mapshaper.

### Flere strømkilder å vurdere
- ENTSO-E Transparency (produksjon per teknologi/time)
- NVE magasinstatistikk (reservoarnivå/fylling i TWh - "reserver" for strøm)
- Statnett sanntidsdrift (nå-balanse i MW)
- SSB historikk (teknologifordelt årsproduksjon lenger tilbake enn NVE)

### Kartlagsmodus
Egen modusvelger (Offshore / På land / Begge) der filter, liste, rangering
og detaljpanel følger aktivt lag, med sammenligningsboksen fast uansett valg.
Ikke påbegynt.


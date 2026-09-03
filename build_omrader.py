# -*- coding: utf-8 -*-
"""
Bygger omrader.geojson: fylkesgrenser tagget med NO-prisomrade (NO1-NO5),
til bruk som eget, valgfritt kartlag ("vis prisomradegrenser").

Grunnlag: fylker-og-kommuner (robhop, Kartverket-baserte grenser, 2024-inndeling).
Ekte elspot-grenser folger IKKE alltid fylkesgrenser eksakt (noen fylker er
delt av en prisomradegrense internt), sa dette er en pedagogisk TILNAERMING,
ikke en offisiell netttopologi. Det star tydelig i kartlaget sin fotnote.

Kilde for selve fylke-til-omrade-inndelingen: NVE/Statnett sin vanlige
5-omrade-modell, slik den oftest presenteres (bl.a. i "hvakosterstrommen"-
sammenhenger): NO1 Ost, NO2 Sor/Agder+Rogaland, NO3 Midt, NO4 Nord, NO5 Vest.
"""
import json
import os
import urllib.request

FYLKER_URL = ("https://raw.githubusercontent.com/robhop/"
              "fylker-og-kommuner/main/Fylker-S.geojson")
RAW_CACHE = "_fylker_raw.geojson"

FYLKE_TIL_OMR = {
    "03": "NO1",  # Oslo
    "32": "NO1",  # Akershus
    "31": "NO1",  # Østfold
    "33": "NO1",  # Buskerud
    "39": "NO1",  # Vestfold
    "40": "NO1",  # Telemark
    "34": "NO1",  # Innlandet
    "42": "NO2",  # Agder
    "11": "NO2",  # Rogaland
    "50": "NO3",  # Trøndelag
    "15": "NO3",  # Møre og Romsdal
    "18": "NO4",  # Nordland
    "55": "NO4",  # Troms
    "56": "NO4",  # Finnmark
    "46": "NO5",  # Vestland
}

def run():
    if not os.path.exists(RAW_CACHE):
        print("Laster ned fylkesgrenser...")
        urllib.request.urlretrieve(FYLKER_URL, RAW_CACHE)
    d = json.load(open(RAW_CACHE, encoding="utf-8"))
    ut = {"type": "FeatureCollection", "features": []}
    manglet = []
    for f in d["features"]:
        p = f["properties"]
        nr = str(p.get("fylkesnummer") or p.get("id") or "").zfill(2)
        omr = FYLKE_TIL_OMR.get(nr)
        if not omr:
            manglet.append(p.get("fylkesnavn") or p.get("name"))
            continue
        ut["features"].append({
            "type": "Feature",
            "geometry": f["geometry"],
            "properties": {
                "fylke": p.get("fylkesnavn") or p.get("name"),
                "omr": omr,
            },
        })
    if manglet:
        print("Uten omrade-mapping:", manglet)
    json.dump(ut, open("omrader.geojson", "w", encoding="utf-8"),
              ensure_ascii=False, separators=(",", ":"))
    print(f"omrader.geojson: {len(ut['features'])} fylker i "
          f"{len(set(x['properties']['omr'] for x in ut['features']))} prisomrader")

if __name__ == "__main__":
    run()

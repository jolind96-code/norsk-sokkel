"""Bygger energiformer.json: nasjonal arlig kraftproduksjon per energiform.

NVEs egen kraftverksdatabase-API (api.nve.no) dekker KUN vannkraft og
vindkraft med geolokaliserte enkeltanlegg - det finnes ingen tilsvarende
API for solkraft eller varmekraft (bekreftet: NVE/API-repoet pa GitHub har
bare mapper for hydropower og wind_power, ingen for termisk/sol - og flere
sannsynlige endepunktnavn ga 404 direkte mot api.nve.no).

Solkraft i Norge er i hovedsak mange sma, ikke-geolokaliserte takanlegg
(32 400+ anlegg, 767 MW samlet, NVE 2024-tall) og varmekraft er naermest
fravaerende - verken egner seg for punkter pa et kart.

I stedet hentes nasjonale arlige totaltall per energiform fra SSB sin
Statistikkbank, tabell 08307 "Produksjon, import, eksport og forbruk av
elektrisk kraft (GWh)". Denne bruker NOYAKTIG samme firedeling som NVE selv
(Vannkraft, Vindkraft, Solkraft, Varmekraft) - se nve.no/energi/energisystem/.
Disse tallene vises som nasjonal kontekst i KPI-kortet (Land-modul), IKKE
som punkter pa kartet - kartet viser fortsatt kun vann+vind (som er de
eneste med per-anlegg-geometri).

Kilde: SSB (data.ssb.no), API-v0/PxWebApi, NLOD/CC BY 4.0.
"""
import json
import os
import urllib.request

UA = {"User-Agent": "sokkel-mvp (apne data)", "Content-Type": "application/json"}
URL = "https://data.ssb.no/api/v0/no/table/08307"
FIRST_YEAR = 1990


def main():
    print("henter energiform-totaler fra SSB (tabell 08307) ...")
    meta_req = urllib.request.Request(URL, headers=UA)
    with urllib.request.urlopen(meta_req, timeout=30) as r:
        meta = json.loads(r.read())
    all_years = meta["variables"][1]["values"]
    years = [y for y in all_years if int(y) >= FIRST_YEAR]

    query = {
        "query": [
            {"code": "ContentsCode", "selection": {"filter": "item",
             "values": ["ProdTotal", "VannKraft", "VindKraft", "Solkraft", "VarmeKraft"]}},
            {"code": "Tid", "selection": {"filter": "item", "values": years}},
        ],
        "response": {"format": "json-stat2"},
    }
    req = urllib.request.Request(URL, data=json.dumps(query).encode("utf-8"), headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.loads(r.read())

    metrics = list(d["dimension"]["ContentsCode"]["category"]["index"].keys())
    n_t = len(years)
    vals = d["value"]
    by_metric = {}
    for mi, m in enumerate(metrics):
        row = vals[mi * n_t:(mi + 1) * n_t]
        by_metric[m] = [None if v is None else round(v) for v in row]

    out = {
        "kilde": "SSB (data.ssb.no), tabell 08307 - NLOD/CC BY 4.0. "
                 "Samme energiform-inndeling som NVE (vann/vind/sol/varme). "
                 "Nasjonale totaltall, GWh/ar - IKKE geolokalisert (NVE har ingen "
                 "per-anlegg-API for sol/varme).",
        "enhet": "GWh",
        "ar": [int(y) for y in years],
        "total": by_metric["ProdTotal"],
        "vann": by_metric["VannKraft"],
        "vind": by_metric["VindKraft"],
        "sol": by_metric["Solkraft"],
        "varme": by_metric["VarmeKraft"],
    }
    with open("energiformer.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))

    last = len(years) - 1
    print(f"  {years[0]}-{years[-1]} ({len(years)} ar)")
    print(f"  siste ar ({years[last]}): total {out['total'][last]:,} GWh, "
          f"vann {out['vann'][last]:,}, vind {out['vind'][last]:,}, "
          f"sol {out['sol'][last]:,}, varme {out['varme'][last]:,}".replace(",", " "))
    print(f"energiformer.json: {round(os.path.getsize('energiformer.json')/1024, 1)} KB")


if __name__ == "__main__":
    main()

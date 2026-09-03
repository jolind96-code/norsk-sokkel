"""Legger konsumprisindeks (KPI) inn i prices.json, sa historiske kroner kan
regnes om til dagens kroneverdi (reelle tall) i stedet for a blande sammen
kroner fra ulike tiar uten videre kontekst.

Kilde: SSB tabell 08184 "Konsumprisindeks (2015=100), etter statistikkvariabel
og ar", arsgjennomsnitt. Apen API, ingen nokkel. Faller tilbake til lokal
cache (_kpi_raw.json) hvis SSB ikke er nabar.
"""
import json
import os
import urllib.request

CACHE = "_kpi_raw.json"
SSB_URL = "https://data.ssb.no/api/v0/no/table/08184/"


def fetch_cpi(years):
    """Henter KPI-arsgjennomsnitt for gitte ar fra SSB. Faller tilbake til cache."""
    body = json.dumps({
        "query": [
            {"code": "ContentsCode", "selection": {"filter": "item", "values": ["KpiAar"]}},
            {"code": "Tid", "selection": {"filter": "item", "values": [str(y) for y in years]}},
        ],
        "response": {"format": "json-stat2"},
    }).encode("utf-8")
    try:
        req = urllib.request.Request(SSB_URL, data=body, headers={
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (sokkel-mvp; apne data)"})
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.loads(r.read().decode("utf-8"))
        vals = d["value"]
        if len(vals) == len(years):
            with open(CACHE, "w", encoding="utf-8") as f:
                json.dump(vals, f)
            print(f"  SSB KPI hentet: {years[0]}-{years[-1]} ({len(vals)} ar)")
            return dict(zip(years, vals))
    except Exception as e:
        print(f"  SSB utilgjengelig ({e}) - bruker cache")
    if os.path.exists(CACHE):
        with open(CACHE, encoding="utf-8-sig") as f:
            vals = json.load(f)
        n = min(len(vals), len(years))
        print(f"  Cache brukt: {years[0]}-{years[n-1]} ({n} ar)")
        return dict(zip(years[:n], vals[:n]))
    raise RuntimeError("Ingen KPI-data tilgjengelig (verken SSB eller cache)")


def main():
    with open("prices.json", encoding="utf-8") as f:
        p = json.load(f)
    years = p["years"]
    # SSB har ikke arsgjennomsnitt for innevaerende, ufullstendige ar - hent
    # det som finnes og videref\u00f8r siste kjente niva for resten (samme
    # "carry forward"-prinsipp som brukes for olje/gass/valuta i build_prices.py).
    kjente = [y for y in years if y <= 2025]
    cpi = fetch_cpi(kjente)
    siste_ar = max(cpi)
    siste_niva = cpi[siste_ar]
    serie = [cpi.get(y, siste_niva) for y in years]

    p["cpi"] = serie
    p["cpiBaseYear"] = siste_ar
    p["cpiNote"] = ("SSB tabell 08184, KPI arsgjennomsnitt (2015=100). "
                     f"Brukes til a regne historiske kronebelop om til {siste_ar}-kroneverdi. "
                     "Ufullstendige/kommende ar viderefores med siste kjente niva.")

    with open("prices.json", "w", encoding="utf-8") as f:
        json.dump(p, f, ensure_ascii=False, separators=(",", ":"))
    print(f"prices.json oppdatert med cpi-serie ({years[0]}-{years[-1]}), "
          f"basisar={siste_ar} (KPI={siste_niva})")


if __name__ == "__main__":
    main()

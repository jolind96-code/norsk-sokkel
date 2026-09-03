"""
Bygger data.json for Sokkel-dashboardet.

Kilder (Sokkeldirektoratet, NLOD-lisens):
  - field_production_monthly : https://factpages.sodir.no  (CSV, ingen CORS -> må hentes server-side)
  - field_reserves           : https://factpages.sodir.no  (CSV)
  - Field by status (lag 502): https://factmaps.sodir.no/api/rest  (GeoJSON, WGS84)

Join-nokkel: fldNpdidField (kart/reserver) == prfNpdidInformationCarrier (produksjon)
"""

import csv
import io
import json
import sys
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import date

FACTPAGES = "https://factpages.sodir.no/public?/Factpages/external/tableview/{table}"
FACTPAGES_ARGS = (
    "&rs:Command=Render&rc:Toolbar=false&rc:Parameters=f"
    "&IpAddress=not_used&CultureCode=en&rs:Format=CSV&Top100=false"
)

FACTMAPS = "https://factmaps.sodir.no/api/rest/services/Factmaps/FactMapsWGS84/MapServer/502/query"

UA = {"User-Agent": "sokkel-mvp/1.0 (open data client)"}


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=300) as resp:
        raw = resp.read()
    return raw.decode("utf-8-sig")


def fetch_csv(table: str) -> list[dict]:
    url = FACTPAGES.format(table=table) + FACTPAGES_ARGS
    print(f"  henter {table} ...", flush=True)
    text = fetch(url)
    rows = list(csv.DictReader(io.StringIO(text)))
    print(f"    {len(rows)} rader")
    return rows


def num(v, default=0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def fetch_geometry() -> dict:
    params = {
        "where": "1=1",
        "outFields": ",".join([
            "fldName", "fldNpdidField", "fldCurrentActivitySatus",
            "cmpLongName", "fldHcType", "fldMainArea", "fldDiscoveryYear",
        ]),
        "returnGeometry": "true",
        "geometryPrecision": "4",
        "maxAllowableOffset": "0.0015",
        "outSR": "4326",
        "f": "geojson",
    }
    url = FACTMAPS + "?" + urllib.parse.urlencode(params)
    print("  henter feltpolygoner ...", flush=True)
    gj = json.loads(fetch(url))
    print(f"    {len(gj['features'])} polygoner")
    return gj


# --- produksjon: mnd -> ar, per felt ------------------------------------------
# CSV-enheter: olje/NGL/kondensat/vann = mill Sm3, gass = mrd Sm3, OE = mill Sm3 o.e.
PROD_COLS = {
    "oil": "prfPrdOilNetMillSm3",
    "gas": "prfPrdGasNetBillSm3",
    "ngl": "prfPrdNGLNetMillSm3",
    "con": "prfPrdCondensateNetMillSm3",
    "oe": "prfPrdOeNetMillSm3",
    "wat": "prfPrdProducedWaterInFieldMillSm3",
}


def build_production(rows: list[dict]):
    # {npdid: {year: {key: value}}}
    agg = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
    names = {}
    latest_month = {}  # npdid -> (year, month) siste maned med produksjon
    for r in rows:
        npdid = r["prfNpdidInformationCarrier"].strip()
        if not npdid:
            continue
        year = int(r["prfYear"])
        month = int(r["prfMonth"])
        names[npdid] = r["prfInformationCarrier"].strip()
        bucket = agg[npdid][year]
        any_prod = False
        for key, col in PROD_COLS.items():
            v = num(r.get(col))
            bucket[key] += v
            if key != "wat" and v > 0:
                any_prod = True
        if any_prod:
            prev = latest_month.get(npdid)
            if prev is None or (year, month) > prev:
                latest_month[npdid] = (year, month)
    return agg, names, latest_month


def build_reserves(rows: list[dict]):
    """Nyeste versjon per felt."""
    best = {}
    for r in rows:
        npdid = r["fldNpdidField"].strip()
        if not npdid:
            continue
        ver = int(num(r.get("fldVersion"), 0))
        if npdid in best and best[npdid]["_ver"] >= ver:
            continue
        best[npdid] = {
            "_ver": ver,
            "asOf": r.get("fldDateOffResEstDisplay", ""),
            "recOil": round(num(r.get("fldRecoverableOil")), 3),
            "recGas": round(num(r.get("fldRecoverableGas")), 3),
            "recNgl": round(num(r.get("fldRecoverableNGL")), 3),
            "recCon": round(num(r.get("fldRecoverableCondensate")), 3),
            "recOe": round(num(r.get("fldRecoverableOE")), 3),
            "remOil": round(num(r.get("fldRemainingOil")), 3),
            "remGas": round(num(r.get("fldRemainingGas")), 3),
            "remNgl": round(num(r.get("fldRemainingNGL")), 3),
            "remCon": round(num(r.get("fldRemainingCondensate")), 3),
            "remOe": round(num(r.get("fldRemainingOE")), 3),
        }
    for v in best.values():
        v.pop("_ver")
    return best


def main() -> int:
    print("Laster ned apne data fra Sokkeldirektoratet ...")
    prod_rows = fetch_csv("field_production_monthly")
    res_rows = fetch_csv("field_reserves")
    geo = fetch_geometry()

    agg, names, latest_month = build_production(prod_rows)
    reserves = build_reserves(res_rows)

    # metadata fra kartlaget
    meta = {}
    for f in geo["features"]:
        p = f["properties"]
        npdid = str(p.get("fldNpdidField"))
        meta[npdid] = {
            "status": p.get("fldCurrentActivitySatus") or "Ukjent",
            "operator": p.get("cmpLongName") or "Ukjent",
            "hcType": p.get("fldHcType") or "Ukjent",
            "area": p.get("fldMainArea") or "Ukjent",
            "discovered": p.get("fldDiscoveryYear"),
        }
        # bruk kartets feltnavn (penere kasus enn CSV sitt VERSALNAVN)
        if npdid in names:
            names[npdid] = p.get("fldName") or names[npdid]

    years_all = sorted({y for d in agg.values() for y in d})
    y0, y1 = years_all[0], years_all[-1]
    # siste maned med data globalt -> siste ar er som regel ufullstendig
    last_y, last_m = max(latest_month.values())
    print(f"  produksjonsar: {y0}-{y1} (siste data: {last_y}-{last_m:02d})")

    fields = []
    for npdid, byyear in agg.items():
        m = meta.get(npdid, {})
        series = {k: [] for k in PROD_COLS}
        for y in range(y0, y1 + 1):
            b = byyear.get(y)
            for k in PROD_COLS:
                series[k].append(round(b[k], 5) if b else 0.0)
        total_oe = round(sum(series["oe"]), 3)
        if total_oe <= 0:
            continue
        lm = latest_month.get(npdid)
        fields.append({
            "id": npdid,
            "name": names.get(npdid, npdid),
            "status": m.get("status", "Ikke i kartlag"),
            "operator": m.get("operator", "Ukjent"),
            "hcType": m.get("hcType", "Ukjent"),
            "area": m.get("area", "Ukjent"),
            "discovered": m.get("discovered"),
            "hasGeom": npdid in meta,
            "firstYear": min(y for y, b in byyear.items() if b["oe"] > 0),
            "lastYear": lm[0] if lm else None,
            "totalOe": total_oe,
            "s": series,
            "res": reserves.get(npdid),
        })

    fields.sort(key=lambda f: -f["totalOe"])
    print(f"  {len(fields)} felt/innretninger med produksjon "
          f"({sum(1 for f in fields if f['hasGeom'])} med geometri)")

    out = {
        "meta": {
            "generated": date.today().isoformat(),
            "source": "Sokkeldirektoratet (sodir.no) - NLOD",
            "yearMin": y0,
            "yearMax": y1,
            "lastDataYear": last_y,
            "lastDataMonth": last_m,
            "partialYear": last_y if last_m < 12 else None,
            "units": {
                "oil": "mill Sm3", "gas": "mrd Sm3", "ngl": "mill Sm3",
                "con": "mill Sm3", "oe": "mill Sm3 o.e.", "wat": "mill Sm3",
            },
        },
        "fields": fields,
        "geo": geo,
    }

    with open("data.json", "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, separators=(",", ":"))
    import os
    print(f"OK -> data.json ({os.path.getsize('data.json')/1e6:.2f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

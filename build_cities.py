"""
Bygger cities.json: norske kysttettsteder med > 5000 innbyggere.

Kilder:
  - Folketall : SSB tabell 04859 "Areal og befolkning i tettsteder" (data.ssb.no, aapen API)
  - Koordinat : Kartverket stedsnavn-API (ws.geonorge.no/stedsnavn/v1, aapent)
  - Kystlinje : Natural Earth 10m coastline (public domain) - for aa avgjore hva som er "kyst"
"""

import json
import math
import re
import time
import urllib.parse
import urllib.request

SSB = "https://data.ssb.no/api/v0/no/table/04859"
GEO = "https://ws.geonorge.no/stedsnavn/v1/sted"
UA = {"User-Agent": "sokkel-mvp/1.0", "Content-Type": "application/json"}

MIN_POP = 5000
MAX_KM_TO_COAST = 15.0
NO_BBOX = (3.0, 57.0, 32.0, 72.0)  # lon_min, lat_min, lon_max, lat_max


def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120).read()


def post(url, payload):
    body = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=body, headers=UA, method="POST")
    return urllib.request.urlopen(req, timeout=180).read()


# ---------- 1. folketall fra SSB ----------
def ssb_population():
    meta = json.loads(get(SSB))
    var = {v["code"]: v for v in meta["variables"]}
    cc = var["ContentsCode"]
    # velg folketall ('Bosatte'), ikke areal
    idx = next((i for i, c in enumerate(cc["values"]) if c.lower().startswith("bosat")), None)
    if idx is None:
        idx = next((i for i, t in enumerate(cc["valueTexts"]) if "bosat" in t.lower()), 0)
    code = cc["values"][idx]
    year = var["Tid"]["values"][-1]
    print(f"  SSB 04859: variabel='{cc['valueTexts'][idx]}' aar={year}")

    q = {"query": [
        {"code": "TettSted", "selection": {"filter": "all", "values": ["*"]}},
        {"code": "ContentsCode", "selection": {"filter": "item", "values": [code]}},
        {"code": "Tid", "selection": {"filter": "item", "values": [year]}},
    ], "response": {"format": "json-stat2"}}
    d = json.loads(post(SSB, q))

    dim = d["dimension"]["TettSted"]["category"]
    labels = dim["label"]
    order = sorted(dim["index"], key=lambda k: dim["index"][k])
    vals = d["value"]

    out = []
    for i, key in enumerate(order):
        v = vals[i] if i < len(vals) else None
        if v is None:
            continue
        out.append({"code": key, "label": labels[key], "pop": int(v)})
    print(f"  {len(out)} tettsteder, {sum(1 for o in out if o['pop'] >= MIN_POP)} med >= {MIN_POP}")
    return [o for o in out if o["pop"] >= MIN_POP], year


# ---------- 2. koordinater fra Kartverket ----------
def clean(label):
    s = re.sub(r"\s*\(.*?\)", "", label).strip()
    return s.split("/")[0].strip()


PREF = ("By", "Tettsted", "Tettbebyggelse", "Bydel", "Grend")


def _xy(h):
    """Kartverket kan gi Point, MultiPoint eller nested koordinater."""
    c = h.get("geojson", {}).get("geometry", {}).get("coordinates")
    while isinstance(c, list) and c and isinstance(c[0], list):
        c = c[0]
    if not (isinstance(c, list) and len(c) >= 2):
        return None
    try:
        return [round(float(c[0]), 4), round(float(c[1]), 4)]
    except (TypeError, ValueError):
        return None


def _meta(h):
    kom = (h.get("kommuner") or [{}])[0].get("kommunenavn")
    fyl = (h.get("fylker") or [{}])[0].get("fylkesnavn")
    return kom, fyl


def geocode(name):
    url = f"{GEO}?{urllib.parse.urlencode({'sok': name, 'treffPerSide': 12, 'utkoordsys': 4258})}"
    try:
        d = json.loads(get(url))
    except Exception:
        return None
    hits = d.get("navn", [])
    if not hits:
        return None
    exact = [h for h in hits
             if str(h.get("skrivemåte", h.get("skrivemate", ""))).lower() == name.lower()] or hits
    for t in PREF:
        for h in exact:
            if h.get("navneobjekttype") == t:
                xy = _xy(h)
                if xy:
                    return (xy, *_meta(h))
    for h in exact:
        xy = _xy(h)
        if xy:
            return (xy, *_meta(h))
    return None


# ---------- 3. avstand til kyst ----------
def coast_points():
    gj = json.loads(open("ne_coastline.geojson", encoding="utf-8").read())
    pts = []
    lo0, la0, lo1, la1 = NO_BBOX
    for f in gj["features"]:
        g = f.get("geometry") or {}
        lines = [g["coordinates"]] if g.get("type") == "LineString" else g.get("coordinates", [])
        for ln in lines:
            for x, y in ln:
                if lo0 <= x <= lo1 and la0 <= y <= la1:
                    pts.append((x, y))
    print(f"  kystpunkt innenfor Norge-bbox: {len(pts)}")
    return pts


def km(a, b):
    dx = (a[0] - b[0]) * 111.32 * math.cos(math.radians((a[1] + b[1]) / 2))
    dy = (a[1] - b[1]) * 110.57
    return math.hypot(dx, dy)


def main():
    print("Henter folketall fra SSB ...")
    towns, year = ssb_population()

    print("Henter koordinater fra Kartverket ...")
    coast = coast_points()
    cities, missing = [], []
    for i, t in enumerate(towns, 1):
        nm = clean(t["label"])
        g = geocode(nm)
        if not g:
            missing.append(nm)
            continue
        (lon, lat), kom, fyl = g
        d = min(km((lon, lat), c) for c in coast) if coast else 999
        if d <= MAX_KM_TO_COAST:
            cities.append({"n": nm, "p": t["pop"], "c": [lon, lat],
                           "km": round(d, 1), "kom": kom, "fyl": fyl})
        if i % 20 == 0:
            print(f"    {i}/{len(towns)} …")
        time.sleep(0.05)

    cities.sort(key=lambda c: -c["p"])
    print(f"\n  {len(cities)} kysttettsteder (<= {MAX_KM_TO_COAST} km fra kyst)")
    print(f"  ikke funnet: {len(missing)} {missing[:10]}")
    print("  topp 12:", ", ".join(f"{c['n']} ({c['p']//1000}k)" for c in cities[:12]))

    json.dump({"year": year, "minPop": MIN_POP, "source": "SSB 04859 + Kartverket stedsnavn",
               "cities": cities}, open("cities.json", "w", encoding="utf-8"),
              ensure_ascii=False, separators=(",", ":"))
    print("OK -> cities.json")


if __name__ == "__main__":
    main()

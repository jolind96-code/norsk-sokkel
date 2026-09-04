"""Bygger power.json: kraftverk pa land i Norge.

Kilder (alle apne, ingen API-nokkel):
  Vannkraft   NVE api.nve.no/web/Powerplant/GetHydroPowerPlantsInOperation  (NLOD)
              + koordinater fra GeoNorge WFS wfs.vannkraft, EL_Kraftstasjon
              Kobling: WFS vannkraftverkNr == NVE VannKraftverkID
  Vindkraft   NVE api.nve.no/web/WindPowerplant/GetWindPowerPlantsInOperation (NLOD)
              + koordinater fra NVE GIS VindkraftView1, koblet pa anleggsNr

Spotpris hentes i nettleseren fra hvakosterstrommen.no, ikke her - den skal
vaere fersk hver gang siden apnes.
"""
import json
import os
import urllib.request
import xml.etree.ElementTree as ET

UA = {"User-Agent": "sokkel-mvp (apne data)"}

NVE_HYDRO = "https://api.nve.no/web/Powerplant/GetHydroPowerPlantsInOperation"
NVE_WIND = "https://api.nve.no/web/WindPowerplant/GetWindPowerPlantsInOperation"
WFS = ("https://wfs.geonorge.no/skwms1/wfs.vannkraft?service=WFS&request=GetFeature"
       "&version=2.0.0&typeNames=app:EL_Kraftstasjon&srsName=urn:ogc:def:crs:EPSG::4326")
GIS_WIND = ("https://gis3.nve.no/arcgis/rest/services/mapservice/VindkraftView1/"
            "MapServer/{lag}/query?where=1%3D1&outFields=anleggsNr&returnGeometry=true"
            "&outSR=4326&f=json")

MIN_MW = 1.0          # dropp mikrokraftverk - de er mange og bidrar lite

# Noen "vindkraft"-anlegg fra NVEs onshore-API er egentlig FLYTENDE HAVVIND
# (testanlegg til havs, ikke landbasert produksjon) - matches pa navn siden
# NVE-APIet ikke har et eget land/hav-flagg. Flagges "offshore":true her sa
# de kan vises i Hav-modulen i stedet for Land i index.html.
OFFSHORE_VIND_NAVN = {"METCentre Karmøy"}


def get_json(url, timeout=240):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", errors="replace"))


def hydro_coords():
    """vannkraftverkNr -> [lon, lat] fra GeoNorge WFS."""
    print("laster kraftstasjoner fra GeoNorge WFS ...")
    with urllib.request.urlopen(urllib.request.Request(WFS, headers=UA), timeout=600) as r:
        raw = r.read()
    print(f"  {round(len(raw)/1024/1024, 1)} MB")
    root = ET.fromstring(raw)

    out = {}
    for st in root.iter():
        if not st.tag.endswith("EL_Kraftstasjon"):
            continue
        nr = pos = None
        for c in st.iter():
            tag = c.tag.split("}")[-1]
            if tag == "vannkraftverkNr":
                nr = (c.text or "").strip()
            elif tag == "pos":
                pos = (c.text or "").strip()
        if not nr or not pos:
            continue
        try:
            lat, lon = (float(v) for v in pos.split()[:2])   # WFS gir lat lon
        except ValueError:
            continue
        out.setdefault(nr, [round(lon, 5), round(lat, 5)])
    print(f"  {len(out)} kraftstasjoner med koordinat")
    return out


def wind_coords():
    """anleggsNr -> [lon, lat] fra NVEs vindkraft-GIS."""
    print("laster vindkraft-koordinater fra NVE GIS ...")
    out = {}
    for lag in range(7):
        try:
            d = get_json(GIS_WIND.format(lag=lag), timeout=120)
        except Exception as e:
            print(f"  lag {lag}: {e}")
            continue
        for f in d.get("features", []):
            a = f["attributes"].get("anleggsNr")
            g = f.get("geometry") or {}
            if a and g.get("x"):
                out.setdefault(str(a), [round(g["x"], 5), round(g["y"], 5)])
    print(f"  {len(out)} anleggsnummer med koordinat")
    return out


def main():
    hc = hydro_coords()
    wc = wind_coords()

    print("laster vannkraftverk fra NVE ...")
    hydro = get_json(NVE_HYDRO)
    print(f"  {len(hydro)} vannkraftverk i drift")

    print("laster vindkraftverk fra NVE ...")
    wind = get_json(NVE_WIND)
    print(f"  {len(wind)} vindkraftverk i drift")

    plants, mangler_h = [], 0
    for p in hydro:
        mw = p.get("MaksYtelse") or 0
        if mw < MIN_MW:
            continue
        c = hc.get(str(p.get("VannKraftverkID")))
        if not c:
            mangler_h += 1
            continue
        plants.append({
            "k": "vann",
            "n": (p.get("Navn") or "").strip(),
            "c": c,
            "mw": round(float(mw), 1),
            "gwh": round(float(p.get("MidProd_91_20") or 0), 1),
            "eier": (p.get("HovedEier") or "").strip().title(),
            "omr": f"NO{p.get('ElspotomraadeNummer')}" if p.get("ElspotomraadeNummer") else "",
            "fylke": (p.get("Fylke") or "").strip(),
            "aar": p.get("DatoForEldsteKraftproduserendeDel") or None,
        })

    mangler_w = []
    for p in wind:
        c = wc.get(str(p.get("AnleggsNr")))
        if not c:
            mangler_w.append(p.get("Navn"))
            continue
        plants.append({
            "k": "vind",
            "n": (p.get("Navn") or "").strip(),
            "c": c,
            "mw": round(float(p.get("InstallertEffekt_MW") or 0), 1),
            "gwh": round(float(p.get("NormalAArsproduksjon_GWh") or 0), 1),
            "eier": (p.get("HovedEierNavn") or "").strip().title(),
            "omr": f"NO{p.get('ElspotomraadeNummer')}" if p.get("ElspotomraadeNummer") else "",
            "fylke": (p.get("Fylke") or "").strip(),
            "aar": int(str(p.get("IdriftsettelseForsteByggetrinn") or "0")[:4]) or None,
            "turb": p.get("AntallOperativeTurbiner"),
            "offshore": (p.get("Navn") or "").strip() in OFFSHORE_VIND_NAVN,
        })

    plants.sort(key=lambda x: -x["mw"])

    # summer per prisomrade - brukes til inntekt per omrade i nettleseren.
    # Havvind (offshore) holdes utenfor - den hoerer til Hav-modulen, ikke
    # "stroem paa land"-tallene.
    omr = {}
    for p in plants:
        if p.get("offshore"):
            continue
        o = p["omr"] or "ukjent"
        d = omr.setdefault(o, {"vann_mw": 0.0, "vind_mw": 0.0,
                               "vann_gwh": 0.0, "vind_gwh": 0.0, "n": 0})
        d[f"{p['k']}_mw"] += p["mw"]
        d[f"{p['k']}_gwh"] += p["gwh"]
        d["n"] += 1
    for d in omr.values():
        for k in d:
            if k != "n":
                d[k] = round(d[k], 1)

    data = {
        "kilde": "NVE (api.nve.no) og GeoNorge WFS vannkraft - NLOD",
        "minMW": MIN_MW,
        "omrader": omr,
        "verk": plants,
    }
    with open("power.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))

    v = [p for p in plants if p["k"] == "vann"]
    w = [p for p in plants if p["k"] == "vind"]
    print(f"\nvannkraft: {len(v)} verk, {round(sum(p['mw'] for p in v)):,} MW, "
          f"{round(sum(p['gwh'] for p in v)):,} GWh/ar".replace(",", " "))
    print(f"vindkraft: {len(w)} verk, {round(sum(p['mw'] for p in w)):,} MW, "
          f"{round(sum(p['gwh'] for p in w)):,} GWh/ar".replace(",", " "))
    print(f"utelatt vannkraft uten koordinat: {mangler_h}")
    print(f"utelatt vindkraft uten koordinat: {mangler_w}")
    print(f"power.json: {round(os.path.getsize('power.json')/1024, 1)} KB")
    print("\ntopp 5:")
    for p in plants[:5]:
        print(f"  {p['n'][:26]:<27}{p['mw']:>8.0f} MW  {p['gwh']:>8.0f} GWh  {p['omr']}  {p['eier'][:24]}")


if __name__ == "__main__":
    main()

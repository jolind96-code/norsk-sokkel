"""Bygger facilities.json: innretninger per felt, klassifisert etter type.

Kilde: Sokkeldirektoratet, tabell facility_fixed (NLOD).
  fclSurface = Y/N  -> star innretningen over vann?
  fclKind           -> konstruksjonstype
Merk: koordinatene er oppgitt i ED50 for de fleste rader. Avviket mot WGS84 er
ca. 100-200 m, som er uten betydning i kartmalestokken vi bruker.
"""
import csv
import json
import os
import urllib.request

CSV_URL = ("https://factpages.sodir.no/public?/Factpages/external/tableview/facility_fixed"
           "&rs:Command=Render&rc:Toolbar=false&rc:Parameters=f&IpAddress=not_used"
           "&CultureCode=en&rs:Format=CSV&Top100=false")

# Innretningstype -> ikonkategori
KIND_MAP = {
    "CONDEEP": "gbs", "TLP CONCRETE": "gbs", "SEMISUB CONCRETE": "gbs",
    "CONCRETE STRUCTURE": "gbs", "MONOTOWER": "jacket",
    "JACKET": "jacket", "JACK-UP": "jacket", "MOPUSTOR": "jacket",
    "FPSO": "fpso", "FSU": "fpso", "FLOATING": "fpso",
    "SEMISUB": "semi", "TLP": "semi", "SPAR": "semi",
    "MULTI WELL TEMPLATE": "subsea", "SINGLE WELL TEMPLATE": "subsea",
    "SUBSEA STRUCTURE": "subsea",
    "ONSHORE FACILITY": "onshore", "LANDFALL": "onshore",
    "OFFSHORE WIND TURBINE": "wind", "LOADING SYSTEM": "loading",
}

# Rangering: hvilken innretning representerer feltet i kartet
PRIORITY = ["gbs", "fpso", "semi", "jacket", "loading", "subsea", "onshore", "wind"]

SKIP_PHASES = {"REMOVED", "DISPOSAL COMPLETED", "DECOMMISSIONED"}


def classify(kind: str) -> str:
    k = (kind or "").upper()
    for pattern, cat in KIND_MAP.items():
        if k.startswith(pattern) or pattern in k:
            return cat
    return "other"


def dms(deg: str, minute: str, sec: str, code: str):
    try:
        v = float(deg or 0) + float(minute or 0) / 60 + float(sec or 0) / 3600
    except ValueError:
        return None
    if (code or "").upper() in ("S", "W"):
        v = -v
    return round(v, 5)


def main():
    print("laster facility_fixed ...")
    req = urllib.request.Request(CSV_URL, headers={"User-Agent": "sokkel-mvp"})
    with urllib.request.urlopen(req, timeout=300) as r:
        raw = r.read().decode("utf-8-sig", errors="replace")
    rows = list(csv.DictReader(raw.splitlines()))
    print(f"  {len(rows)} rader")

    by_field: dict[str, list] = {}
    stats: dict[str, int] = {}

    for r in rows:
        if r.get("fclBelongsToKind") != "FIELD":
            continue
        if r.get("fclPhase") in SKIP_PHASES:
            continue
        npdid = (r.get("fclBelongsToS") or "").strip()
        if not npdid:
            continue

        cat = classify(r.get("fclKind"))
        if cat in ("wind", "onshore"):
            continue

        lat = dms(r.get("fclNsDeg"), r.get("fclNsMin"), r.get("fclNsSec"), r.get("fclNsCode"))
        lon = dms(r.get("fclEwDeg"), r.get("fclEwMin"), r.get("fclEwSec"), r.get("fclEwCode"))
        if lat is None or lon is None or (lat == 0 and lon == 0):
            continue

        stats[cat] = stats.get(cat, 0) + 1
        by_field.setdefault(npdid, []).append({
            "n": r.get("fclName", "").strip(),
            "k": cat,
            "kind": (r.get("fclKind") or "").strip().title(),
            "surf": r.get("fclSurface") == "Y",
            "c": [lon, lat],
            "depth": (r.get("fclWaterDepth") or "").strip(),
            "start": (r.get("fclStartupDate") or "").strip()[-4:],
            "phase": (r.get("fclPhase") or "").strip(),
        })

    # ett representativt ikon per felt: hoyest prioriterte overflateinnretning
    main_icon = {}
    for npdid, fac in by_field.items():
        surf = [f for f in fac if f["surf"]]
        pool = surf or fac
        pool.sort(key=lambda f: PRIORITY.index(f["k"]) if f["k"] in PRIORITY else 99)
        best = pool[0]
        main_icon[npdid] = {"k": best["k"], "n": best["n"], "c": best["c"],
                            "surface": bool(surf), "count": len(fac),
                            "nSurf": len(surf)}

    out = {
        "source": "Sokkeldirektoratet (sodir.no) - facility_fixed - NLOD",
        "byField": by_field,
        "mainIcon": main_icon,
    }
    with open("facilities.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))

    print(f"\nfelt med innretninger: {len(by_field)}")
    print(f"felt med overflateinnretning: {sum(1 for v in main_icon.values() if v['surface'])}")
    print(f"felt kun havbunn: {sum(1 for v in main_icon.values() if not v['surface'])}")
    print("\nfordeling (alle innretninger):")
    for k, v in sorted(stats.items(), key=lambda x: -x[1]):
        print(f"  {v:>4}  {k}")
    print(f"\nfacilities.json: {round(os.path.getsize('facilities.json') / 1024, 1)} KB")


if __name__ == "__main__":
    main()

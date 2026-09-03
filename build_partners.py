"""Bygger partners.json: gjeldende rettighetshavere og eierandeler per felt.

Kilde: Sokkeldirektoratet, DataService lag 7108 (field_licensee_hst), NLOD.
Tabellen er historisk - gjeldende eierskap = rader der fldLicenseeTo er tom.
"""
import datetime
import json
import os
import urllib.parse
import urllib.request

BASE = ("https://factmaps.sodir.no/api/rest/services/DataService/Data/"
        "FeatureServer/7108/query")
PAGE = 2000


def fetch(offset: int):
    q = {
        "where": "fldLicenseeTo IS NULL",
        "outFields": ("fldNpdidField,fldName,cmpLongName,fldCompanyShare,"
                      "fldSdfiShare,fldLicenseeFrom,fldLicenseeDateUpdated"),
        "returnGeometry": "false",
        "f": "json",
        "resultOffset": str(offset),
        "resultRecordCount": str(PAGE),
        "orderByFields": "fldNpdidField,fldCompanyShare DESC",
    }
    url = BASE + "?" + urllib.parse.urlencode(q)
    req = urllib.request.Request(url, headers={"User-Agent": "sokkel-mvp"})
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read().decode("utf-8", errors="replace"))


def main():
    rows, offset = [], 0
    while True:
        d = fetch(offset)
        feats = d.get("features", [])
        rows += [f["attributes"] for f in feats]
        print(f"  offset {offset}: {len(feats)} rader")
        if len(feats) < PAGE:
            break
        offset += PAGE

    by_field: dict[str, list] = {}
    from_ms: dict[str, int] = {}
    for a in rows:
        npdid = str(a.get("fldNpdidField") or "").strip()
        name = (a.get("cmpLongName") or "").strip()
        share = a.get("fldCompanyShare")
        if not npdid or not name or share is None:
            continue
        by_field.setdefault(npdid, []).append([name, round(float(share), 4)])
        # REST-API-et gir datoer som epoch-millisekunder
        fr = a.get("fldLicenseeFrom")
        if isinstance(fr, (int, float)) and fr > 0:
            from_ms[npdid] = max(from_ms.get(npdid, 0), int(fr))

    # sorter synkende og fjern duplikater
    out = {}
    for k, v in by_field.items():
        seen, clean = set(), []
        for name, share in sorted(v, key=lambda x: -x[1]):
            if name in seen:
                continue
            seen.add(name)
            clean.append([name, share])
        entry = {"p": clean}
        if k in from_ms:
            d = datetime.datetime.fromtimestamp(from_ms[k] / 1000, datetime.timezone.utc)
            entry["fra"] = d.strftime("%d.%m.%Y")
        out[k] = entry

    with open("partners.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))

    sums = [sum(s for _, s in v["p"]) for v in out.values()]
    ok = sum(1 for s in sums if 99 <= s <= 101)
    print(f"\nfelt med partnere: {len(out)}")
    print(f"summerer til ~100 %: {ok} av {len(out)}")
    print(f"med gyldig-fra-dato: {sum(1 for v in out.values() if 'fra' in v)}")
    print(f"partners.json: {round(os.path.getsize('partners.json')/1024, 1)} KB")
    for k in list(out)[:2]:
        print(f"  {k}: fra {out[k].get('fra')} · {out[k]['p'][:2]}")


if __name__ == "__main__":
    main()

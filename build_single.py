"""Bygger en enkeltfil-versjon som kan deles direkte pa Teams eller e-post.

Alle datafiler bakes inn i HTML-en, slik at fila kan apnes ved a dobbeltklikke.
Uten dette blokkerer nettleseren fetch() fra file:// og siden blir staende tom.
"""
import json
import os
import re

SRC = "index.html"
OUT = "norsk-sokkel.html"
EMBED = ["data.json", "cities.json", "ncs.geojson", "prices.json", "facilities.json",
         "partners.json", "power.json", "omrader.geojson", "energiformer.json"]
VENDOR = ["vendor/maplibre-gl.css", "vendor/maplibre-gl.js", "vendor/echarts.min.js"]

html = open(SRC, encoding="utf-8").read()

# 0) bake inn kartbibliotek (MapLibre) og diagrambibliotek (ECharts) som
#    rene tekstblokker, sa fila fungerer helt uten unpkg/jsdelivr - kun
#    kartflisene (openfreemap.org) krever fortsatt nett.
for path in VENDOR:
    if not os.path.exists(path):
        raise SystemExit(f"FANT IKKE {path} - kjor nedlasting til vendor/ forst")
    print(f"  bakte inn {path}  ({round(os.path.getsize(path)/1024,1)} KB)")
css = open("vendor/maplibre-gl.css", encoding="utf-8").read()
maplibre_js = open("vendor/maplibre-gl.js", encoding="utf-8").read()
echarts_js = open("vendor/echarts.min.js", encoding="utf-8").read()
html = html.replace(
    '<link rel="stylesheet" href="vendor/maplibre-gl.css">',
    f"<style>{css}</style>")
html = html.replace(
    '<script src="vendor/maplibre-gl.js"></script>',
    f"<script>{maplibre_js}</script>")
html = html.replace(
    '<script src="vendor/echarts.min.js"></script>',
    f"<script>{echarts_js}</script>")

# 1) bygg innebygde konstanter
blobs = []
for name in EMBED:
    if not os.path.exists(name):
        print(f"  hopper over {name} (finnes ikke)")
        continue
    data = json.load(open(name, encoding="utf-8-sig"))
    var = "__" + re.sub(r"\W", "_", name).upper() + "__"
    blobs.append(f"const {var}={json.dumps(data, ensure_ascii=False, separators=(',', ':'))};")
    print(f"  bakte inn {name} -> {var}  ({round(os.path.getsize(name)/1024,1)} KB)")

# 2) bytt ut fetch-kall og kartkilder med de innebygde dataene
repl = {
    "fetch('data.json').then(r=>r.json())":
        "Promise.resolve(__DATA_JSON__)",
    "fetch('cities.json').then(r=>r.json())":
        "Promise.resolve(__CITIES_JSON__)",
    "fetch('prices.json').then(r=>r.json())":
        "Promise.resolve(__PRICES_JSON__)",
    "fetch('facilities.json').then(r=>r.json())":
        "Promise.resolve(__FACILITIES_JSON__)",
    "fetch('partners.json').then(r=>r.json())":
        "Promise.resolve(__PARTNERS_JSON__)",
    "POW=await (await fetch('power.json')).json();":
        "POW=__POWER_JSON__;",
    "OMR=await (await fetch('omrader.geojson')).json();":
        "OMR=__OMRADER_GEOJSON__;",
    "data:'ncs.geojson'":
        "data:__NCS_GEOJSON__",
    "fetch('energiformer.json').then(r=>r.json())":
        "Promise.resolve(__ENERGIFORMER_JSON__)",
}
misses = [k for k in repl if k not in html]
if misses:
    raise SystemExit("FANT IKKE monsteret(e) - index.html er endret:\n  " + "\n  ".join(misses))
for old, new in repl.items():
    html = html.replace(old, new)

# 3) sett inn konstantene forst i skriptblokken
marker = "<script>"
i = html.rindex(marker)
html = html[:i + len(marker)] + "\n" + "\n".join(blobs) + "\n" + html[i + len(marker):]

# 4) liten fotnote om at kartfliser krever nett
# NB: bruk rindex/siste forekomst - vendor-bibliotekene (bl.a. echarts) kan
# selv inneholde literal-strengen "</body>" i egen kildekode (f.eks. i en
# bilde-eksport-funksjon), og et vanlig .replace() ville da ogsa truffet og
# odelagt den koden.
i = html.rindex("</body>")
html = (html[:i]
        + "<!-- Enkeltfil-versjon. MapLibre og ECharts er bakt inn og krever ikke nett. "
          "Kartfliser (openfreemap.org) krever fortsatt nett. -->\n"
        + html[i:])

open(OUT, "w", encoding="utf-8").write(html)
print(f"\n{OUT}: {round(os.path.getsize(OUT)/1024/1024, 2)} MB")

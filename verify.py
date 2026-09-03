"""Headless-verifisering av dashboardet: fanger konsollfeil, leser DOM, tar skjermbilde."""
import json
import sys
from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:8765/index.html"
SHOT = sys.argv[1] if len(sys.argv) > 1 else "shot.png"

PROBE = """() => {
  const t = s => { const e = document.querySelector(s); return e ? e.textContent.trim() : 'MANGLER'; };
  return {
    felt: typeof filtered !== 'undefined' ? filtered.length : null,
    totalt: typeof D !== 'undefined' && D ? D.fields.length : null,
    unit: typeof unit !== 'undefined' ? unit : null,
    kumulativ: typeof cum !== 'undefined' ? cum : null,
    aar: typeof year !== 'undefined' ? year : null,
    operatorer: document.getElementById('cop') ? document.getElementById('cop').options.length : 0,
    opForste: document.getElementById('cop')
        ? Array.from(document.getElementById('cop').options).slice(1, 4).map(o => o.text) : [],
    aktiv: t('#active'),
    tsscope: t('#tsscope'),
    kpi: Array.from(document.querySelectorAll('#kpis .kpi')).map(
        k => k.querySelector('.k').textContent + ' = ' +
             k.querySelector('.v').textContent + ' ' +
             k.querySelector('.u').textContent),
    kart: !!document.querySelector('.maplibregl-canvas'),
    feltNavnSynlige: typeof map !== 'undefined' && map.getLayer && map.getLayer('lbl')
        ? map.queryRenderedFeatures({layers: ['lbl']}).length : 'n/a',
    punkter: typeof map !== 'undefined' && map.getSource && map.getSource('pts')
        ? (map.getSource('pts')._data.features || []).length : 'n/a',
  };
}"""

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1600, "height": 950})
    errors, console = [], []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.on("console", lambda m: console.append(f"{m.type}: {m.text}") if m.type == "error" else None)

    pg.goto(URL, wait_until="networkidle")
    pg.wait_for_timeout(3500)

    print("=== SIDEFEIL ===")
    print("\n".join(errors) if errors else "ingen")
    print("\n=== KONSOLLFEIL ===")
    print("\n".join(console) if console else "ingen")

    print("\n=== TILSTAND ===")
    print(json.dumps(pg.evaluate(PROBE), indent=1, ensure_ascii=False))

    pg.screenshot(path=SHOT, full_page=False)
    print(f"\nSkjermbilde: {SHOT}")
    b.close()

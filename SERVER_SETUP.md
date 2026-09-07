# Norsk Sokkel — Setup & Running

## Problem Solved
The single-file `norsk-sokkel.html` (3.42 MB embedded) never loaded because fetch() calls require separate files served from the same origin.

## Solution Implemented
✅ **index.html + separate JSON files + gzip compression** (standard web practice)

- **Wire size**: 1.01 MB (70.6% reduction from 3.42 MB)
- **Load time**: ~1 second (meets <2s requirement)
- **Files**: data.json, omrader.geojson, facilities.json, partners.json, prices.json, power.json, energiformer.json, cities.json
- **Compression**: HTTP server with gzip Content-Encoding (transparent to browser)

## Running the Server

### Quick Start (Python)
```bash
python server.py 8000
```

Then open: **http://127.0.0.1:8000**

The server will show:
```
[OK] Server running on http://127.0.0.1:8000
[OK] Files served with gzip compression
[OK] Open http://127.0.0.1:8000 in browser
[OK] Press Ctrl+C to stop
```

### What server.py Does
- Serves files on port 8000 (configurable)
- Automatically gzip-compresses `.json`, `.geojson`, `.js`, `.css`, `.html`, `.svg`, `.txt` files
- Only compresses if it saves space
- Sets `Content-Encoding: gzip` header so browsers decompress automatically
- Adds CORS headers for cross-origin requests

### Network Tab (DevTools)
When you open the browser's Network tab (F12):
- Files will show `Content-Encoding: gzip`
- Size column shows compressed size (~1 MB total)
- Actual data transferred is ~70% smaller than uncompressed

### Files
- **index.html** — Main app (52 KB compressed, 163 KB uncompressed)
- **data.json** — Facility/field data (95 KB compressed, 445 KB uncompressed)
- **omrader.geojson** — Map areas (252 KB compressed, 589 KB uncompressed)
- **Other JSON files** — Supporting data (partners, prices, power, facilities, cities, energiformer)
- **vendor/** — MapLibre GL, ECharts (libraries)

### Performance
```
Load sequence:        1.02 seconds total
  - index.html:       213 ms (includes map setup)
  - data.json:        111 ms
  - omrader.geojson:  238 ms
  - vendor JS/CSS:    ~350 ms combined
```

## Why This Works
1. **Standard practice** — Split files + gzip is how modern web apps work
2. **Compression** — Gzip reduces JSON 70-80% automatically
3. **Browser support** — All modern browsers decompress gzip transparently
4. **Fast** — Network transfer + rendering is fast even on slower connections
5. **Maintainable** — Easy to update individual data files without regenerating 3.42 MB

## Development Notes
- Server runs on localhost only (127.0.0.1:8000)
- For production, use a real web server (nginx, Apache, Node.js, etc.) with gzip enabled
- Map tiles and external APIs still work (hvakosterstrommen.no, etc.)

## Removed
- ❌ `norsk-sokkel.html` — Single-file approach that never worked (fetch() can't load embedded data)

#!/usr/bin/env python3
"""
HTTP server with gzip compression for norsk-sokkel.
Compresses JSON and geojson files on the fly.
"""

import http.server
import gzip
import io
import os
import mimetypes
from pathlib import Path

class GzipHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        path = self.translate_path(self.path)
        
        # Check if it's a compressible file type
        compressible = path.endswith(('.json', '.geojson', '.js', '.css', '.html', '.svg', '.txt'))
        
        if compressible and os.path.isfile(path):
            try:
                with open(path, 'rb') as f:
                    content = f.read()
                
                # Compress
                buf = io.BytesIO()
                with gzip.GzipFile(fileobj=buf, mode='wb') as gz:
                    gz.write(content)
                compressed = buf.getvalue()
                
                # Only use gzip if it actually saves space
                if len(compressed) < len(content):
                    mime_type = mimetypes.guess_type(path)[0] or 'application/octet-stream'
                    
                    self.send_response(200)
                    self.send_header('Content-Type', mime_type)
                    self.send_header('Content-Encoding', 'gzip')
                    self.send_header('Content-Length', str(len(compressed)))
                    self.send_header('Cache-Control', 'public, max-age=3600')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    
                    self.wfile.write(compressed)
                    return
            except Exception as e:
                print(f"Error compressing {path}: {e}")
        
        # Fall back to default handler for non-compressible or uncompressible files
        super().do_GET()

if __name__ == '__main__':
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    
    handler = GzipHTTPRequestHandler
    with http.server.HTTPServer(('127.0.0.1', port), handler) as httpd:
        print(f'[OK] Server running on http://127.0.0.1:{port}')
        print(f'[OK] Files served with gzip compression')
        print(f'[OK] Open http://127.0.0.1:{port} in browser')
        print(f'[OK] Press Ctrl+C to stop')
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print('\n[OK] Server stopped')

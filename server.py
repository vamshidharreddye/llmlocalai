"""
Simple HTTP server to serve the UI
Run: python server.py
Then open: http://localhost:3000
"""

import http.server
import socketserver
from pathlib import Path
import os

PORT = 3000

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        # Change to root directory so files are served correctly
        super().__init__(*args, directory=str(Path(__file__).parent), **kwargs)
    
    def end_headers(self):
        # Add CORS headers for API calls
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

if __name__ == '__main__':
    Handler = MyHTTPRequestHandler
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"🌐 UI Server running at http://localhost:{PORT}")
        print(f"📁 Serving files from: {Path(__file__).parent}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n✋ Server stopped")

#!/usr/bin/env python3
"""Simple HTTP server for mock websites"""

import http.server
import socketserver
import os
import sys

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 3000
DIRECTORY = os.path.dirname(os.path.abspath(__file__))


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)
    
    def log_message(self, format, *args):
        # Suppress logging for cleaner output
        pass


def main():
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"Mock sites server running at http://localhost:{PORT}")
        print(f"Available sites:")
        for name in sorted(os.listdir(DIRECTORY)):
            path = os.path.join(DIRECTORY, name)
            if os.path.isdir(path) and not name.startswith('.'):
                print(f"  - http://localhost:{PORT}/{name}/")
        print(f"\nPress Ctrl+C to stop")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped")


if __name__ == "__main__":
    main()


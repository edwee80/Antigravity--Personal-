#!/usr/bin/env python3
"""
Fort Canning Time Portal - Local Web Server Runner

Run this script to launch a local server and automatically open the Fort Canning
Time Portal interactive website in your default browser.

Usage:
    python fortcanning.py
"""

import http.server
import socket
import socketserver
import sys
import webbrowser
from pathlib import Path

DIRECTORY = Path(__file__).parent.resolve()
HTML_FILE = "fortcanning.html"


def find_available_port(start_port=8080, max_attempts=50):
    """Find an open TCP port on localhost starting from start_port."""
    for port in range(start_port, start_port + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
    return start_port


class LocalFileHandler(http.server.SimpleHTTPRequestHandler):
    """Custom handler serving from current project directory with minimal logging."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DIRECTORY), **kwargs)

    def log_message(self, format, *args):
        # Keep terminal output clean
        pass


def main():
    target_html = DIRECTORY / HTML_FILE

    if not target_html.exists():
        print(f"[!] Error: {HTML_FILE} was not found at {DIRECTORY}")
        sys.exit(1)

    port = find_available_port(8080)
    url = f"http://localhost:{port}/{HTML_FILE}"

    print("=" * 64, flush=True)
    print(" [*] Fort Canning Time Portal is running!", flush=True)
    print(f" [>] URL: {url}", flush=True)
    print(" [>] Opening in your default web browser...", flush=True)
    print(" [x] Press Ctrl+C in this terminal window to stop the server.", flush=True)
    print("=" * 64, flush=True)

    # Automatically open the site in the default browser
    webbrowser.open(url)

    # Start the local server
    try:
        with socketserver.TCPServer(("127.0.0.1", port), LocalFileHandler) as httpd:
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[i] Server stopped cleanly. Goodbye!")
    except Exception as e:
        print(f"\n[!] Server error: {e}")
        print("[i] Opening directly via file protocol fallback...")
        webbrowser.open(target_html.as_uri())


if __name__ == "__main__":
    main()
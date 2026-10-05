#!/usr/bin/env python3
"""
CIVIL & STRUCTURAL ENGINEERING RESUME WEB SERVER (PYTHON)

Starts a local HTTP server rendering the Jinja2 template with data from data.py.
Includes API endpoints, static file serving, and static HTML compilation.

Usage:
    py app.py              # Start server and open browser
    py app.py --port 8000  # Start on specific port
    py app.py --build      # Export static index.html
"""

import sys
import os
import json
import mimetypes
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

# Import resume data
try:
    from data import RESUME_DATA
except ImportError:
    print("Error: data.py not found in the current directory.")
    sys.exit(1)

# Jinja2 environment setup
try:
    import jinja2
    TEMPLATE_DIR = Path(__file__).parent / "templates"
    jinja_env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=jinja2.select_autoescape(["html", "xml"])
    )
    import markupsafe
    jinja_env.filters["tojson"] = lambda obj: markupsafe.Markup(json.dumps(obj))
except ImportError:
    print("Warning: Jinja2 is required for server-side rendering. Install with: py -m pip install jinja2")
    sys.exit(1)


def get_template_context() -> dict:
    """Prepare context dictionary for the template."""
    categories = sorted(list({p.get("category", "") for p in RESUME_DATA.get("projects", [])}))
    return {
        **RESUME_DATA,
        "project_categories": categories,
    }


def render_html() -> str:
    """Render the Jinja2 index.html template with data."""
    template = jinja_env.get_template("index.html")
    context = get_template_context()
    return template.render(**context)


def build_static(output_path: str = "index.html") -> None:
    """Export pre-rendered HTML to a static file."""
    html_content = render_html()
    dest = Path(__file__).parent / output_path
    with open(dest, "w", encoding="utf-8") as f:
        f.write(html_content)
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass
    print(f"[OK] Static site successfully built to: {dest.resolve()}")


class ResumeRequestHandler(BaseHTTPRequestHandler):
    """HTTP Request Handler serving resume pages, APIs, and static assets."""

    def log_message(self, format, *args):
        # Clean terminal logging
        sys.stdout.write(f"[{self.log_date_time_string()}] {self.command} {self.path}\n")

    def do_GET(self):
        base_dir = Path(__file__).parent

        # 1. Main Page
        if self.path == "/" or self.path == "/index.html":
            try:
                html_body = render_html().encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(html_body)))
                self.end_headers()
                self.wfile.write(html_body)
            except Exception as e:
                self.send_error(500, f"Template rendering error: {e}")
            return

        # 2. JSON API: Full Resume Data
        if self.path == "/api/resume":
            data_bytes = json.dumps(RESUME_DATA, indent=2).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(data_bytes)))
            self.end_headers()
            self.wfile.write(data_bytes)
            return

        # 3. JSON API: Projects Only
        if self.path == "/api/projects":
            projects_bytes = json.dumps(RESUME_DATA.get("projects", []), indent=2).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(projects_bytes)))
            self.end_headers()
            self.wfile.write(projects_bytes)
            return

        # 4. Static Files (/static/* or direct root files like /styles.css)
        file_path = None
        clean_path = self.path.split("?")[0].lstrip("/")

        # Check in static directory first, then root directory
        candidate_static = base_dir / clean_path
        if candidate_static.is_file():
            file_path = candidate_static
        elif (base_dir / "static" / clean_path).is_file():
            file_path = base_dir / "static" / clean_path

        if file_path and file_path.is_file():
            mime_type, _ = mimetypes.guess_type(str(file_path))
            mime_type = mime_type or "application/octet-stream"

            try:
                with open(file_path, "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", mime_type)
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
                return
            except OSError:
                self.send_error(404, "File Not Found")
                return

        # Not found fallback
        self.send_error(404, "Not Found")


def run_server(port: int = 5000, open_browser: bool = True) -> None:
    """Start the Python HTTP server and optionally open the browser."""
    # Try specified port, fall back to next free port if occupied
    server_address = ("", port)
    max_tries = 10
    httpd = None

    for p in range(port, port + max_tries):
        try:
            httpd = HTTPServer(("", p), ResumeRequestHandler)
            port = p
            break
        except OSError:
            continue

    if not httpd:
        print(f"Could not bind to ports {port} to {port + max_tries - 1}.")
        sys.exit(1)

    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

    url = f"http://localhost:{port}"
    print("\n" + "=" * 60)
    print("  [CIVIL & STRUCTURAL ENGINEERING RESUME - PYTHON SERVER]")
    print("=" * 60)
    print(f"  * Running at:        {url}")
    print(f"  * API endpoint:      {url}/api/resume")
    print(f"  * Edit data in:      data.py")
    print("  * Press Ctrl+C to stop server")
    print("=" * 60 + "\n")

    if open_browser:
        webbrowser.open(url)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer gracefully stopped.")
        httpd.server_close()


if __name__ == "__main__":
    # Check flags
    if "--build" in sys.argv:
        build_static()
        sys.exit(0)

    # Optional port argument
    port = 5000
    if "--port" in sys.argv:
        try:
            idx = sys.argv.index("--port")
            port = int(sys.argv[idx + 1])
        except (ValueError, IndexError):
            print("Invalid port specified. Using 5000.")

    no_open = "--no-browser" in sys.argv
    run_server(port=port, open_browser=not no_open)

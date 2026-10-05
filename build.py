#!/usr/bin/env python3
"""
STATIC BUILD SCRIPT (PYTHON)

Generates a standalone, static index.html from data.py and templates/index.html.
Can be hosted directly on GitHub Pages, Netlify, or opened in any browser.

Usage:
    py build.py
"""

from pathlib import Path
import json
import sys
import jinja2

# Import data
from data import RESUME_DATA
import markupsafe

def build():
    base_dir = Path(__file__).parent
    template_dir = base_dir / "templates"
    
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(template_dir)),
        autoescape=jinja2.select_autoescape(["html", "xml"])
    )
    env.filters["tojson"] = lambda obj: markupsafe.Markup(json.dumps(obj))

    categories = sorted(list({p.get("category", "") for p in RESUME_DATA.get("projects", [])}))
    context = {
        **RESUME_DATA,
        "project_categories": categories,
    }

    template = env.get_template("index.html")
    rendered = template.render(**context)

    # In standalone static file, make sure static/styles.css works locally
    output_file = base_dir / "index.html"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(rendered)

    # Use ASCII or UTF-8 safe print
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

    print(f"[OK] Standalone index.html successfully generated at: {output_file.resolve()}")
    print("[OK] You can now open index.html directly in your browser or deploy it to GitHub Pages!")

if __name__ == "__main__":
    build()

# 🏗️ Muhammad Edrey Bin Jeffrey — Civil Engineering Resume & Portfolio Website

A modern, minimalist, and responsive resume website powered by **Python**, featuring dynamic server-side rendering with **Jinja2**, REST API endpoints, and a print-optimized executive stylesheet.

---

## 👤 Profile & Credentials

- **Name**: Muhammad Edrey Bin Jeffrey
- **Institution**: National University of Singapore (NUS)
- **Programme**: Bachelor of Engineering (Civil Engineering), Specialisation in Digitalisation of Urban Infrastructure
- **Academic Standing**: NUS GPA: 4.11 / 5.00 | Singapore Polytechnic Diploma GPA: 3.92 / 4.00 (6 Distinctions)
- **Contact**: +65 8138 3602 • edreyjeffrey@gmail.com • [LinkedIn Profile](https://www.linkedin.com/in/edreyjeffrey2311/)
- **Location**: Singapore

---

## 🚀 Running the Python Web Application

### 1. Launch Local Live Server
```bash
py app.py
```
*(Starts the server on `http://localhost:5000` and automatically opens your browser)*

### 2. Recompile Standalone Static HTML (For GitHub Pages / Netlify)
```bash
py build.py
```
*(Exports the site directly to `index.html` with your latest data from `data.py`)*

---

## ✏️ How to Update Your Details

All resume content is stored in [`data.py`](data.py). Simply edit the Python dictionaries and run `py build.py` or restart `py app.py`.

---

## 📁 File Structure

```text
├── app.py             # Python HTTP server, Jinja2 template renderer & REST APIs
├── data.py            # Authenticated resume configuration in Python
├── build.py           # Standalone static site compiler
├── templates/
│   └── index.html     # Minimalist Jinja2 HTML5 template with project modals
├── static/
│   └── styles.css     # Clean black & white design system with @media print rules
├── index.html         # Pre-compiled standalone static website
└── README.md          # Project documentation
```

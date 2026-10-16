"""Convenience entry point to launch the Infrastructure Digital Twin Streamlit app."""

import os
import subprocess
import sys

def main():
    project_dir = os.path.dirname(os.path.abspath(__file__))
    # Target app.py at root, fallback to app/main.py if needed
    app_path = os.path.join(project_dir, "app.py")
    if not os.path.exists(app_path):
        app_path = os.path.join(project_dir, "app", "main.py")

    # Locate virtual environment python if available
    venv_python_win = os.path.join(project_dir, ".venv", "Scripts", "python.exe")
    venv_python_posix = os.path.join(project_dir, ".venv", "bin", "python")

    if os.path.exists(venv_python_win):
        python_exe = venv_python_win
    elif os.path.exists(venv_python_posix):
        python_exe = venv_python_posix
    else:
        python_exe = sys.executable

    print(f"Launching Infrastructure Digital Twin using: {python_exe}")
    cmd = [python_exe, "-m", "streamlit", "run", app_path]
    try:
        subprocess.run(cmd, cwd=project_dir, check=True)
    except KeyboardInterrupt:
        print("\nDigital Twin application stopped.")

if __name__ == "__main__":
    main()

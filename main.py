import os
import subprocess
import sys
from pathlib import Path
import shutil

# Define paths
CURRENT_DIR = Path(__file__).parent
VENV_DIR = CURRENT_DIR / "venv"
FLASK_APP = CURRENT_DIR / "flask_app" / "app.py"
REACT_BUILD_DIR = CURRENT_DIR / "flask_app" / "build"

def create_virtual_env():
    """Create a virtual environment if it doesn't exist."""
    if not VENV_DIR.exists():
        print("Creating virtual environment...")
        subprocess.run([sys.executable, "-m", "venv", VENV_DIR])
    else:
        print("Virtual environment already exists.")

def install_dependencies():
    """Install dependencies in the virtual environment."""
    print("Installing dependencies...")
    pip = VENV_DIR / "Scripts" / "pip" if os.name == "nt" else VENV_DIR / "bin" / "pip"
    subprocess.run([pip, "install", "-r", "requirements.txt"])

def build_react_app():
    """Check if React build exists, else build it."""
    if not REACT_BUILD_DIR.exists():
        print("Building React frontend...")
        subprocess.run(["npm", "install"], cwd=REACT_BUILD_DIR.parent)
        subprocess.run(["npm", "run", "build"], cwd=REACT_BUILD_DIR.parent)
    else:
        print("React frontend is already built.")

def start_application():
    """Run the Flask app with React frontend."""
    import webbrowser
    flask_url = "http://127.0.0.1:5000"  # Default Flask URL
    print("Starting the application...")
    python = VENV_DIR / "Scripts" / "python" if os.name == "nt" else VENV_DIR / "bin" / "python"
    
    # Open the browser after Flask starts
    subprocess.Popen([python, str(FLASK_APP)])
    webbrowser.open(flask_url)

       

def create_windows_shortcut():
    """Create a desktop shortcut to launch the app (Windows only)."""
    try:
        import winshell
        desktop = Path(os.path.join(os.path.expanduser("~"), "Desktop"))
        shortcut = desktop / "MyApp.lnk"
        if not shortcut.exists():
            with winshell.shortcut(shortcut) as link:
                link.path = str(sys.executable)
                link.arguments = str(FLASK_APP)
                link.description = "MyApp - Click to Run"
                link.icon_location = str(CURRENT_DIR / "icon.ico")
            print("Shortcut created on desktop.")
        else:
            print("Shortcut already exists.")
    except ImportError:
        print("winshell module not installed. Skipping shortcut creation.")

def create_linux_desktop_file():
    """Create a .desktop file for Linux systems."""
    desktop_file_path = Path.home() / ".local" / "share" / "applications" / "MyApp.desktop"
    desktop_file_content = f"""[Desktop Entry]
Type=Application
Name=MyApp
Exec=python3 {FLASK_APP}
Icon={CURRENT_DIR}/icon.png
Terminal=false
"""
    desktop_file_path.parent.mkdir(parents=True, exist_ok=True)
    desktop_file_path.write_text(desktop_file_content)
    print("Shortcut created in applications menu (Linux).")

def bundle_executable():
    """Bundle the project as a single executable using PyInstaller."""
    print("Bundling the project into an executable...")
    subprocess.run([
        "pyinstaller",
        "--onefile",
        "--icon=icon.ico",
        "--add-data",
        f"{REACT_BUILD_DIR}:flask_app/build",
        "--add-data",
        f"{FLASK_APP.parent}:flask_app",
        str(FLASK_APP.resolve())
    ])

def main():
    """Main function to automate the setup process."""
    create_virtual_env()
    install_dependencies()
    #build_react_app()
    if os.name == "nt":
        create_windows_shortcut()
    else:
        create_linux_desktop_file()
    bundle_executable()
    print("Setup complete. Run the executable in the 'dist' folder.")

if __name__ == "__main__":
    main()

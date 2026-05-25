import os
import sys
import subprocess
import shutil

def verify_dependencies():
    """Ensures all packaging dependencies are present in the active python environment."""
    print("Checking build environment dependencies...")
    try:
        import customtkinter
        import fitz
        import vtracer
        from PIL import Image
        import PyInstaller
        print("  - All dependency imports verified successfully!")
    except ImportError as e:
        print(f"  [ERROR] Missing required packaging dependencies: {e}")
        print("  Please run: pip install customtkinter PyMuPDF vtracer pillow pyinstaller")
        sys.exit(1)

def get_customtkinter_path():
    """Locates the installed customtkinter package directory to bundle UI themes and configs."""
    import customtkinter
    return os.path.dirname(customtkinter.__file__)

def build_standalone_executable():
    """Runs PyInstaller programmatically to generate the portable binary."""
    verify_dependencies()
    
    # Configure target names
    app_name = "VectorizerStudio"
    entry_point = "app.py"
    
    # Locate CustomTkinter directory to explicitly bundle themes/assets
    ctk_path = get_customtkinter_path()
    print(f"Found CustomTkinter assets at: {ctk_path}")
    
    # Formulate PyInstaller command arguments
    # 1. Main entry file
    cmd = [
        sys.executable, "-m", "PyInstaller",
        entry_point,
        "--name", app_name,
        "--noconsole",           # Disable black terminal window on launch
        "--onefile",             # Package into a single portable executable file
        "--clean",               # Clear cache before building
    ]
    
    # 2. Add CustomTkinter assets to package data
    # format is 'source_dir;target_dir' on Windows and 'source_dir:target_dir' on Mac/Linux
    separator = ";" if sys.platform == "win32" else ":"
    cmd.extend([
        "--add-data", f"{ctk_path}{separator}customtkinter"
    ])
    
    # 3. Handle specific DLLs or package exports if any
    # PyInstaller hooks handle vtracer and PyMuPDF (fitz) automatically in v6+,
    # but we list them in hidden-imports to be absolutely safe
    cmd.extend([
        "--hidden-import", "vtracer",
        "--hidden-import", "fitz",
        "--hidden-import", "PIL",
    ])
    
    print("\nExecuting PyInstaller command:")
    print(" ".join(cmd))
    print("\nThis may take 1-2 minutes as it compiles and compresses all native DLLs. Please wait...")
    
    # Run PyInstaller
    try:
        # Use subprocess to run the packaging task
        result = subprocess.run(cmd, check=True)
        if result.returncode == 0:
            print("\n[BUILD SUCCESSFUL!]")
            
            output_ext = ".exe" if sys.platform == "win32" else ""
            out_binary = os.path.join("dist", f"{app_name}{output_ext}")
            print(f"Your portable standalone binary is located at: {os.path.abspath(out_binary)}")
            
            # Print Installer Guideline
            print_installer_guidelines(app_name, out_binary)
    except subprocess.CalledProcessError as e:
        print(f"\n[BUILD FAILED] PyInstaller compilation failed: {e}")
        sys.exit(1)

def print_installer_guidelines(app_name, binary_path):
    """Outputs instructions for compiling the portable binary into official installers (Inno Setup / DMG)."""
    print("\n" + "="*60)
    print("PACKAGING YOUR BINARY INTO OS INSTALLERS")
    print("="*60)
    
    if sys.platform == "win32":
        print("""
For Windows (Create a Standard EXE Installer):
----------------------------------------------
We highly recommend using Inno Setup (free and open source):
1. Download and install Inno Setup: https://jrsoftware.org/isdl.php
2. Open Inno Setup and select 'Create a new script file using the Script Wizard'.
3. Set your application name to 'Vectorizer Studio'.
4. In 'Application Files', select your newly compiled executable:
   C:\\Users\\BLightAdee\\Vectorizer\\dist\\VectorizerStudio.exe
5. Complete the wizard to generate a highly professional Windows installer (.exe)
   complete with desktop shortcuts, registry entries, and an uninstaller!
""")
    else:
        print("""
For macOS (Create a Drag-and-Drop DMG Disk Image):
--------------------------------------------------
We recommend using 'create-dmg' (a command line utility) to build beautiful DMGs:
1. Install create-dmg via Homebrew:
   brew install create-dmg
2. Generate the DMG pointing to the PyInstaller .app bundle inside the dist folder:
   create-dmg \\
     --volname "Vectorizer Studio" \\
     --volicon "assets/icon.icns" \\
     --background "assets/dmg_bg.png" \\
     --window-pos 200 120 \\
     --window-size 800 400 \\
     --icon-size 100 \\
     --icon "VectorizerStudio.app" 200 190 \\
     --hide-extension "VectorizerStudio.app" \\
     --app-drop-link 600 190 \\
     "dist/VectorizerStudio-Installer.dmg" \\
     "dist/VectorizerStudio.app"
""")
    print("="*60 + "\n")

if __name__ == "__main__":
    build_standalone_executable()

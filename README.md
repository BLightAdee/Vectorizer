# Vectorizer Studio ⚡

A high-performance, native (non-Electron, non-Tauri) cross-platform desktop application for accurately converting raster images and PDF documents into high-fidelity, scalable SVG files. 

Powered under the hood by **vtracer** (a high-speed, Rust-compiled vectorization engine) and **PyMuPDF** (a pixel-perfect document rendering and vector tree parsing compiler).

> [!WARNING]
> **Disclaimer**: This project is 100% vibe-coded. I do not plan on maintaining it, nor do I guarantee the integrity, safety, or correctness of any code inside this repository. Use entirely at your own discretion.

---

## 🌟 Key Features

* **Lossless PDF Vector Extraction**: Parses mathematical graphic paths, Bezier curves, line weights, strokes, and text directly from vector-based PDFs, outputting perfectly scaled vector SVGs in milliseconds with zero loss in resolution and minimal file sizes.
* **Smart Rasterization & Tracing (Scanned PDFs)**: Automatically renders scanned or image-only PDF documents at high-resolution (300 DPI) in-memory and traces them, generating editable, scalable vector shapes from static scanned paper!
* **Rust-Powered Raster Vectorization**: Integrates `vtracer`, which traces color images (greatly outperforming standard black-and-white tools like Potrace) and performs bezier spline fitting to produce smooth curves.
* **Fluid Multithreading**: Offloads image/PDF thumbnail rendering and core file translations to background worker threads, keeping the CustomTkinter GUI perfectly fluid and responsive during large batch operations.
* **Advanced Tuning Sliders**: Adjust detail levels with quick presets or take granular control of color clustering bit-depths, noise speckle filtering, corner thresholds, path float precision, and spline fitting models.
* **Rich Native UX**: Modern dark theme, interactive batch file queues, detailed metadata overlays, live visual file previews, and direct OS-level file and folder launchers.

---

## 🛠️ Technology Stack

* **Language**: Python 3.14+
* **GUI Engine**: CustomTkinter (leveraging native OS drawing engines for dark/light appearance)
* **Vectorizing Core**: VTracer (Rust-backed WebAssembly/Native bindings)
* **PDF Compiler**: PyMuPDF (`fitz` bindings for MuPDF)
* **Image Processing**: Pillow (PIL)

---

## 🚀 Getting Started

### Prerequisites

Ensure you have **Python 3.14+** installed. Then, set up the project:

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/<your-username>/Vectorizer.git
   cd Vectorizer
   ```

2. **Initialize a Virtual Environment**:
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1 # On Windows
   source venv/bin/activate    # On macOS/Linux
   ```

3. **Install Dependencies**:
   ```bash
   pip install customtkinter PyMuPDF vtracer pillow pyinstaller
   ```

### Running Locally

To start the graphical desktop workspace:
```bash
python app.py
```

### Running Backend Tests

Verify the conversion engines programmatically without launching the GUI:
```bash
python test_converter.py
```

---

## 📦 Building the Standalone App

To package the application into a single portable binary that runs natively on Windows/macOS without needing Python installed:

1. Run the packaging utility script:
   ```bash
   python build_app.py
   ```
2. The standalone portable binary will be created inside the `dist/` directory:
   * **Windows**: `dist/VectorizerStudio.exe` (automatically optimized for High-DPI screens and runs with no console window).
   * **macOS**: `dist/VectorizerStudio.app`

### Packaging into OS Installers

#### Windows (EXE/MSI Installer)
To compile the portable `.exe` into a standard Windows installer (enabling desktop shortcuts, start menu pins, and uninstallers), we recommend using **Inno Setup** (free):
1. Download and install Inno Setup.
2. Select **Create a new script file using the Script Wizard**.
3. Point the main application file to `dist\VectorizerStudio.exe` and complete the wizard.

#### macOS (Drag-and-Drop DMG)
To package the `.app` bundle into a professional disk image:
1. Install `create-dmg` via Homebrew:
   ```bash
   brew install create-dmg
   ```
2. Build the DMG installer:
   ```bash
   create-dmg \
     --volname "Vectorizer Studio" \
     --volicon "assets/icon.icns" \
     --icon-size 100 \
     --icon "VectorizerStudio.app" 200 190 \
     --hide-extension "VectorizerStudio.app" \
     --app-drop-link 600 190 \
     "dist/VectorizerStudio-Installer.dmg" \
     "dist/VectorizerStudio.app"
   ```

---

## 📁 Repository Structure

```
Vectorizer/
├── .gitignore              # Excludes caches, test outputs, and venv files
├── README.md               # Complete project documentation
├── app.py                  # Core GUI code (CustomTkinter)
├── converter.py            # Vectorization and PDF translation engine
├── preview.py              # Visual scaling and image/PDF previewer
├── build_app.py            # Automated packaging utility (PyInstaller)
├── test_converter.py      # Automated backend verification test suite
└── venv/                   # Local Python Virtual Environment (Ignored)
```

---

## 📝 License

This project is open-source and available under the [MIT License](LICENSE).

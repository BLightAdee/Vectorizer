import os
import sys
from PIL import Image, ImageDraw
import fitz  # PyMuPDF
from converter import convert_file

def create_test_assets():
    """Programmatically generates a test PNG and a test PDF for validation."""
    print("Generating temporary test assets...")
    
    # 1. Create a simple test PNG (white background with a red circle)
    img = Image.new("RGB", (200, 200), "white")
    draw = ImageDraw.Draw(img)
    draw.ellipse([50, 50, 150, 150], fill="red", outline="darkred", width=3)
    img.save("test_circle.png")
    print("  - Created test_circle.png")
    
    # 2. Create a simple vector PDF using PyMuPDF
    doc = fitz.open()
    page = doc.new_page(width=400, height=400)
    
    # Draw native PDF vector lines
    page.draw_line((50, 50), (350, 50), color=(0, 0, 1), width=4)  # Blue line
    page.draw_rect((50, 100, 150, 200), color=(0, 0.5, 0), fill=(0.7, 0.9, 0.7), width=2) # Green box
    
    # Insert some vector text
    page.insert_text((50, 250), "Native Vector PDF Test", fontsize=20, color=(0.2, 0.2, 0.2))
    
    doc.save("test_doc.pdf")
    doc.close()
    print("  - Created test_doc.pdf")

def run_tests():
    # Setup test directory
    output_dir = "test_output"
    os.makedirs(output_dir, exist_ok=True)
    
    create_test_assets()
    print("\nRunning conversion engine tests...")
    
    # Test 1: Raster Image to SVG
    print("Test 1: Converting PNG to SVG (vtracer)...")
    try:
        results = convert_file(
            input_path="test_circle.png",
            output_dir=output_dir,
            params={"colormode": "color", "path_precision": 3}
        )
        for path in results:
            if os.path.exists(path) and os.path.getsize(path) > 0:
                print(f"  [SUCCESS] Created: {path} ({os.path.getsize(path)} bytes)")
            else:
                print(f"  [FAILED] Output file is empty or missing: {path}")
                sys.exit(1)
    except Exception as e:
        print(f"  [ERROR] Test 1 failed with exception: {e}")
        sys.exit(1)
        
    # Test 2: PDF Page Direct Vector Extraction
    print("Test 2: Converting PDF to SVG directly (PyMuPDF Lossless)...")
    try:
        results = convert_file(
            input_path="test_doc.pdf",
            output_dir=output_dir,
            params={"pdf_mode": "direct", "pdf_pages": "1"}
        )
        for path in results:
            if os.path.exists(path) and os.path.getsize(path) > 0:
                print(f"  [SUCCESS] Created: {path} ({os.path.getsize(path)} bytes)")
            else:
                print(f"  [FAILED] Output file is empty or missing: {path}")
                sys.exit(1)
    except Exception as e:
        print(f"  [ERROR] Test 2 failed with exception: {e}")
        sys.exit(1)
        
    # Test 3: PDF Page Rasterize & Trace (Scanned Mode)
    print("Test 3: Converting PDF to SVG via Rasterize & Trace (MuPDF + vtracer)...")
    try:
        results = convert_file(
            input_path="test_doc.pdf",
            output_dir=output_dir,
            # Force scanned tracing mode
            params={"pdf_mode": "trace", "pdf_pages": "1", "colormode": "color"}
        )
        # The output file in this test will overwrite the previous page-1 SVG since they write to the same place,
        # but let's change target name by supplying custom output dir or just checking the file.
        for path in results:
            if os.path.exists(path) and os.path.getsize(path) > 0:
                print(f"  [SUCCESS] Created: {path} ({os.path.getsize(path)} bytes)")
            else:
                print(f"  [FAILED] Output file is empty or missing: {path}")
                sys.exit(1)
    except Exception as e:
        print(f"  [ERROR] Test 3 failed with exception: {e}")
        sys.exit(1)
        
    print("\nCleaning up temporary test source assets...")
    if os.path.exists("test_circle.png"):
        os.remove("test_circle.png")
    if os.path.exists("test_doc.pdf"):
        os.remove("test_doc.pdf")
        
    print("\n[ALL TESTS PASSED SUCCESSFULLY!]")

if __name__ == "__main__":
    run_tests()

import io
from PIL import Image
import fitz  # PyMuPDF

def get_preview_image(file_path, max_width, max_height, page_num=0):
    """
    Loads an image or PDF page and scales it to fit within max_width x max_height while preserving aspect ratio.
    Returns:
    - pil_image (PIL.Image): The scaled PIL Image.
    - display_width (int): The calculated width for GUI presentation.
    - display_height (int): The calculated height for GUI presentation.
    """
    if file_path.lower().endswith('.pdf'):
        # PDF page preview extraction
        with fitz.open(file_path) as doc:
            if page_num < 0 or page_num >= doc.page_count:
                page_num = 0
            page = doc.load_page(page_num)
            
            # 150 DPI is more than enough for a crisp, responsive GUI preview
            pix = page.get_pixmap(dpi=150)
            
            # Read pixmap bytes directly into Pillow in-memory
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))
            img.load()  # Load image data into memory before closing PDF
    else:
        # Standard raster image load
        img = Image.open(file_path)
        img.load()
        
    # Calculate aspect ratio scaling
    orig_w, orig_h = img.size
    
    # Calculate scaling factor
    ratio = min(max_width / orig_w, max_height / orig_h)
    
    # Ensure we don't scale UP beyond original dimensions
    scale = min(1.0, ratio)
    
    display_w = int(orig_w * scale)
    display_h = int(orig_h * scale)
    
    # Resize the image using high-quality Lanczos interpolation
    # CustomTkinter CTkImage will render this image nicely
    resized_img = img.resize((display_w, display_h), Image.Resampling.LANCZOS)
    
    return resized_img, display_w, display_h

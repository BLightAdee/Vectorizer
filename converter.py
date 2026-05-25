import os
import fitz  # PyMuPDF
import vtracer

def map_params(params):
    """Maps custom user settings to vtracer's expected arguments with solid defaults."""
    # Base defaults
    mapped = {
        'colormode': 'color',
        'hierarchical': 'stacked',
        'mode': 'spline',
        'filter_speckle': 4,
        'color_precision': 6,
        'layer_difference': 16,
        'corner_threshold': 60,
        'length_threshold': 4.0,
        'max_iterations': 10,
        'splice_threshold': 45,
        'path_precision': 2
    }
    
    if not params:
        return mapped
        
    # Map user inputs if present
    if 'colormode' in params:
        mapped['colormode'] = str(params['colormode']).lower()
    if 'hierarchical' in params:
        mapped['hierarchical'] = str(params['hierarchical']).lower()
    if 'mode' in params:
        # Map user input and correct plural form if needed
        m = str(params['mode']).lower()
        if m == 'splines':
            m = 'spline'
        mapped['mode'] = m
    if 'filter_speckle' in params:
        mapped['filter_speckle'] = int(params['filter_speckle'])
    if 'color_precision' in params:
        mapped['color_precision'] = int(params['color_precision'])
    if 'layer_difference' in params:
        mapped['layer_difference'] = int(params['layer_difference'])
    if 'corner_threshold' in params:
        mapped['corner_threshold'] = int(params['corner_threshold'])
    if 'length_threshold' in params:
        mapped['length_threshold'] = float(params['length_threshold'])
    if 'max_iterations' in params:
        mapped['max_iterations'] = int(params['max_iterations'])
    if 'splice_threshold' in params:
        mapped['splice_threshold'] = int(params['splice_threshold'])
    if 'path_precision' in params:
        mapped['path_precision'] = int(params['path_precision'])
        
    return mapped

def convert_raster_to_svg(input_path, output_path, params=None):
    """Converts a raster image to SVG using vtracer."""
    vtracer_params = map_params(params)
    
    # We MUST use positional arguments because passing keyword arguments
    # to vtracer's PyO3 bindings on Windows causes a silent crash (exit code 1).
    vtracer.convert_image_to_svg_py(
        input_path,
        output_path,
        vtracer_params['colormode'],
        vtracer_params['hierarchical'],
        vtracer_params['mode'],
        vtracer_params['filter_speckle'],
        vtracer_params['color_precision'],
        vtracer_params['layer_difference'],
        vtracer_params['corner_threshold'],
        vtracer_params['length_threshold'],
        vtracer_params['max_iterations'],
        vtracer_params['splice_threshold'],
        vtracer_params['path_precision']
    )

def convert_pdf_page_to_svg_direct(pdf_doc, page_num, output_path):
    """Extracts a vector SVG directly from a PDF page using PyMuPDF (Lossless)."""
    page = pdf_doc.load_page(page_num)
    svg_data = page.get_svg_image()
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(svg_data)

def convert_pdf_page_to_svg_traced(pdf_doc, page_num, output_path, params=None):
    """Renders a PDF page to a high-res image and traces it with vtracer (Scanned PDFs)."""
    page = pdf_doc.load_page(page_num)
    
    # Render page to standard 300 DPI high-res pixmap
    pix = page.get_pixmap(dpi=300)
    
    # Save to a temporary PNG file in the same directory as the target output
    temp_png_path = output_path + ".temp.png"
    pix.save(temp_png_path)
    
    try:
        # Trace the temporary PNG to the final SVG
        convert_raster_to_svg(temp_png_path, output_path, params)
    finally:
        # Guarantee cleanup of temporary PNG
        if os.path.exists(temp_png_path):
            os.remove(temp_png_path)

def parse_pages_selection(pages_str, total_pages):
    """Parses a user-defined page selection string (e.g. '1, 3-5, 8') into a list of 0-indexed page integers."""
    if not pages_str or str(pages_str).strip().lower() == 'all':
        return list(range(total_pages))
    
    if str(pages_str).strip().lower() == 'first':
        return [0]
        
    pages = set()
    parts = str(pages_str).replace(' ', '').split(',')
    
    for part in parts:
        if not part:
            continue
        if '-' in part:
            try:
                start, end = part.split('-')
                start_idx = max(1, int(start)) - 1
                end_idx = min(total_pages, int(end))
                for i in range(start_idx, end_idx):
                    pages.add(i)
            except ValueError:
                pass  # Skip malformed ranges
        else:
            try:
                idx = int(part) - 1
                if 0 <= idx < total_pages:
                    pages.add(idx)
            except ValueError:
                pass  # Skip malformed integers
                
    return sorted(list(pages)) if pages else [0]

def convert_file(input_path, output_dir, params=None, progress_callback=None):
    """
    Main file converter interface.
    Handles routing to either PDF conversion or image tracing.
    
    Parameters:
    - input_path (str): Path to input image/PDF.
    - output_dir (str): Directory where SVG(s) should be saved.
    - params (dict): Vectorization settings & PDF configurations.
    - progress_callback (callable): Function of the form callback(status_text, percent_float).
    """
    if progress_callback:
        progress_callback("Reading file...", 0.1)
        
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")
        
    os.makedirs(output_dir, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(input_path))[0]
    ext = os.path.splitext(input_path)[1].lower()
    
    # Initialize conversion parameters
    params = params or {}
    
    if ext == '.pdf':
        doc = fitz.open(input_path)
        total_pages = doc.page_count
        
        # Get page selection and conversion mode
        pages_str = params.get('pdf_pages', 'all')
        pages_to_convert = parse_pages_selection(pages_str, total_pages)
        
        pdf_mode = params.get('pdf_mode', 'direct')  # 'direct' or 'trace'
        
        if progress_callback:
            progress_callback(f"Converting PDF ({len(pages_to_convert)} pages)...", 0.2)
            
        converted_files = []
        for index, page_num in enumerate(pages_to_convert):
            # Formulate individual page output path
            if len(pages_to_convert) == 1:
                out_path = os.path.join(output_dir, f"{base_name}.svg")
            else:
                out_path = os.path.join(output_dir, f"{base_name}_page_{page_num + 1}.svg")
                
            percent_progress = 0.2 + (0.7 * (index / len(pages_to_convert)))
            if progress_callback:
                progress_callback(f"Converting page {page_num + 1} of {total_pages}...", percent_progress)
                
            if pdf_mode == 'trace':
                convert_pdf_page_to_svg_traced(doc, page_num, out_path, params)
            else:  # Direct lossless path extraction
                convert_pdf_page_to_svg_direct(doc, page_num, out_path)
                
            converted_files.append(out_path)
            
        doc.close()
        
        if progress_callback:
            progress_callback("Conversion complete!", 1.0)
        return converted_files
        
    else:  # Raster Image Conversion
        out_path = os.path.join(output_dir, f"{base_name}.svg")
        if progress_callback:
            progress_callback("Tracing image outlines...", 0.4)
            
        convert_raster_to_svg(input_path, out_path, params)
        
        if progress_callback:
            progress_callback("Conversion complete!", 1.0)
        return [out_path]

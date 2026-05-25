import os
import sys
import threading
import queue
import time
import subprocess
from tkinter import filedialog, messagebox
import customtkinter as ctk

# Import our custom modules
from converter import convert_file
from preview import get_preview_image

# Configure CustomTkinter
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")  # Beautiful native blue accents

class VectorizerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Configure Main Window
        self.title("Vectorizer Studio - Premium Raster & PDF to SVG Converter")
        self.geometry("1150x750")
        self.minsize(1050, 650)
        
        # Application State
        self.queue_list = []  # List of dicts: {id, path, format, size, status, card_widget, progress_bar, status_label, output_svgs}
        self.queue_id_counter = 0
        self.selected_queue_id = None
        self.conversion_queue = queue.Queue()
        self.conversion_thread = None
        self.conversion_active = False
        self.output_directory = ""
        self.elapsed_start_time = 0
        self.completed_count = 0
        
        # Configure Grid Layout (3-Column Layout)
        self.grid_columnconfigure(0, weight=0, minsize=320)  # Settings panel
        self.grid_columnconfigure(1, weight=1)                # File Queue workspace
        self.grid_columnconfigure(2, weight=0, minsize=320)  # Preview panel
        self.grid_rowconfigure(0, weight=1)
        
        # Create Layout Frames
        self.create_settings_sidebar()
        self.create_workspace_center()
        self.create_preview_sidebar()
        
        # Load Initial Preset Settings
        self.on_preset_change("High Detail (Color)")
        
        # Setup GUI polling loop for threaded conversion progress
        self.poll_queue()
        
    def create_settings_sidebar(self):
        """Creates the left panel for vectorization configuration and presets."""
        self.settings_frame = ctk.CTkFrame(self, corner_radius=0, width=320, fg_color="#1E1E24")
        self.settings_frame.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        self.settings_frame.grid_propagate(False)
        
        # Sidebar Header
        sidebar_header = ctk.CTkLabel(
            self.settings_frame, 
            text="⚡ VECTORIZER STUDIO", 
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#3B82F6"
        )
        sidebar_header.pack(anchor="w", padx=20, pady=(25, 5))
        
        sub_header = ctk.CTkLabel(
            self.settings_frame, 
            text="High-Fidelity SVG Engine", 
            font=ctk.CTkFont(size=12),
            text_color="#9CA3AF"
        )
        sub_header.pack(anchor="w", padx=20, pady=(0, 20))
        
        # Divider
        divider1 = ctk.CTkFrame(self.settings_frame, height=2, fg_color="#2D2D36")
        divider1.pack(fill="x", padx=15, pady=5)
        
        # --- SECTION: OUTPUT ---
        output_label = ctk.CTkLabel(
            self.settings_frame, 
            text="📁 OUTPUT DESTINATION", 
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#E5E7EB"
        )
        output_label.pack(anchor="w", padx=20, pady=(15, 8))
        
        self.dest_mode = ctk.CTkSegmentedButton(
            self.settings_frame, 
            values=["Same Folder", "Custom Directory"],
            command=self.on_dest_mode_change
        )
        self.dest_mode.pack(fill="x", padx=20, pady=5)
        self.dest_mode.set("Same Folder")
        
        self.custom_path_frame = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        self.custom_path_button = ctk.CTkButton(
            self.custom_path_frame, 
            text="Browse...", 
            width=70, 
            command=self.browse_output_directory
        )
        self.custom_path_button.pack(side="right", padx=(5, 0))
        
        self.custom_path_label = ctk.CTkLabel(
            self.custom_path_frame, 
            text="Choose output path...", 
            anchor="w",
            text_color="#9CA3AF",
            font=ctk.CTkFont(size=11)
        )
        self.custom_path_label.pack(side="left", fill="x", expand=True)
        # Hidden by default until "Custom Directory" is selected
        
        # Divider
        divider2 = ctk.CTkFrame(self.settings_frame, height=2, fg_color="#2D2D36")
        divider2.pack(fill="x", padx=15, pady=15)
        
        # --- SECTION: TUNING ENGINE ---
        engine_label = ctk.CTkLabel(
            self.settings_frame, 
            text="⚙️ VECTORIZATION SETTINGS", 
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#E5E7EB"
        )
        engine_label.pack(anchor="w", padx=20, pady=(0, 10))
        
        # Presets OptionMenu
        preset_frame = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        preset_frame.pack(fill="x", padx=20, pady=5)
        
        preset_label = ctk.CTkLabel(preset_frame, text="Preset:", font=ctk.CTkFont(size=12))
        preset_label.pack(side="left")
        
        self.preset_menu = ctk.CTkOptionMenu(
            preset_frame,
            values=["High Detail (Color)", "Medium Detail (Color)", "Flat Logo (Color)", "Black & White Silhouette", "Custom (Advanced)"],
            command=self.on_preset_change
        )
        self.preset_menu.pack(side="right", fill="x", expand=True, padx=(10, 0))
        
        # Tunable Sliders (Scrollable area for advanced settings)
        self.sliders_frame = ctk.CTkScrollableFrame(self.settings_frame, fg_color="#18181F", height=240, label_text="Parameters Tuning")
        self.sliders_frame.pack(fill="x", padx=20, pady=10)
        
        # 1. Color Mode
        self.colormode_switch = ctk.CTkSwitch(
            self.sliders_frame, 
            text="Color Mode (vs. B&W)", 
            command=self.on_slider_change
        )
        self.colormode_switch.pack(anchor="w", padx=5, pady=8)
        
        # 2. Speckle filter
        self.speckle_label = ctk.CTkLabel(self.sliders_frame, text="Speckle Filter: 4 px", font=ctk.CTkFont(size=11))
        self.speckle_label.pack(anchor="w", padx=5, pady=(5, 0))
        self.speckle_slider = ctk.CTkSlider(self.sliders_frame, from_=0, to=64, number_of_steps=64, command=self.on_speckle_slide)
        self.speckle_slider.pack(fill="x", padx=5, pady=(0, 8))
        
        # 3. Color Precision
        self.color_prec_label = ctk.CTkLabel(self.sliders_frame, text="Color Precision: 6 bits", font=ctk.CTkFont(size=11))
        self.color_prec_label.pack(anchor="w", padx=5, pady=(5, 0))
        self.color_prec_slider = ctk.CTkSlider(self.sliders_frame, from_=1, to=8, number_of_steps=7, command=self.on_color_prec_slide)
        self.color_prec_slider.pack(fill="x", padx=5, pady=(0, 8))
        
        # 4. Corner Threshold
        self.corner_label = ctk.CTkLabel(self.sliders_frame, text="Corner Threshold: 60°", font=ctk.CTkFont(size=11))
        self.corner_label.pack(anchor="w", padx=5, pady=(5, 0))
        self.corner_slider = ctk.CTkSlider(self.sliders_frame, from_=0, to=180, number_of_steps=36, command=self.on_corner_slide)
        self.corner_slider.pack(fill="x", padx=5, pady=(0, 8))
        
        # 5. Path Precision
        self.path_prec_label = ctk.CTkLabel(self.sliders_frame, text="Path Precision: 2 decimals", font=ctk.CTkFont(size=11))
        self.path_prec_label.pack(anchor="w", padx=5, pady=(5, 0))
        self.path_prec_slider = ctk.CTkSlider(self.sliders_frame, from_=1, to=6, number_of_steps=5, command=self.on_path_prec_slide)
        self.path_prec_slider.pack(fill="x", padx=5, pady=(0, 8))
        
        # 6. Spline Fitting Mode
        fitting_frame = ctk.CTkFrame(self.sliders_frame, fg_color="transparent")
        fitting_frame.pack(fill="x", padx=5, pady=8)
        fitting_lbl = ctk.CTkLabel(fitting_frame, text="Fitting:", font=ctk.CTkFont(size=11))
        fitting_lbl.pack(side="left")
        self.fitting_menu = ctk.CTkOptionMenu(fitting_frame, values=["Spline", "Polygon"], height=22, command=self.on_slider_change)
        self.fitting_menu.pack(side="right", fill="x", expand=True, padx=(10, 0))
        
        # Divider
        divider3 = ctk.CTkFrame(self.settings_frame, height=2, fg_color="#2D2D36")
        divider3.pack(fill="x", padx=15, pady=(5, 10))
        
        # --- SECTION: PDF SPECIFIC SETTINGS ---
        pdf_label = ctk.CTkLabel(
            self.settings_frame, 
            text="📄 PDF CONFIGURATION", 
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#E5E7EB"
        )
        pdf_label.pack(anchor="w", padx=20, pady=(0, 8))
        
        pdf_mode_frame = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        pdf_mode_frame.pack(fill="x", padx=20, pady=4)
        pdf_mode_lbl = ctk.CTkLabel(pdf_mode_frame, text="Method:", font=ctk.CTkFont(size=11))
        pdf_mode_lbl.pack(side="left")
        self.pdf_mode_menu = ctk.CTkOptionMenu(
            pdf_mode_frame, 
            values=["Lossless Vector Extract", "Rasterize & Trace (300 DPI)"],
            height=25
        )
        self.pdf_mode_menu.pack(side="right", fill="x", expand=True, padx=(10, 0))
        self.pdf_mode_menu.set("Lossless Vector Extract")
        
        pdf_pages_frame = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        pdf_pages_frame.pack(fill="x", padx=20, pady=(4, 15))
        pdf_pages_lbl = ctk.CTkLabel(pdf_pages_frame, text="Pages:", font=ctk.CTkFont(size=11))
        pdf_pages_lbl.pack(side="left")
        self.pdf_pages_entry = ctk.CTkEntry(
            pdf_pages_frame, 
            placeholder_text="e.g. all, 1, 3-5",
            height=25
        )
        self.pdf_pages_entry.pack(side="right", fill="x", expand=True, padx=(10, 0))
        self.pdf_pages_entry.insert(0, "all")
        
    def create_workspace_center(self):
        """Creates the main workspace panel, containing the drag landing and scrollable file cards."""
        self.workspace_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="#121214")
        self.workspace_frame.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)
        
        # Grid layout for workspace: Header, Content, Footer
        self.workspace_frame.grid_rowconfigure(0, weight=0)  # Top Bar
        self.workspace_frame.grid_rowconfigure(1, weight=1)  # File list / landing
        self.workspace_frame.grid_rowconfigure(2, weight=0)  # Action panel
        self.workspace_frame.grid_columnconfigure(0, weight=1)
        
        # 1. TOP BAR
        top_bar = ctk.CTkFrame(self.workspace_frame, fg_color="transparent", height=60)
        top_bar.grid(row=0, column=0, sticky="ew", padx=25, pady=(20, 10))
        
        workspace_title = ctk.CTkLabel(
            top_bar, 
            text="Active Workspace Queue", 
            font=ctk.CTkFont(size=18, weight="bold")
        )
        workspace_title.pack(side="left", anchor="center")
        
        self.import_button = ctk.CTkButton(
            top_bar, 
            text="➕ Import Files", 
            command=self.import_files,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#3B82F6",
            hover_color="#2563EB",
            width=120
        )
        self.import_button.pack(side="right", anchor="center")
        
        self.clear_button = ctk.CTkButton(
            top_bar, 
            text="🧹 Clear All", 
            command=self.clear_queue,
            font=ctk.CTkFont(size=12),
            fg_color="#27272A",
            hover_color="#3F3F46",
            text_color="#D1D5DB",
            width=90
        )
        self.clear_button.pack(side="right", anchor="center", padx=(0, 10))
        
        # 2. CONTENT VIEW (Double state: Empty state vs Scrollable queue)
        # State A: Empty Landing Zone
        self.landing_frame = ctk.CTkFrame(self.workspace_frame, fg_color="#18181C", border_width=2, border_color="#2D2D36", corner_radius=12)
        self.landing_frame.grid(row=1, column=0, sticky="nsew", padx=25, pady=10)
        
        self.landing_frame.grid_rowconfigure(0, weight=1)
        self.landing_frame.grid_rowconfigure(1, weight=0)
        self.landing_frame.grid_rowconfigure(2, weight=1)
        self.landing_frame.grid_columnconfigure(0, weight=1)
        
        inner_landing = ctk.CTkFrame(self.landing_frame, fg_color="transparent")
        inner_landing.grid(row=1, column=0)
        
        vector_art_lbl = ctk.CTkLabel(
            inner_landing, 
            text="🖼️", 
            font=ctk.CTkFont(size=72)
        )
        vector_art_lbl.pack(pady=10)
        
        instruct_lbl1 = ctk.CTkLabel(
            inner_landing, 
            text="Queue is currently empty", 
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#F3F4F6"
        )
        instruct_lbl1.pack(pady=5)
        
        instruct_lbl2 = ctk.CTkLabel(
            inner_landing, 
            text="Import raster images (PNG, JPG, BMP, WebP) or PDF documents\nand accurately vectorize them offline into SVG assets.", 
            font=ctk.CTkFont(size=12),
            text_color="#9CA3AF",
            justify="center"
        )
        instruct_lbl2.pack(pady=5)
        
        browse_call_btn = ctk.CTkButton(
            inner_landing, 
            text="Select Files to Vectorize", 
            command=self.import_files,
            fg_color="#3B82F6",
            hover_color="#2563EB",
            height=35,
            font=ctk.CTkFont(weight="bold")
        )
        browse_call_btn.pack(pady=15)
        
        # State B: Scrollable List (Initially hidden)
        self.queue_scroll_frame = ctk.CTkScrollableFrame(self.workspace_frame, fg_color="transparent", corner_radius=0)
        # Packed dynamically based on queue presence
        
        # 3. ACTION FOOTER PANEL
        self.action_frame = ctk.CTkFrame(self.workspace_frame, fg_color="#1E1E24", corner_radius=12, height=90)
        self.action_frame.grid(row=2, column=0, sticky="ew", padx=25, pady=(15, 25))
        self.action_frame.grid_propagate(False)
        
        self.action_frame.grid_columnconfigure(0, weight=1)
        self.action_frame.grid_columnconfigure(1, weight=0)
        
        # Stats & Progress Indicators (Left side of footer)
        footer_left = ctk.CTkFrame(self.action_frame, fg_color="transparent")
        footer_left.grid(row=0, column=0, sticky="w", padx=20, pady=12)
        
        self.global_status_label = ctk.CTkLabel(
            footer_left, 
            text="0 files queued in active session", 
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#E5E7EB"
        )
        self.global_status_label.pack(anchor="w")
        
        self.global_progress = ctk.CTkProgressBar(footer_left, width=320, height=8, fg_color="#2D2D36")
        self.global_progress.pack(anchor="w", pady=(8, 0))
        self.global_progress.set(0.0)
        
        # Primary Glowing Convert Button (Right side of footer)
        footer_right = ctk.CTkFrame(self.action_frame, fg_color="transparent")
        footer_right.grid(row=0, column=1, sticky="e", padx=20, pady=12)
        
        self.convert_button = ctk.CTkButton(
            footer_right, 
            text="⚡ Convert Queue", 
            command=self.start_conversion,
            height=45,
            width=180,
            fg_color="#10B981",  # Vibrant emerald green accent for action
            hover_color="#059669",
            font=ctk.CTkFont(size=15, weight="bold")
        )
        self.convert_button.pack(side="right")
        
        # Open folder utility button
        self.open_out_btn = ctk.CTkButton(
            footer_right,
            text="📂 Open Folder",
            command=self.open_output_folder,
            height=45,
            width=120,
            fg_color="#27272A",
            hover_color="#3F3F46",
            text_color="#E5E7EB",
            font=ctk.CTkFont(size=13)
        )
        self.open_out_btn.pack(side="right", padx=(0, 10))
        
    def create_preview_sidebar(self):
        """Creates the right panel, showing detailed information and a scaling thumbnail preview of the selected file."""
        self.preview_frame = ctk.CTkFrame(self, corner_radius=0, width=320, fg_color="#1E1E24")
        self.preview_frame.grid(row=0, column=2, sticky="nsew", padx=0, pady=0)
        self.preview_frame.grid_propagate(False)
        
        # Header
        preview_header = ctk.CTkLabel(
            self.preview_frame, 
            text="🎨 MEDIA PREVIEW", 
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#E5E7EB"
        )
        preview_header.pack(anchor="w", padx=20, pady=(25, 5))
        
        preview_subheader = ctk.CTkLabel(
            self.preview_frame, 
            text="Inspect source composition", 
            font=ctk.CTkFont(size=11),
            text_color="#9CA3AF"
        )
        preview_subheader.pack(anchor="w", padx=20, pady=(0, 20))
        
        # Divider
        divider = ctk.CTkFrame(self.preview_frame, height=2, fg_color="#2D2D36")
        divider.pack(fill="x", padx=15, pady=5)
        
        # 1. Preview Box (The Frame that hosts the CTkImage)
        self.preview_box = ctk.CTkFrame(self.preview_frame, fg_color="#121214", border_width=1, border_color="#2D2D36", corner_radius=8, height=260, width=280)
        self.preview_box.pack(padx=20, pady=15)
        self.preview_box.pack_propagate(False)
        
        self.preview_label = ctk.CTkLabel(
            self.preview_box, 
            text="Select an image or PDF\nto render a thumbnail", 
            text_color="#6B7280",
            font=ctk.CTkFont(size=11),
            justify="center"
        )
        self.preview_label.pack(expand=True, fill="both")
        
        # 2. Metadata details Frame
        self.metadata_frame = ctk.CTkFrame(self.preview_frame, fg_color="#18181F", corner_radius=8, height=180)
        self.metadata_frame.pack(fill="x", padx=20, pady=10)
        self.metadata_frame.pack_propagate(False)
        
        # Metadata Title
        meta_title = ctk.CTkLabel(self.metadata_frame, text="File Information", font=ctk.CTkFont(size=12, weight="bold"), text_color="#3B82F6")
        meta_title.pack(anchor="w", padx=15, pady=(10, 5))
        
        # Data Labels
        self.meta_name = self.create_meta_row(self.metadata_frame, "Name:", "-")
        self.meta_format = self.create_meta_row(self.metadata_frame, "Format:", "-")
        self.meta_size = self.create_meta_row(self.metadata_frame, "Input Size:", "-")
        self.meta_details = self.create_meta_row(self.metadata_frame, "Info:", "-")
        
        # Bottom Tip
        tip_lbl = ctk.CTkLabel(
            self.preview_frame,
            text="💡 Tip: Direct Lossless Extract is instant and generates the smallest, vector-perfect SVG files for PDFs.",
            text_color="#9CA3AF",
            font=ctk.CTkFont(size=11),
            justify="center",
            wraplength=270
        )
        tip_lbl.pack(side="bottom", fill="x", padx=20, pady=25)
        
    def create_meta_row(self, parent, label_text, default_val):
        """Helper to create a structured row for metadata displays."""
        row_frame = ctk.CTkFrame(parent, fg_color="transparent")
        row_frame.pack(fill="x", padx=15, pady=4)
        
        lbl = ctk.CTkLabel(row_frame, text=label_text, font=ctk.CTkFont(size=11, weight="bold"), text_color="#9CA3AF", width=80, anchor="w")
        lbl.pack(side="left")
        
        val = ctk.CTkLabel(row_frame, text=default_val, font=ctk.CTkFont(size=11), text_color="#E5E7EB", anchor="w")
        val.pack(side="left", fill="x", expand=True)
        
        return val

    # --- UI INTERACTION HANDLERS ---
    def on_dest_mode_change(self, mode):
        """Handles switching between original and custom output destinations."""
        if mode == "Custom Directory":
            self.custom_path_frame.pack(fill="x", padx=20, pady=5)
            if not self.output_directory:
                self.browse_output_directory()
        else:
            self.custom_path_frame.pack_forget()
            
    def browse_output_directory(self):
        """Opens a directory browser dialog."""
        folder = filedialog.askdirectory(title="Select Custom SVG Output Folder")
        if folder:
            self.output_directory = os.path.normpath(folder)
            short_path = self.output_directory
            if len(short_path) > 30:
                short_path = "..." + short_path[-27:]
            self.custom_path_label.configure(text=short_path, text_color="#E5E7EB")
        else:
            # Fall back to Same Folder if cancelled
            if not self.output_directory:
                self.dest_mode.set("Same Folder")
                self.custom_path_frame.pack_forget()

    def on_slider_change(self, *args):
        """Called when a custom tuner slider or switch is adjusted."""
        # Enforce preset to "Custom" if they manually adjust things
        if self.preset_menu.get() != "Custom (Advanced)":
            self.preset_menu.set("Custom (Advanced)")
            
    def on_speckle_slide(self, value):
        self.speckle_label.configure(text=f"Speckle Filter: {int(value)} px")
        self.on_slider_change()
        
    def on_color_prec_slide(self, value):
        self.color_prec_label.configure(text=f"Color Precision: {int(value)} bits")
        self.on_slider_change()
        
    def on_corner_slide(self, value):
        self.corner_label.configure(text=f"Corner Threshold: {int(value)}°")
        self.on_slider_change()
        
    def on_path_prec_slide(self, value):
        self.path_prec_label.configure(text=f"Path Precision: {int(value)} decimals")
        self.on_slider_change()

    def on_preset_change(self, preset_name):
        """Applies configuration presets to sliders and options."""
        # Temporarily disable standard change callbacks to prevent preset overwrite
        self.sliders_frame.configure(label_text=f"Parameters Tuning ({preset_name})")
        
        if preset_name == "High Detail (Color)":
            self.colormode_switch.select()
            self.speckle_slider.set(4)
            self.color_prec_slider.set(6)
            self.corner_slider.set(60)
            self.path_prec_slider.set(3)
            self.fitting_menu.set("Spline")
        elif preset_name == "Medium Detail (Color)":
            self.colormode_switch.select()
            self.speckle_slider.set(8)
            self.color_prec_slider.set(5)
            self.corner_slider.set(70)
            self.path_prec_slider.set(2)
            self.fitting_menu.set("Spline")
        elif preset_name == "Flat Logo (Color)":
            self.colormode_switch.select()
            self.speckle_slider.set(16)
            self.color_prec_slider.set(3)
            self.corner_slider.set(90)
            self.path_prec_slider.set(2)
            self.fitting_menu.set("Spline")
        elif preset_name == "Black & White Silhouette":
            self.colormode_switch.deselect()
            self.speckle_slider.set(4)
            self.color_prec_slider.set(3)
            self.corner_slider.set(60)
            self.path_prec_slider.set(2)
            self.fitting_menu.set("Spline")
        
        # Update text labels
        self.speckle_label.configure(text=f"Speckle Filter: {int(self.speckle_slider.get())} px")
        self.color_prec_label.configure(text=f"Color Precision: {int(self.color_prec_slider.get())} bits")
        self.corner_label.configure(text=f"Corner Threshold: {int(self.corner_slider.get())}°")
        self.path_prec_label.configure(text=f"Path Precision: {int(self.path_prec_slider.get())} decimals")
        
        self.update_idletasks()

    def get_current_settings(self):
        """Assembles a parameter dictionary from the current sidebar GUI states."""
        return {
            'colormode': 'color' if self.colormode_switch.get() else 'binary',
            'hierarchical': 'stacked', # Recommended default
            'mode': self.fitting_menu.get().lower(),
            'filter_speckle': int(self.speckle_slider.get()),
            'color_precision': int(self.color_prec_slider.get()),
            'layer_difference': 16, # Optimized base difference
            'corner_threshold': int(self.corner_slider.get()),
            'length_threshold': 4.0,
            'max_iterations': 10,
            'splice_threshold': 45,
            'path_precision': int(self.path_prec_slider.get()),
            
            # PDF specific configs
            'pdf_mode': 'trace' if 'Rasterize' in self.pdf_mode_menu.get() else 'direct',
            'pdf_pages': self.pdf_pages_entry.get().strip() or 'all'
        }

    # --- QUEUE & WORKSPACE OPERATIONS ---
    def import_files(self):
        """Prompts the user to select raster images or PDF documents and queues them."""
        filetypes = [
            ("All Supported Formats", "*.png *.jpg *.jpeg *.bmp *.webp *.pdf"),
            ("Raster Images", "*.png *.jpg *.jpeg *.bmp *.webp"),
            ("PDF Documents", "*.pdf")
        ]
        
        paths = filedialog.askopenfilenames(
            title="Import Media to Queue",
            filetypes=filetypes
        )
        
        if not paths:
            return
            
        for path in paths:
            path = os.path.normpath(path)
            # Avoid duplicate imports
            if any(item['path'] == path for item in self.queue_list):
                continue
                
            self.add_file_to_queue(path)
            
        self.update_workspace_state()

    def add_file_to_queue(self, path):
        """Constructs a UI card frame representing the file and appends it to queue state."""
        self.queue_id_counter += 1
        q_id = self.queue_id_counter
        
        filename = os.path.basename(path)
        ext = os.path.splitext(filename)[1].upper().replace('.', '')
        
        # Calculate readable file size
        bytes_size = os.path.getsize(path)
        if bytes_size < 1024 * 1024:
            size_str = f"{bytes_size / 1024:.1f} KB"
        else:
            size_str = f"{bytes_size / (1024*1024):.2f} MB"
            
        # Create Card Frame inside the scroll view
        card = ctk.CTkFrame(self.queue_scroll_frame, fg_color="#1E1E24", corner_radius=8, height=65)
        card.pack(fill="x", padx=10, pady=5)
        
        # Interactive selection
        card.bind("<Button-1>", lambda e, q=q_id: self.select_queue_item(q))
        
        # Make sub-elements clickable too
        def bind_clicks(widget):
            widget.bind("<Button-1>", lambda e, q=q_id: self.select_queue_item(q))
            for child in widget.winfo_children():
                bind_clicks(child)
                
        # Card Sub-layouts
        # Column 0: Format Badge
        badge_frame = ctk.CTkFrame(card, fg_color="#2D2D36", corner_radius=4, width=50, height=40)
        badge_frame.pack(side="left", padx=15, pady=10)
        badge_frame.pack_propagate(False)
        
        badge_text = "📄" if ext == "PDF" else "🖼️"
        badge_icon = ctk.CTkLabel(badge_frame, text=badge_text, font=ctk.CTkFont(size=14))
        badge_icon.pack(expand=True)
        
        # Column 1: Filename and details
        details_frame = ctk.CTkFrame(card, fg_color="transparent")
        details_frame.pack(side="left", fill="both", expand=True, pady=10)
        
        # Crop filename if excessively long
        display_name = filename
        if len(display_name) > 35:
            display_name = display_name[:32] + "..."
            
        name_lbl = ctk.CTkLabel(details_frame, text=display_name, font=ctk.CTkFont(size=13, weight="bold"), anchor="w")
        name_lbl.pack(anchor="w")
        
        sub_details = ctk.CTkLabel(
            details_frame, 
            text=f"{ext} • {size_str}", 
            font=ctk.CTkFont(size=11), 
            text_color="#9CA3AF",
            anchor="w"
        )
        sub_details.pack(anchor="w")
        
        # Column 2: Progress & State indicators
        indicator_frame = ctk.CTkFrame(card, fg_color="transparent")
        indicator_frame.pack(side="right", padx=15, pady=10)
        
        status_lbl = ctk.CTkLabel(indicator_frame, text="Ready", font=ctk.CTkFont(size=11, weight="bold"), text_color="#3B82F6", width=80, anchor="e")
        status_lbl.pack(side="top", anchor="e", pady=(0, 2))
        
        prog_bar = ctk.CTkProgressBar(indicator_frame, width=120, height=5, fg_color="#2D2D36")
        prog_bar.pack(side="bottom", anchor="e")
        prog_bar.set(0.0)
        prog_bar.pack_forget() # Hide until running
        
        # Column 3: Utility inline action buttons
        action_btn_frame = ctk.CTkFrame(card, fg_color="transparent")
        action_btn_frame.pack(side="right", padx=(5, 10))
        
        # 1. Glowing inline Open Button (initially hidden)
        open_svg_btn = ctk.CTkButton(
            action_btn_frame, 
            text="👁️ Open", 
            width=65, 
            height=28, 
            fg_color="#10B981", 
            hover_color="#059669",
            font=ctk.CTkFont(size=11, weight="bold"),
            command=lambda q=q_id: self.open_result_svg(q)
        )
        # We will pack this upon successful conversion
        
        # 2. Delete item button
        delete_btn = ctk.CTkButton(
            action_btn_frame, 
            text="🗑️", 
            width=28, 
            height=28, 
            fg_color="transparent",
            hover_color="#EF4444",
            text_color="#9CA3AF",
            command=lambda q=q_id: self.remove_item_from_queue(q)
        )
        delete_btn.pack(side="right")
        
        bind_clicks(details_frame)
        bind_clicks(badge_frame)
        
        # Append queue state
        self.queue_list.append({
            'id': q_id,
            'path': path,
            'format': ext,
            'size': size_str,
            'status': 'Ready',
            'card_widget': card,
            'progress_bar': prog_bar,
            'status_label': status_lbl,
            'open_button': open_svg_btn,
            'output_svgs': []
        })
        
        # Trigger preview for the newly added item
        self.select_queue_item(q_id)

    def remove_item_from_queue(self, q_id):
        """Deletes a file representation from both queue states and UI."""
        item = next((x for x in self.queue_list if x['id'] == q_id), None)
        if not item:
            return
            
        # Destroy GUI frame
        item['card_widget'].destroy()
        self.queue_list.remove(item)
        
        if self.selected_queue_id == q_id:
            self.selected_queue_id = None
            self.reset_preview_sidebar()
            
        self.update_workspace_state()
        
        # Reselect another item if queue still has items
        if self.queue_list:
            self.select_queue_item(self.queue_list[-1]['id'])

    def clear_queue(self):
        """Clears all queued files."""
        if self.conversion_active:
            messagebox.showwarning("Active Queue", "Cannot clear queue during background conversion.")
            return
            
        for item in self.queue_list:
            item['card_widget'].destroy()
            
        self.queue_list.clear()
        self.selected_queue_id = None
        self.reset_preview_sidebar()
        self.update_workspace_state()

    def update_workspace_state(self):
        """Controls switching between landing zone and queue list views based on queue counts."""
        count = len(self.queue_list)
        if count == 0:
            self.queue_scroll_frame.pack_forget()
            self.landing_frame.grid(row=1, column=0, sticky="nsew", padx=25, pady=10)
            self.global_status_label.configure(text="0 files queued in active session")
            self.global_progress.set(0.0)
        else:
            self.landing_frame.grid_forget()
            self.queue_scroll_frame.pack(fill="both", expand=True, padx=25, pady=10)
            self.global_status_label.configure(text=f"{count} file{'s' if count > 1 else ''} queued • Ready to Vectorize")

    def select_queue_item(self, q_id):
        """Highlights the selected queue item and triggers thread for preview generation."""
        # Deselect old highlight
        if self.selected_queue_id:
            old_item = next((x for x in self.queue_list if x['id'] == self.selected_queue_id), None)
            if old_item and old_item['card_widget'].winfo_exists():
                old_item['card_widget'].configure(fg_color="#1E1E24", border_width=0)
                
        self.selected_queue_id = q_id
        
        # Highlight new item card
        item = next((x for x in self.queue_list if x['id'] == q_id), None)
        if item:
            item['card_widget'].configure(fg_color="#2D2D3D", border_width=1, border_color="#3B82F6")
            
            # Start background preview generation thread to avoid GUI freeze on large files/PDFs
            threading.Thread(
                target=self.generate_preview_async, 
                args=(item['path'], item['format']),
                daemon=True
            ).start()

    # --- ASYNC LIVE PREVIEW GENERATION ---
    def generate_preview_async(self, file_path, file_format):
        """Loads and resizes previews in background and posts update to main thread."""
        try:
            # Generate crisp aspect-ratio corrected visual
            pil_img, disp_w, disp_h = get_preview_image(file_path, 260, 240)
            
            # Safely request UI updates in main thread
            self.after(0, lambda: self.apply_preview_to_ui(pil_img, disp_w, disp_h, file_path, file_format))
        except Exception as e:
            self.after(0, lambda: self.apply_preview_failed_to_ui(file_path, file_format, str(e)))

    def apply_preview_to_ui(self, pil_image, width, height, path, ext):
        """Loads the computed PIL Image into a CustomTkinter CTkImage and presents it."""
        # Make sure item is still selected
        selected_item = next((x for x in self.queue_list if x['id'] == self.selected_queue_id), None)
        if not selected_item or selected_item['path'] != path:
            return
            
        # Create a modern high-DPI scaling CustomTkinter image
        ctk_preview = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=(width, height))
        
        self.preview_label.configure(image=ctk_preview, text="")
        
        # Update metadata display
        filename = os.path.basename(path)
        if len(filename) > 28:
            filename = filename[:25] + "..."
            
        self.meta_name.configure(text=filename)
        self.meta_format.configure(text=ext)
        self.meta_size.configure(text=selected_item['size'])
        
        # Custom extra details based on file format
        if ext == "PDF":
            try:
                doc = fitz.open(path)
                p_count = doc.page_count
                doc.close()
                self.meta_details.configure(text=f"{p_count} Page{'s' if p_count > 1 else ''}")
            except:
                self.meta_details.configure(text="-")
        else:
            w, h = pil_image.size
            # Show original pixel dimensions from PIL metadata if possible
            try:
                from PIL import Image
                with Image.open(path) as temp_img:
                    orig_w, orig_h = temp_img.size
                self.meta_details.configure(text=f"{orig_w} x {orig_h} px")
            except:
                self.meta_details.configure(text="-")

    def apply_preview_failed_to_ui(self, path, ext, err_msg):
        """Invoked when file preview loading encounters issues."""
        selected_item = next((x for x in self.queue_list if x['id'] == self.selected_queue_id), None)
        if not selected_item or selected_item['path'] != path:
            return
            
        self.preview_label.configure(image=None, text=f"⚠️ Failed to load preview\n\n{err_msg[:40]}...", text_color="#EF4444")
        
        filename = os.path.basename(path)
        if len(filename) > 28:
            filename = filename[:25] + "..."
        self.meta_name.configure(text=filename)
        self.meta_format.configure(text=ext)
        self.meta_size.configure(text=selected_item['size'])
        self.meta_details.configure(text="Load Error")

    def reset_preview_sidebar(self):
        """Cleans out the preview window and sets it to default state."""
        self.preview_label.configure(image=None, text="Select an image or PDF\nto render a thumbnail", text_color="#6B7280")
        self.meta_name.configure(text="-")
        self.meta_format.configure(text="-")
        self.meta_size.configure(text="-")
        self.meta_details.configure(text="-")

    # --- MULTI-THREADED BATCH PROCESSING ---
    def start_conversion(self):
        """Assembles settings, populates background worker queue, and spawns the converter thread."""
        if not self.queue_list:
            messagebox.showinfo("Empty Queue", "Please import files into the workspace before converting.")
            return
            
        if self.conversion_active:
            messagebox.showwarning("Active Session", "Vectorization is currently in progress. Please wait.")
            return
            
        # Disable queue modifications
        self.import_button.configure(state="disabled")
        self.clear_button.configure(state="disabled")
        self.convert_button.configure(state="disabled")
        
        self.conversion_active = True
        self.completed_count = 0
        self.elapsed_start_time = time.time()
        
        # Reset progress states on cards
        for item in self.queue_list:
            if item['status'] != 'Success':
                item['status'] = 'Pending'
                item['status_label'].configure(text="Queued", text_color="#9CA3AF")
                item['progress_bar'].pack(side="bottom", anchor="e")
                item['progress_bar'].set(0.0)
                item['open_button'].pack_forget()
                
        # Gather active vectorization parameters
        settings = self.get_current_settings()
        
        # Enforce destination paths
        custom_out_dir = self.output_directory if self.dest_mode.get() == "Custom Directory" else None
        
        # Clear background conversion queue
        while not self.conversion_queue.empty():
            try:
                self.conversion_queue.get_nowait()
            except queue.Empty:
                break
                
        # Populate Queue
        for item in self.queue_list:
            # Skip items that were already successfully converted to prevent double processing
            if item['status'] == 'Success':
                self.completed_count += 1
                continue
                
            self.conversion_queue.put((item['id'], item['path'], settings, custom_out_dir))
            
        # Update global stats
        self.update_global_progress_stats()
        
        if self.conversion_queue.empty():
            # All items were already successful
            self.on_all_conversions_complete()
            return
            
        # Spawn daemon worker thread to execute files sequentially without hanging GUI
        self.conversion_thread = threading.Thread(target=self.conversion_worker, daemon=True)
        self.conversion_thread.start()

    def conversion_worker(self):
        """Sequential loop executed in daemon thread, processing items in queue."""
        while self.conversion_active:
            try:
                q_task = self.conversion_queue.get(timeout=0.5)
            except queue.Empty:
                # All items finished
                self.after(0, self.on_all_conversions_complete)
                break
                
            q_id, file_path, params, custom_out_dir = q_task
            
            # Set target output directory
            target_out = custom_out_dir if custom_out_dir else os.path.dirname(file_path)
            
            # Core conversion call wrapper
            # Define callback closures to post updates back to main thread
            def local_callback(status_text, percent_val, q=q_id):
                self.after(0, lambda: self.update_card_progress(q, status_text, percent_val))
                
            try:
                # Execute conversion algorithm
                output_svgs = convert_file(file_path, target_out, params, progress_callback=local_callback)
                
                # Signal success
                self.after(0, lambda: self.mark_card_success(q_id, output_svgs))
            except Exception as e:
                # Signal failure
                self.after(0, lambda: self.mark_card_failed(q_id, str(e)))
                
            self.conversion_queue.task_done()

    # --- WORKER CONSOLE FEEDBACK & STATS REFRESH ---
    def update_card_progress(self, q_id, status_text, percent):
        """Updates individual card labels and progress bars based on background worker reports."""
        item = next((x for x in self.queue_list if x['id'] == q_id), None)
        if not item:
            return
            
        item['status'] = 'Processing'
        # Display progress status
        item['status_label'].configure(text=status_text, text_color="#3B82F6")
        item['progress_bar'].set(percent)

    def mark_card_success(self, q_id, output_svgs):
        """Triggered upon successful file translation. Highlights card in green and displays open button."""
        item = next((x for x in self.queue_list if x['id'] == q_id), None)
        if not item:
            return
            
        item['status'] = 'Success'
        item['status_label'].configure(text="✔️ Complete", text_color="#10B981")
        item['progress_bar'].set(1.0)
        item['progress_bar'].pack_forget() # Hide progress bar
        
        item['output_svgs'] = output_svgs
        
        # Pack inline Open Button
        item['open_button'].pack(side="left", padx=(0, 5))
        
        self.completed_count += 1
        self.update_global_progress_stats()

    def mark_card_failed(self, q_id, error_message):
        """Invoked when parsing/tracing exceptions occur. Displays failure card in red."""
        item = next((x for x in self.queue_list if x['id'] == q_id), None)
        if not item:
            return
            
        item['status'] = 'Failed'
        item['status_label'].configure(text="❌ Failed", text_color="#EF4444")
        item['progress_bar'].set(0.0)
        item['progress_bar'].pack_forget()
        
        # Display tooltip details on click or show alert if critical
        print(f"File {item['path']} conversion failed: {error_message}")
        
        self.completed_count += 1
        self.update_global_progress_stats()

    def update_global_progress_stats(self):
        """Calculates global percentages, counts, and remaining time estimations for presentation."""
        total = len(self.queue_list)
        if total == 0:
            return
            
        percent = self.completed_count / total
        self.global_progress.set(percent)
        
        elapsed = time.time() - self.elapsed_start_time if self.elapsed_start_time > 0 else 0
        
        stat_msg = f"{self.completed_count} of {total} files processed • {elapsed:.1f}s elapsed"
        self.global_status_label.configure(text=stat_msg)

    def on_all_conversions_complete(self):
        """Invoked when worker runs empty. Resets panel state and triggers user notification."""
        self.conversion_active = False
        
        # Enable elements back
        self.import_button.configure(state="normal")
        self.clear_button.configure(state="normal")
        self.convert_button.configure(state="normal")
        
        elapsed = time.time() - self.elapsed_start_time if self.elapsed_start_time > 0 else 0
        self.global_status_label.configure(text=f"Batch complete • {len(self.queue_list)} files processed in {elapsed:.1f}s")
        
        # Highlight overall completion status
        messagebox.showinfo(
            "Process Complete", 
            f"Batch conversion completed in {elapsed:.1f} seconds.\nReview successful outputs in the workspace queue."
        )

    # --- SHELL UTILITY EXECUTORS ---
    def open_result_svg(self, q_id):
        """Opens the successfully generated SVG file in the operating system's default browser or editor."""
        item = next((x for x in self.queue_list if x['id'] == q_id), None)
        if not item or not item['output_svgs']:
            return
            
        # Open first generated SVG (usually the only one, or first page of PDF)
        target_path = item['output_svgs'][0]
        
        if not os.path.exists(target_path):
            messagebox.showerror("File Missing", f"Could not find converted SVG asset: {target_path}")
            return
            
        try:
            if sys.platform == "win32":
                os.startfile(target_path)
            elif sys.platform == "darwin":
                subprocess.run(["open", target_path])
            else:
                subprocess.run(["xdg-open", target_path])
        except Exception as e:
            messagebox.showerror("Launch Error", f"Unable to open file: {e}")

    def open_output_folder(self):
        """Opens the active output directory in Windows File Explorer or Mac Finder."""
        # Find directory path
        target_dir = ""
        if self.dest_mode.get() == "Custom Directory" and self.output_directory:
            target_dir = self.output_directory
        elif self.queue_list:
            # Fall back to folder containing the first queued file
            target_dir = os.path.dirname(self.queue_list[0]['path'])
        else:
            messagebox.showinfo("Folder Path", "No files imported yet. Import files or set a custom directory first.")
            return
            
        if not os.path.exists(target_dir):
            messagebox.showerror("Path Missing", f"Output directory does not exist: {target_dir}")
            return
            
        try:
            if sys.platform == "win32":
                os.startfile(target_dir)
            elif sys.platform == "darwin":
                subprocess.run(["open", target_dir])
            else:
                subprocess.run(["xdg-open", target_dir])
        except Exception as e:
            messagebox.showerror("Launch Error", f"Unable to open output directory: {e}")

    def poll_queue(self):
        """Fires repeatedly, ensuring UI maintains high responsive threading feedback."""
        # CustomTkinter main loops handle canvas redrawing internally,
        # but standard periodic after-callbacks help ensure queue synchronization.
        self.after(200, self.poll_queue)


if __name__ == "__main__":
    # Prevent Windows High-DPI blurriness
    try:
        if sys.platform == "win32":
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except:
        pass
        
    app = VectorizerApp()
    app.mainloop()

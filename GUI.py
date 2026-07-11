"""
GUI.py — All tkinter/ttk widget code for WADForge.

The WADForgeApp class builds the entire UI and delegates all
business logic to functions in backend.py.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from tkinter.scrolledtext import ScrolledText
import os
import sys
import struct
import re
import subprocess
from PIL import Image, ImageTk

import backend

# ----------------------------------------------------------------------
# GUI Application
# ----------------------------------------------------------------------

class WADForgeApp:
    def __init__(self, root):
        self.root = root
        self.root.title("WADForge - Quake/HL Texture Manager")
        self.root.geometry("1100x700")
        self.root.minsize(950, 600)
        
        # Load settings from the persistent JSON file via backend
        settings = backend.load_settings()
        
        # State Variables
        self.workspace_dir = tk.StringVar(value=settings["workspace_dir"])
        self.target_wad_path = tk.StringVar()
        self.wad_format = tk.StringVar(value="WAD2")
        self.search_query = tk.StringVar()
        
        # Internal caching
        self.detected_images = [] # List of dicts representing files
        self.wad_contents = []  # List of dicts representing lumps
        
        # Preview state variables
        self.current_preview_image = None
        self.current_preview_source = None
        self.current_preview_name = None
        self.updating_selection = False
        self.zoom_level = 1.0
        self.zoom_fit_enabled = True
        self.canvas_image_id = None
        self._checkerboard_cache = None
        
        # Set Up Styles
        self.setup_styles()
        
        # Build UI
        self.build_ui()
        
        # Initial Scan
        self.refresh_all()

    def setup_styles(self):
        # Catppuccin Mocha-inspired theme
        self.colors = {
            "bg": "#1e1e2e",
            "card": "#252538",
            "overlay": "#313244",
            "text": "#cdd6f4",
            "subtext": "#a6adc8",
            "accent": "#cba6f7",
            "primary": "#89b4fa",
            "success": "#a6e3a1",
            "warning": "#f9e2af",
            "error": "#f38ba8",
            "border": "#45475a",
            "highlight": "#45475a"
        }
        
        self.root.configure(bg=self.colors["bg"])
        
        self.style = ttk.Style()
        self.style.theme_use("clam")
        
        # Configure frames
        self.style.configure("TFrame", background=self.colors["bg"])
        self.style.configure("Card.TFrame", background=self.colors["card"], bordercolor=self.colors["border"], relief="solid", borderwidth=1)
        self.style.configure("Header.TFrame", background=self.colors["card"])
        
        # Configure Labels
        self.style.configure("TLabel", background=self.colors["bg"], foreground=self.colors["text"], font=("Segoe UI", 10))
        self.style.configure("Card.TLabel", background=self.colors["card"], foreground=self.colors["text"], font=("Segoe UI", 10))
        self.style.configure("Title.TLabel", background=self.colors["bg"], foreground=self.colors["accent"], font=("Segoe UI", 16, "bold"))
        self.style.configure("Header.TLabel", background=self.colors["card"], foreground=self.colors["accent"], font=("Segoe UI", 11, "bold"))
        self.style.configure("Sub.TLabel", background=self.colors["bg"], foreground=self.colors["subtext"], font=("Segoe UI", 9, "italic"))
        
        # Configure buttons
        self.style.configure("TButton",
                             background=self.colors["overlay"],
                             foreground=self.colors["text"],
                             bordercolor=self.colors["border"],
                             lightcolor=self.colors["overlay"],
                             darkcolor=self.colors["overlay"],
                             font=("Segoe UI", 9, "bold"))
        self.style.map("TButton",
                       background=[("active", self.colors["highlight"]), ("disabled", self.colors["bg"])],
                       foreground=[("active", "#ffffff"), ("disabled", self.colors["subtext"])])
                       
        self.style.configure("Primary.TButton",
                             background=self.colors["primary"],
                             foreground="#11111b",
                             bordercolor=self.colors["primary"],
                             lightcolor=self.colors["primary"],
                             darkcolor=self.colors["primary"],
                             font=("Segoe UI", 10, "bold"))
        self.style.map("Primary.TButton",
                       background=[("active", "#b4befe"), ("disabled", self.colors["overlay"])],
                       foreground=[("active", "#11111b"), ("disabled", self.colors["subtext"])])
                       
        # Configure entries & dropdowns
        self.style.configure("TEntry", fieldbackground=self.colors["overlay"], foreground=self.colors["text"], bordercolor=self.colors["border"])
        self.style.configure("TCombobox", fieldbackground=self.colors["overlay"], background=self.colors["overlay"], foreground=self.colors["text"], bordercolor=self.colors["border"])
        self.style.map("TCombobox", fieldbackground=[("readonly", self.colors["overlay"])], selectbackground=[("readonly", self.colors["highlight"])])

        # Configure Treeview
        self.style.configure("Treeview",
                             background=self.colors["card"],
                             foreground=self.colors["text"],
                             fieldbackground=self.colors["card"],
                             bordercolor=self.colors["border"],
                             lightcolor=self.colors["card"],
                             darkcolor=self.colors["card"],
                             rowheight=25,
                             font=("Segoe UI", 9))
        self.style.map("Treeview", 
                       background=[("selected", self.colors["highlight"])], 
                       foreground=[("selected", "#ffffff")])
                       
        self.style.configure("Treeview.Heading",
                             background=self.colors["overlay"],
                             foreground=self.colors["accent"],
                             bordercolor=self.colors["border"],
                             lightcolor=self.colors["overlay"],
                             darkcolor=self.colors["overlay"],
                             font=("Segoe UI", 9, "bold"))
        self.style.map("Treeview.Heading", background=[("active", self.colors["highlight"])])

    def build_ui(self):
        # Main Layout Grid
        # Header
        header_frame = ttk.Frame(self.root)
        header_frame.pack(fill=tk.X, padx=15, pady=(10, 5))
        
        title_label = ttk.Label(header_frame, text="WADForge - Quake/HL Texture Manager", style="Title.TLabel")
        title_label.pack(side=tk.LEFT)
        
        subtitle = ttk.Label(header_frame, text="Texture packer & WAD editor for GoldSrc & idTech games", style="Sub.TLabel")
        subtitle.pack(side=tk.LEFT, padx=15, pady=(6, 0))

        # ----------------- Selection Card (Paths & Configuration) -----------------
        paths_card = ttk.Frame(self.root, style="Card.TFrame")
        paths_card.pack(fill=tk.X, padx=15, pady=5)
        
        # Workspace Path Row
        ws_label = ttk.Label(paths_card, text="Workspace Folder:", style="Card.TLabel")
        ws_label.grid(row=0, column=0, padx=10, pady=8, sticky="w")
        
        ws_entry = ttk.Entry(paths_card, textvariable=self.workspace_dir, width=80)
        ws_entry.grid(row=0, column=1, padx=5, pady=8, sticky="ew")
        
        ws_btn_frame = ttk.Frame(paths_card, style="Card.TFrame")
        ws_btn_frame.grid(row=0, column=2, padx=10, pady=8, sticky="ew")
        
        ws_browse = ttk.Button(ws_btn_frame, text="Browse...", command=self.browse_workspace)
        ws_browse.pack(side=tk.LEFT, padx=(0, 2))
        
        ws_save = ttk.Button(ws_btn_frame, text="Save As Default", command=self.save_workspace_settings)
        ws_save.pack(side=tk.LEFT, padx=2)
        
        ws_reset = ttk.Button(ws_btn_frame, text="Restore Default", command=self.restore_workspace_default)
        ws_reset.pack(side=tk.LEFT, padx=(2, 0))
        
        # Target WAD Path Row
        wad_label = ttk.Label(paths_card, text="Target WAD File:", style="Card.TLabel")
        wad_label.grid(row=1, column=0, padx=10, pady=8, sticky="w")
        
        wad_entry = ttk.Entry(paths_card, textvariable=self.target_wad_path, width=80)
        wad_entry.grid(row=1, column=1, padx=5, pady=8, sticky="ew")
        
        wad_btn_frame = ttk.Frame(paths_card)
        wad_btn_frame.configure(style="Card.TFrame")
        wad_btn_frame.grid(row=1, column=2, padx=10, pady=8, sticky="ew")
        
        wad_browse = ttk.Button(wad_btn_frame, text="Select...", command=self.browse_wad)
        wad_browse.pack(side=tk.LEFT, padx=(0, 5))
        
        wad_new = ttk.Button(wad_btn_frame, text="New...", command=self.create_new_wad)
        wad_new.pack(side=tk.LEFT)
        
        # Format Selector & Refresh
        cfg_frame = ttk.Frame(paths_card)
        cfg_frame.configure(style="Card.TFrame")
        cfg_frame.grid(row=2, column=0, columnspan=3, padx=10, pady=8, sticky="ew")
        
        fmt_label = ttk.Label(cfg_frame, text="WAD Format Target:", style="Card.TLabel")
        fmt_label.pack(side=tk.LEFT, padx=(0, 5))
        
        fmt_combo = ttk.Combobox(cfg_frame, textvariable=self.wad_format, values=["WAD2", "WAD3"], width=10, state="readonly")
        fmt_combo.pack(side=tk.LEFT, padx=5)
        fmt_combo.bind("<<ComboboxSelected>>", self.on_format_changed)
        
        info_label = ttk.Label(cfg_frame, text="(WAD2 = Quake 1, WAD3 = Half-Life)", style="Sub.TLabel")
        info_label.pack(side=tk.LEFT, padx=10)
        
        refresh_btn = ttk.Button(cfg_frame, text="Refresh Lists", command=self.refresh_all)
        refresh_btn.pack(side=tk.RIGHT, padx=5)
        
        paths_card.columnconfigure(1, weight=1)

        # ----------------- Paned Window for Lists -----------------
        list_pane = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        list_pane.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)
        
        # Left Panel (Workspace Images)
        image_panel = ttk.Frame(list_pane, style="Card.TFrame")
        list_pane.add(image_panel, weight=35)
        
        image_header = ttk.Frame(image_panel, style="Header.TFrame")
        image_header.pack(fill=tk.X, padx=5, pady=5)
        
        image_title = ttk.Label(image_header, text="Workspace Images", style="Header.TLabel")
        image_title.pack(side=tk.LEFT, pady=5)
        
        # Search Box
        search_label = ttk.Label(image_header, text="Filter:", style="Card.TLabel")
        search_label.pack(side=tk.RIGHT, padx=5)
        
        search_entry = ttk.Entry(image_header, textvariable=self.search_query, width=20)
        search_entry.pack(side=tk.RIGHT, padx=5)
        self.search_query.trace_add("write", lambda *args: self.filter_images())
        
        # Image Treeview
        tree_frame_images = ttk.Frame(image_panel)
        tree_frame_images.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.tree_images = ttk.Treeview(tree_frame_images, columns=("filename", "texname", "res", "format", "status"), show="headings", selectmode="extended")
        self.tree_images.heading("filename", text="File Name", command=lambda: self.sort_tree(self.tree_images, "filename", False))
        self.tree_images.heading("texname", text="Texture Name", command=lambda: self.sort_tree(self.tree_images, "texname", False))
        self.tree_images.heading("res", text="Resolution", command=lambda: self.sort_tree(self.tree_images, "res", False))
        self.tree_images.heading("format", text="Format", command=lambda: self.sort_tree(self.tree_images, "format", False))
        self.tree_images.heading("status", text="Status", command=lambda: self.sort_tree(self.tree_images, "status", False))
        
        self.tree_images.column("filename", width=140)
        self.tree_images.column("texname", width=110)
        self.tree_images.column("res", width=80, anchor="center")
        self.tree_images.column("format", width=85, anchor="center")
        self.tree_images.column("status", width=160)
        
        image_scroll_y = ttk.Scrollbar(tree_frame_images, orient=tk.VERTICAL, command=self.tree_images.yview)
        self.tree_images.configure(yscrollcommand=image_scroll_y.set)
        
        self.tree_images.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        image_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.tree_images.bind("<Double-1>", self.on_image_double_click)
        self.tree_images.bind("<<TreeviewSelect>>", self.on_image_selection_changed)
        
        # Selection tools
        image_ctrls = ttk.Frame(image_panel, style="Card.TFrame")
        image_ctrls.pack(fill=tk.X, padx=5, pady=5)
        
        sel_all_btn = ttk.Button(image_ctrls, text="Select All", command=self.select_all_images)
        sel_all_btn.pack(side=tk.LEFT, padx=5, pady=2)
        
        sel_none_btn = ttk.Button(image_ctrls, text="Clear Selection", command=self.clear_image_selection)
        sel_none_btn.pack(side=tk.LEFT, padx=5, pady=2)
        
        self.selection_lbl = ttk.Label(image_ctrls, text="0 / 0 selected (0 valid)", style="Card.TLabel")
        self.selection_lbl.pack(side=tk.RIGHT, padx=10)
        
        # Middle Panel (WAD Contents)
        wad_panel = ttk.Frame(list_pane, style="Card.TFrame")
        list_pane.add(wad_panel, weight=35)
        
        wad_header = ttk.Frame(wad_panel, style="Header.TFrame")
        wad_header.pack(fill=tk.X, padx=5, pady=5)
        
        wad_title = ttk.Label(wad_header, text="Target WAD Textures", style="Header.TLabel")
        wad_title.pack(side=tk.LEFT, pady=5)
        
        # WAD Convert format button
        self.convert_wad_btn = ttk.Button(wad_header, text="Convert Format", command=self.convert_wad_format)
        self.convert_wad_btn.pack(side=tk.LEFT, padx=10, pady=2)
        
        self.wad_lbl = ttk.Label(wad_header, text="No WAD Loaded", style="Card.TLabel")
        self.wad_lbl.pack(side=tk.RIGHT, padx=5)
        
        # WAD Treeview
        tree_frame_wad = ttk.Frame(wad_panel)
        tree_frame_wad.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.tree_wad = ttk.Treeview(tree_frame_wad, columns=("name", "res", "size"), show="headings", selectmode="extended")
        self.tree_wad.heading("name", text="Texture Name", command=lambda: self.sort_tree(self.tree_wad, "name", False))
        self.tree_wad.heading("res", text="Resolution", command=lambda: self.sort_tree(self.tree_wad, "res", False))
        self.tree_wad.heading("size", text="Size (Bytes)", command=lambda: self.sort_tree(self.tree_wad, "size", False))
        
        self.tree_wad.column("name", width=120)
        self.tree_wad.column("res", width=90, anchor="center")
        self.tree_wad.column("size", width=100, anchor="e")
        
        wad_scroll_y = ttk.Scrollbar(tree_frame_wad, orient=tk.VERTICAL, command=self.tree_wad.yview)
        self.tree_wad.configure(yscrollcommand=wad_scroll_y.set)
        
        self.tree_wad.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        wad_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.tree_wad.bind("<<TreeviewSelect>>", self.on_wad_selection_changed)
        
        # Right Panel (Preview & Action Controls)
        preview_panel = ttk.Frame(list_pane, style="Card.TFrame")
        list_pane.add(preview_panel, weight=30)
        
        preview_header = ttk.Frame(preview_panel, style="Header.TFrame")
        preview_header.pack(fill=tk.X, padx=5, pady=5)
        
        preview_title = ttk.Label(preview_header, text="Texture Preview", style="Header.TLabel")
        preview_title.pack(side=tk.LEFT, pady=5)
        
        # Preview canvas with checkerboard background
        self.preview_frame = ttk.Frame(preview_panel, style="Card.TFrame")
        self.preview_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=(5, 0))
        
        self.preview_canvas = tk.Canvas(
            self.preview_frame, bg="#181825", highlightthickness=0,
            bd=0, cursor="crosshair"
        )
        self.preview_canvas.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
        self.preview_canvas.bind("<Configure>", self.on_preview_frame_resize)
        self.preview_canvas.bind("<Motion>", self.on_preview_motion)
        
        self._canvas_placeholder = self.preview_canvas.create_text(
            200, 100, text="Select an image\nto preview",
            fill=self.colors["subtext"],
            font=("Segoe UI", 10),
            anchor="center",
            tags=("placeholder",)
        )
        
        # Zoom controls
        zoom_frame = ttk.Frame(preview_panel, style="Card.TFrame")
        zoom_frame.pack(fill=tk.X, padx=5, pady=(2, 0))
        
        self.zoom_out_btn = ttk.Button(zoom_frame, text="−", width=3,
                                        command=self.zoom_out, state=tk.DISABLED)
        self.zoom_out_btn.pack(side=tk.LEFT, padx=1)
        
        self.zoom_label = ttk.Label(zoom_frame, text="Fit", style="Card.TLabel",
                                     width=5, anchor="center")
        self.zoom_label.pack(side=tk.LEFT, padx=1)
        
        self.zoom_in_btn = ttk.Button(zoom_frame, text="+", width=3,
                                       command=self.zoom_in, state=tk.DISABLED)
        self.zoom_in_btn.pack(side=tk.LEFT, padx=1)
        
        self.zoom_fit_btn = ttk.Button(zoom_frame, text="1:1", width=3,
                                        command=self.zoom_1to1, state=tk.DISABLED)
        self.zoom_fit_btn.pack(side=tk.LEFT, padx=1)
        
        self.pixel_info_lbl = ttk.Label(zoom_frame, text="", style="Card.TLabel",
                                         font=("Segoe UI", 8))
        self.pixel_info_lbl.pack(side=tk.RIGHT, padx=5)
        
        # Metadata Frame
        meta_frame = ttk.Frame(preview_panel, style="Card.TFrame")
        meta_frame.pack(fill=tk.X, padx=5, pady=(5, 0))
        
        self.meta_name_lbl = ttk.Label(meta_frame, text="Name: -", font=("Segoe UI", 9, "bold"), style="Card.TLabel")
        self.meta_name_lbl.pack(anchor="w", padx=5, pady=1)
        
        self.meta_res_lbl = ttk.Label(meta_frame, text="Resolution: -", style="Card.TLabel")
        self.meta_res_lbl.pack(anchor="w", padx=5, pady=1)
        
        self.meta_src_lbl = ttk.Label(meta_frame, text="Source: -", style="Card.TLabel")
        self.meta_src_lbl.pack(anchor="w", padx=5, pady=1)
        
        self.meta_info_lbl = ttk.Label(meta_frame, text="Format: -", style="Card.TLabel")
        self.meta_info_lbl.pack(anchor="w", padx=5, pady=1)
        
        # Action Buttons — restructured with clear context labels
        self.ops_frame = ttk.Frame(preview_panel, style="Card.TFrame")
        self.ops_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.source_context_label = ttk.Label(
            self.ops_frame, text="Select an image to get started",
            style="Card.TLabel", font=("Segoe UI", 8, "italic")
        )
        self.source_context_label.pack(anchor="w", padx=5, pady=(4, 2))
        
        # Single button row — context-aware enabled/disabled
        btn_frame = ttk.Frame(self.ops_frame, style="Card.TFrame")
        btn_frame.pack(fill=tk.X, padx=2, pady=(0, 4))
        
        self.op_btn_rename = ttk.Button(btn_frame, text="Rename", command=self.on_op_rename)
        self.op_btn_rename.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=1)
        
        self.op_btn_delete = ttk.Button(btn_frame, text="Delete", command=self.on_op_delete)
        self.op_btn_delete.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=1)
        
        self.op_btn_export = ttk.Button(btn_frame, text="Export", command=self.on_op_export)
        self.op_btn_export.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=1)
        
        self.op_btn_replace = ttk.Button(btn_frame, text="Replace", command=self.on_op_replace)
        self.op_btn_replace.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=1)
        
        self._disable_all_op_buttons()

        # ----------------- Actions Panel -----------------
        act_panel = ttk.Frame(self.root, style="Card.TFrame")
        act_panel.pack(fill=tk.X, padx=15, pady=5)

        act_inner = ttk.Frame(act_panel, style="Card.TFrame")
        act_inner.pack(fill=tk.X, padx=20, pady=10)

        self.pack_status_lbl = ttk.Label(
            act_inner, text="Select textures from the workspace to begin",
            style="Card.TLabel", anchor="center", font=("Segoe UI", 9)
        )
        self.pack_status_lbl.pack(fill=tk.X, pady=(0, 6))

        btn_container = ttk.Frame(act_inner, style="Card.TFrame")
        btn_container.pack(fill=tk.X)
        self.pack_btn = ttk.Button(
            btn_container, text="Pack Selected Textures",
            style="Primary.TButton", command=self.pack_textures
        )
        self.pack_btn.pack(expand=True, ipadx=30, ipady=6)

        self.progress = ttk.Progressbar(act_inner, orient=tk.HORIZONTAL, mode='determinate')
        self.progress.pack(fill=tk.X, pady=(8, 0))

        # ----------------- Console Log Pane -----------------
        log_panel = ttk.Frame(self.root, style="Card.TFrame", height=120)
        log_panel.pack(fill=tk.BOTH, expand=False, padx=15, pady=(5, 15))
        
        log_title_frame = ttk.Frame(log_panel, style="Header.TFrame")
        log_title_frame.pack(fill=tk.X, padx=5, pady=2)
        
        log_title = ttk.Label(log_title_frame, text="Execution Log / Warnings", style="Header.TLabel")
        log_title.pack(side=tk.LEFT)
        
        clear_log_btn = ttk.Button(log_title_frame, text="Clear Log", command=self.clear_log)
        clear_log_btn.pack(side=tk.RIGHT)
        
        self.log_text = ScrolledText(log_panel, height=4, background="#11111b", foreground=self.colors["text"], insertbackground=self.colors["text"], font=("Consolas", 9), state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Tags for colored logs
        self.log_text.tag_config("log_info", foreground=self.colors["text"])
        self.log_text.tag_config("log_warning", foreground=self.colors["warning"])
        self.log_text.tag_config("log_error", foreground=self.colors["error"])
        self.log_text.tag_config("log_success", foreground=self.colors["success"])

    # ----------------------------------------------------------------------
    # UI Control Handlers
    # ----------------------------------------------------------------------

    def log(self, message, level="info"):
        self.log_text.config(state=tk.NORMAL)
        tag = f"log_{level}"
        self.log_text.insert(tk.END, f"[{level.upper()}] {message}\n", tag)
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def clear_log(self):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete("1.0", tk.END)
        self.log_text.config(state=tk.DISABLED)

    def browse_workspace(self):
        dir_path = filedialog.askdirectory(initialdir=self.workspace_dir.get(), title="Select Workspace Folder")
        if dir_path:
            self.workspace_dir.set(dir_path)
            self.refresh_all()

    def save_workspace_settings(self):
        folder = self.workspace_dir.get()
        if backend.save_settings(folder):
            self.log(f"Workspace path default successfully stored to config.json", "success")
            messagebox.showinfo("Settings Saved", "Current folder path saved as your default workspace!", parent=self.root)
        else:
            self.log("Failed to write configurations to config.json", "error")

    def restore_workspace_default(self):
        default_dir = backend.restore_default_settings()
        self.workspace_dir.set(default_dir)
        self.log(f"Workspace reset to executable directory default.", "info")
        self.refresh_all()

    def browse_wad(self):
        file_path = filedialog.askopenfilename(
            initialdir=self.workspace_dir.get(),
            title="Select WAD File",
            filetypes=[("Quake/HL WAD Files", "*.wad"), ("All Files", "*.*")]
        )
        if file_path:
            self.target_wad_path.set(file_path)
            self.refresh_wad()

    def create_new_wad(self):
        file_path = filedialog.asksaveasfilename(
            initialdir=self.workspace_dir.get(),
            title="Create New WAD",
            defaultextension=".wad",
            filetypes=[("Quake/HL WAD Files", "*.wad")]
        )
        if file_path:
            self.target_wad_path.set(file_path)
            magic_bytes = self.wad_format.get().encode('ascii')
            wad = backend.WadFile(magic_bytes)
            try:
                wad.save(file_path)
                self.log(f"Created new empty {self.wad_format.get()} file: {os.path.basename(file_path)}", "success")
            except Exception as e:
                self.log(f"Failed to create new WAD: {str(e)}", "error")
            self.refresh_wad()

    def on_format_changed(self, event=None):
        target = self.target_wad_path.get()
        if target and os.path.exists(target):
            try:
                with open(target, 'rb') as f:
                    magic = f.read(4)
                sel_magic = self.wad_format.get().encode('ascii')
                if magic in (b'WAD2', b'WAD3') and magic != sel_magic:
                    self.log(f"Target file has magic {magic.decode('ascii')}, but dropdown is {self.wad_format.get()}. Changing dropdown to match file.", "warning")
                    self.wad_format.set(magic.decode('ascii'))
            except Exception:
                pass

    def select_all_images(self):
        self.tree_images.selection_set(self.tree_images.get_children())
        self.on_image_selection_changed()

    def clear_image_selection(self):
        self.tree_images.selection_remove(self.tree_images.get_children())
        self.on_image_selection_changed()

    def on_image_double_click(self, event):
        item = self.tree_images.focus()
        if not item:
            return
        vals = self.tree_images.item(item, "values")
        if vals:
            filename = vals[0]
            full_path = os.path.join(self.workspace_dir.get(), filename)
            if os.path.exists(full_path):
                self.log(f"Opening {filename} in system viewer...", "info")
                try:
                    if os.name == 'nt':
                        os.startfile(full_path)
                    elif sys.platform == 'darwin':
                        subprocess.call(('open', full_path))
                    else:
                        subprocess.call(('xdg-open', full_path))
                except Exception as e:
                    self.log(f"Could not open file: {str(e)}", "error")

    # ----------------------------------------------------------------------
    # Core Scan & Refresh (delegates to backend)
    # ----------------------------------------------------------------------

    def refresh_all(self):
        self.clear_log()
        self.log("Refreshing lists...", "info")
        self.refresh_images()
        self.refresh_wad()

    def refresh_images(self):
        # Clear list
        for item in self.tree_images.get_children():
            self.tree_images.delete(item)
            
        self.detected_images = []
        folder = self.workspace_dir.get()
        
        try:
            result = backend.scan_workspace_images(folder)
        except FileNotFoundError as e:
            self.log(str(e), "error")
            return
        except Exception as e:
            self.log(f"Failed to scan directory: {str(e)}", "error")
            return
        
        if not result:
            self.log("No valid image files found in workspace folder.", "warning")
            self.selection_lbl.config(text="0 / 0 selected (0 valid)")
            return
        
        self.detected_images, warnings = result
        
        # Log any warnings from the scan
        for level, msg in warnings:
            self.log(msg, level)
        
        self.filter_images()

    def filter_images(self):
        # Repopulate Treeview based on filter
        for item in self.tree_images.get_children():
            self.tree_images.delete(item)
            
        query = self.search_query.get().lower().strip()
        
        for info in self.detected_images:
            if query and query not in info["filename"].lower() and query not in info["texname"].lower():
                continue
                
            item_id = self.tree_images.insert("", tk.END, values=(
                info["filename"],
                info["texname"],
                info["res"],
                info["format"],
                info["status"]
            ))
            
            # Tags for row color formatting
            status = info["status"]
            if status.startswith("ERR:") or status.startswith("Error"):
                self.tree_images.item(item_id, tags=("error",))
            elif status.startswith("WARN:"):
                self.tree_images.item(item_id, tags=("warning",))
            elif status.startswith("CONFLICT:"):
                self.tree_images.item(item_id, tags=("conflict",))
            elif status.startswith("DUP:"):
                self.tree_images.item(item_id, tags=("duplicate",))
            else:
                self.tree_images.item(item_id, tags=("ok",))
                
        # Configure tags colors in Treeview
        self.tree_images.tag_configure("error", foreground=self.colors["error"])
        self.tree_images.tag_configure("warning", foreground=self.colors["warning"])
        self.tree_images.tag_configure("conflict", foreground=self.colors["warning"])
        self.tree_images.tag_configure("duplicate", foreground=self.colors["subtext"])
        self.tree_images.tag_configure("ok", foreground=self.colors["text"])
        
        self.on_image_selection_changed()

    def _update_pack_status(self):
        valid = sum(1 for b in self.detected_images if b["valid"])
        selected = len(self.tree_images.selection())
        if selected > 0:
            valid_in_sel = 0
            for item in self.tree_images.selection():
                vals = self.tree_images.item(item, "values")
                if vals:
                    for info in self.detected_images:
                        if info["filename"] == vals[0] and info["valid"]:
                            valid_in_sel += 1
                            break
            self.pack_status_lbl.config(
                text=f"{valid_in_sel} valid of {selected} selected  —  ready to pack"
            )
        elif valid > 0:
            self.pack_status_lbl.config(
                text=f"{valid} valid textures available  —  select specific files or pack all"
            )
        else:
            self.pack_status_lbl.config(
                text="No valid textures found in the workspace"
            )

    def refresh_wad(self):
        for item in self.tree_wad.get_children():
            self.tree_wad.delete(item)
            
        target = self.target_wad_path.get()
        if not target:
            self.wad_lbl.config(text="No WAD Loaded")
            return
            
        if not os.path.exists(target):
            self.wad_lbl.config(text="File Not Found")
            return
            
        self.log(f"Reading target WAD file: {os.path.basename(target)}", "info")
        try:
            loaded_format, entries_list = backend.read_wad_contents(target)
            
            self.wad_format.set(loaded_format)
            self.wad_lbl.config(text=f"{loaded_format} loaded ({len(entries_list)} textures)")
            
            for entry_info in entries_list:
                self.tree_wad.insert("", tk.END, values=(
                    entry_info["name"],
                    entry_info["res"],
                    entry_info["size"]
                ))
                
        except Exception as e:
            self.wad_lbl.config(text="Error Reading File")
            self.log(f"Error loading target WAD: {str(e)}", "error")

    # ----------------------------------------------------------------------
    # Preview helpers
    # ----------------------------------------------------------------------

    def _disable_all_op_buttons(self):
        for btn in (self.op_btn_rename, self.op_btn_delete,
                     self.op_btn_export, self.op_btn_replace):
            btn.config(state=tk.DISABLED)

    def _update_op_context(self, source, count=1):
        colors = self.colors
        plural = "s" if count > 1 else ""

        if source == "workspace":
            self.source_context_label.config(
                text=f"▸ Workspace File{plural} selected — Rename & Delete operate on disk",
                foreground=colors["primary"]
            )
            self.op_btn_rename.config(state=tk.NORMAL)
            self.op_btn_delete.config(state=tk.NORMAL)
            self.op_btn_export.config(state=tk.DISABLED)
            self.op_btn_replace.config(state=tk.DISABLED)
        elif source == "workspace_bulk":
            self.source_context_label.config(
                text=f"▸ {count} Workspace Files selected — bulk delete only",
                foreground=colors["primary"]
            )
            self.op_btn_rename.config(state=tk.DISABLED)
            self.op_btn_delete.config(state=tk.NORMAL)
            self.op_btn_export.config(state=tk.DISABLED)
            self.op_btn_replace.config(state=tk.DISABLED)
        elif source == "wad":
            self.source_context_label.config(
                text=f"▸ WAD Texture selected — operates inside the open WAD",
                foreground=colors["accent"]
            )
            self.op_btn_rename.config(state=tk.NORMAL)
            self.op_btn_delete.config(state=tk.NORMAL)
            self.op_btn_export.config(state=tk.NORMAL)
            self.op_btn_replace.config(state=tk.NORMAL)
        elif source == "wad_bulk":
            self.source_context_label.config(
                text=f"▸ {count} WAD Textures selected — bulk export/delete inside WAD",
                foreground=colors["accent"]
            )
            self.op_btn_rename.config(state=tk.DISABLED)
            self.op_btn_delete.config(state=tk.NORMAL)
            self.op_btn_export.config(state=tk.NORMAL)
            self.op_btn_replace.config(state=tk.DISABLED)
        else:
            self.source_context_label.config(
                text="Select an image to get started",
                foreground=colors["subtext"]
            )
            self._disable_all_op_buttons()

    def _make_checkerboard(self, w, h, cell=10):
        key = (w, h, cell)
        if self._checkerboard_cache and self._checkerboard_cache[0] == key:
            return self._checkerboard_cache[1]

        tile = Image.new("RGB", (cell * 2, cell * 2), (24, 24, 37))
        light = (40, 40, 56)
        for y in range(cell):
            for x in range(cell):
                tile.putpixel((cell + x, y), light)
                tile.putpixel((x, cell + y), light)

        cb = Image.new("RGB", (w, h))
        for y in range(0, h, cell * 2):
            for x in range(0, w, cell * 2):
                cb.paste(tile, (x, y))
        self._checkerboard_cache = (key, cb)
        return cb

    def on_preview_motion(self, event):
        if not self.current_preview_image:
            self.pixel_info_lbl.config(text="")
            return
        img = self.current_preview_image
        cw = self.preview_canvas.winfo_width()
        ch = self.preview_canvas.winfo_height()

        if self.canvas_image_id:
            coords = self.preview_canvas.coords(self.canvas_image_id)
            if not coords:
                self.pixel_info_lbl.config(text="")
                return
            cx, cy = coords
            scaled_w = img.size[0] * self.zoom_level
            scaled_h = img.size[1] * self.zoom_level
            ix = event.x - cx + scaled_w // 2
            iy = event.y - cy + scaled_h // 2
            px = int(ix / self.zoom_level)
            py = int(iy / self.zoom_level)

            if 0 <= px < img.size[0] and 0 <= py < img.size[1]:
                pixel = img.getpixel((px, py))
                if isinstance(pixel, int):
                    self.pixel_info_lbl.config(text=f"X:{px} Y:{py}  idx:{pixel}")
                else:
                    r, g, b = pixel[:3]
                    self.pixel_info_lbl.config(text=f"X:{px} Y:{py}  R:{r} G:{g} B:{b}")
                return
        self.pixel_info_lbl.config(text="")

    def zoom_in(self):
        self.zoom_level = min(8.0, self.zoom_level * 1.25)
        self.zoom_fit_enabled = False
        self._update_zoom_label()
        self.update_preview_display()

    def zoom_out(self):
        self.zoom_level = max(0.125, self.zoom_level / 1.25)
        self.zoom_fit_enabled = False
        self._update_zoom_label()
        self.update_preview_display()

    def zoom_1to1(self):
        self.zoom_level = 1.0
        self.zoom_fit_enabled = False
        self._update_zoom_label()
        self.update_preview_display()

    def zoom_fit(self):
        self.zoom_fit_enabled = True
        self._update_zoom_label()
        self.update_preview_display()

    def _update_zoom_label(self):
        if self.zoom_fit_enabled:
            self.zoom_label.config(text="Fit")
        else:
            self.zoom_label.config(text=f"{int(self.zoom_level * 100)}%")

    def _enable_zoom_controls(self, enable):
        state = tk.NORMAL if enable else tk.DISABLED
        self.zoom_out_btn.config(state=state)
        self.zoom_in_btn.config(state=state)
        self.zoom_fit_btn.config(state=state)

    # ----------------------------------------------------------------------
    # Selection & Preview Handlers
    # ----------------------------------------------------------------------

    def on_image_selection_changed(self, event=None):
        if getattr(self, 'updating_selection', False):
            return
            
        selected_items = self.tree_images.selection()
        total_selected = len(selected_items)
        valid_selected = 0
        
        for item in selected_items:
            vals = self.tree_images.item(item, "values")
            if vals:
                filename = vals[0]
                for info in self.detected_images:
                    if info["filename"] == filename and info["valid"]:
                        valid_selected += 1
                        break
                        
        self.selection_lbl.config(text=f"{total_selected} / {len(self.detected_images)} selected ({valid_selected} valid)")
        
        # Clear WAD tree selection quietly
        if total_selected > 0:
            self.clear_tree_selection(self.tree_wad)
            
        self.update_preview_from_selection()
        self._update_pack_status()
        
    def on_wad_selection_changed(self, event=None):
        if getattr(self, 'updating_selection', False):
            return
            
        selected_items = self.tree_wad.selection()
        total_selected = len(selected_items)
        
        # Clear BMP tree selection quietly
        if total_selected > 0:
            self.clear_tree_selection(self.tree_images)
            
        self.update_preview_from_selection()

    def clear_tree_selection(self, tree):
        self.updating_selection = True
        tree.selection_remove(tree.selection())
        self.updating_selection = False

    def update_preview_from_selection(self):
        image_sel = self.tree_images.selection()
        wad_sel = self.tree_wad.selection()

        self.current_preview_image = None
        self.current_preview_source = None
        self.current_preview_name = None

        self.preview_canvas.delete("all")
        self.canvas_image_id = None

        if len(image_sel) == 1:
            vals = self.tree_images.item(image_sel[0], "values")
            if vals:
                filename = vals[0]
                full_path = os.path.join(self.workspace_dir.get(), filename)
                if os.path.exists(full_path):
                    try:
                        img = Image.open(full_path)
                        img.load()
                        self.current_preview_image = img
                        self.current_preview_source = "workspace"
                        self.current_preview_name = filename

                        self.meta_name_lbl.config(text=f"Name: {filename}")
                        self.meta_res_lbl.config(text=f"Resolution: {img.size[0]}x{img.size[1]}")
                        self.meta_src_lbl.config(text="Source: Workspace Image")
                        self.meta_info_lbl.config(text=f"Format: {img.mode}")
                    except Exception as e:
                        self._draw_placeholder(f"Error:\n{str(e)[:40]}")
                        self.meta_name_lbl.config(text=f"Name: {filename}")
                        self.meta_res_lbl.config(text="Resolution: Unknown")
                        self.meta_src_lbl.config(text="Source: Workspace Image")
                        self.meta_info_lbl.config(text="Format: Unknown")

        elif len(image_sel) > 1:
            self.current_preview_source = "workspace_bulk"
            count = len(image_sel)
            self._draw_placeholder(f"{count} files\nselected")
            self.meta_name_lbl.config(text=f"Multiple Files ({count})")
            self.meta_res_lbl.config(text="-")
            self.meta_src_lbl.config(text="Source: Workspace Images")
            self.meta_info_lbl.config(text="-")

        elif len(wad_sel) == 1:
            vals = self.tree_wad.item(wad_sel[0], "values")
            if vals:
                entry_name = vals[0]
                target = self.target_wad_path.get()
                if target and os.path.exists(target):
                    try:
                        wad = backend.WadFile.load(target)
                        if entry_name in wad.entries:
                            entry = wad.entries[entry_name]
                            img = backend.decode_miptex_to_image(entry.data, self.wad_format.get())
                            self.current_preview_image = img
                            self.current_preview_source = "wad"
                            self.current_preview_name = entry_name

                            self.meta_name_lbl.config(text=f"Name: {entry_name}")
                            self.meta_res_lbl.config(text=f"Resolution: {img.size[0]}x{img.size[1]}")
                            self.meta_src_lbl.config(text="Source: WAD Texture")
                            self.meta_info_lbl.config(text=f"Format: {self.wad_format.get()} Lump")
                    except Exception as e:
                        self._draw_placeholder(f"Decode error:\n{str(e)[:40]}")
                        self.meta_name_lbl.config(text=f"Name: {entry_name}")
                        self.meta_res_lbl.config(text="Resolution: Unknown")
                        self.meta_src_lbl.config(text="Source: WAD Texture")
                        self.meta_info_lbl.config(text="Format: Unknown")

        elif len(wad_sel) > 1:
            self.current_preview_source = "wad_bulk"
            count = len(wad_sel)
            self._draw_placeholder(f"{count} textures\nselected")
            self.meta_name_lbl.config(text=f"Multiple Textures ({count})")
            self.meta_res_lbl.config(text="-")
            self.meta_src_lbl.config(text="Source: WAD Textures")
            self.meta_info_lbl.config(text="-")

        else:
            self._draw_placeholder("Select an image\nto preview")
            self.meta_name_lbl.config(text="Name: -")
            self.meta_res_lbl.config(text="Resolution: -")
            self.meta_src_lbl.config(text="Source: -")
            self.meta_info_lbl.config(text="Format: -")

        self._update_op_context(
            self.current_preview_source,
            len(image_sel) if self.current_preview_source in ("workspace", "workspace_bulk") else len(wad_sel)
        )

        if self.current_preview_source in ("workspace", "wad"):
            self.zoom_fit_enabled = True
            self._update_zoom_label()
            self._enable_zoom_controls(True)
        else:
            self._enable_zoom_controls(False)

        self.update_preview_display()

    def _draw_placeholder(self, text):
        self.preview_canvas.delete("all")
        self.canvas_image_id = None
        cw = max(60, self.preview_canvas.winfo_width())
        ch = max(60, self.preview_canvas.winfo_height())
        self.preview_canvas.create_text(
            cw // 2, ch // 2,
            text=text, fill=self.colors["subtext"],
            font=("Segoe UI", 10), anchor="center"
        )

    def update_preview_display(self):
        self.preview_canvas.delete("all")
        self.canvas_image_id = None

        if not self.current_preview_image:
            self._draw_placeholder("Select an image\nto preview")
            return

        img = self.current_preview_image
        orig_w, orig_h = img.size
        cw = max(60, self.preview_canvas.winfo_width())
        ch = max(60, self.preview_canvas.winfo_height())

        if self.zoom_fit_enabled:
            self.zoom_level = min(cw / orig_w, ch / orig_h)
            self._update_zoom_label()

        scaled_w = int(orig_w * self.zoom_level)
        scaled_h = int(orig_h * self.zoom_level)

        if scaled_w < 1 or scaled_h < 1:
            return

        display_img = img
        if display_img.mode in ("P", "L"):
            display_img = display_img.convert("RGBA")

        resample = Image.Resampling.NEAREST if self.zoom_level >= 1.0 else Image.Resampling.BILINEAR
        scaled_img = display_img.resize((scaled_w, scaled_h), resample)

        cb = self._make_checkerboard(scaled_w, scaled_h, cell=max(6, int(8 * self.zoom_level)))
        cb.paste(scaled_img, (0, 0), scaled_img)

        self._preview_photo = ImageTk.PhotoImage(cb)
        x = cw // 2
        y = ch // 2
        self.canvas_image_id = self.preview_canvas.create_image(
            x, y, image=self._preview_photo, anchor="center"
        )

    def on_preview_frame_resize(self, event=None):
        if self.current_preview_image and self.zoom_fit_enabled:
            self.zoom_level = 0
        self.update_preview_display()

    # ----------------------------------------------------------------------
    # Operation Handlers (delegate to backend, handle UI feedback)
    # ----------------------------------------------------------------------

    def on_op_rename(self):
        source = self.current_preview_source
        name = self.current_preview_name
        
        if source == "workspace":
            new_name = simpledialog.askstring("Rename Workspace File", "Enter new filename:", initialvalue=name, parent=self.root)
            if new_name:
                try:
                    final_name = backend.rename_workspace_file(self.workspace_dir.get(), name, new_name)
                    self.log(f"Renamed file '{name}' to '{final_name}'", "success")
                    self.refresh_images()
                    # Re-select renamed file
                    for item in self.tree_images.get_children():
                        vals = self.tree_images.item(item, "values")
                        if vals and vals[0] == final_name:
                            self.tree_images.selection_set(item)
                            self.tree_images.see(item)
                            break
                except FileNotFoundError:
                    return
                except FileExistsError as e:
                    messagebox.showerror("Error", str(e), parent=self.root)
                except Exception as e:
                    self.log(f"Failed to rename file: {str(e)}", "error")
                    messagebox.showerror("Error", f"Failed to rename file:\n{str(e)}", parent=self.root)
                    
        elif source == "wad":
            target_path = self.target_wad_path.get()
            if not target_path or not os.path.exists(target_path):
                return
            new_name = simpledialog.askstring("Rename WAD Texture", "Enter new texture name (max 15 chars):", initialvalue=name, parent=self.root)
            if new_name:
                try:
                    final_name = backend.rename_wad_entry(target_path, name, new_name)
                    self.log(f"Renamed WAD texture '{name}' to '{final_name}'", "success")
                    self.refresh_wad()
                    # Re-select renamed entry
                    for item in self.tree_wad.get_children():
                        vals = self.tree_wad.item(item, "values")
                        if vals and vals[0] == final_name:
                            self.tree_wad.selection_set(item)
                            self.tree_wad.see(item)
                            break
                except (ValueError, KeyError) as e:
                    messagebox.showerror("Error", str(e), parent=self.root)
                except Exception as e:
                    self.log(f"Failed to rename WAD texture: {str(e)}", "error")
                    messagebox.showerror("Error", f"Failed to rename WAD texture:\n{str(e)}", parent=self.root)

    def on_op_delete(self):
        source = self.current_preview_source
        
        if source == "workspace":
            name = self.current_preview_name
            if messagebox.askyesno("Delete File", f"Are you sure you want to delete '{name}' from the workspace?", parent=self.root):
                success, errors = backend.delete_workspace_files(self.workspace_dir.get(), [name])
                if errors:
                    for fname, err in errors:
                        self.log(f"Failed to delete '{fname}': {err}", "error")
                    messagebox.showerror("Error", f"Failed to delete file:\n{errors[0][1]}", parent=self.root)
                else:
                    self.log(f"Deleted file '{name}'", "success")
                self.refresh_images()
                    
        elif source == "workspace_bulk":
            sel = self.tree_images.selection()
            filenames = []
            for item in sel:
                vals = self.tree_images.item(item, "values")
                if vals:
                    filenames.append(vals[0])
            if not filenames:
                return
            if messagebox.askyesno("Delete Files", f"Are you sure you want to delete these {len(filenames)} files from the workspace?", parent=self.root):
                success, errors = backend.delete_workspace_files(self.workspace_dir.get(), filenames)
                for fname, err in errors:
                    self.log(f"Failed to delete '{fname}': {err}", "error")
                self.log(f"Deleted {success} of {len(filenames)} files", "success" if success == len(filenames) else "warning")
                self.refresh_images()
                
        elif source == "wad":
            name = self.current_preview_name
            target_path = self.target_wad_path.get()
            if not target_path or not os.path.exists(target_path):
                return
            if messagebox.askyesno("Delete Texture", f"Are you sure you want to delete texture '{name}' from the WAD?", parent=self.root):
                try:
                    count = backend.delete_wad_entries(target_path, [name])
                    if count > 0:
                        self.log(f"Deleted texture '{name}' from WAD", "success")
                    else:
                        self.log(f"Failed to delete texture: Entry '{name}' not found", "error")
                    self.refresh_wad()
                except Exception as e:
                    self.log(f"Failed to delete texture: {str(e)}", "error")
                    messagebox.showerror("Error", f"Failed to delete texture:\n{str(e)}", parent=self.root)
                    
        elif source == "wad_bulk":
            sel = self.tree_wad.selection()
            names = []
            for item in sel:
                vals = self.tree_wad.item(item, "values")
                if vals:
                    names.append(vals[0])
            if not names:
                return
            target_path = self.target_wad_path.get()
            if not target_path or not os.path.exists(target_path):
                return
            if messagebox.askyesno("Delete Textures", f"Are you sure you want to delete these {len(names)} textures from the WAD?", parent=self.root):
                try:
                    count = backend.delete_wad_entries(target_path, names)
                    self.log(f"Deleted {count} of {len(names)} textures from WAD", "success")
                    self.refresh_wad()
                except Exception as e:
                    self.log(f"Failed to delete textures: {str(e)}", "error")
                    messagebox.showerror("Error", f"Failed to delete textures:\n{str(e)}", parent=self.root)

    def on_op_export(self):
        source = self.current_preview_source
        
        if source == "wad":
            name = self.current_preview_name
            target_path = self.target_wad_path.get()
            if not target_path or not os.path.exists(target_path):
                return
            filename = filedialog.asksaveasfilename(
                initialdir=self.workspace_dir.get(),
                initialfile=f"{name}.bmp",
                defaultextension=".bmp",
                filetypes=[("BMP Files", "*.bmp"), ("PNG Files", "*.png"), ("All Files", "*.*")],
                title="Export Texture",
                parent=self.root
            )
            if filename:
                try:
                    backend.export_wad_entry(target_path, name, filename, self.wad_format.get())
                    self.log(f"Exported texture '{name}' to '{filename}'", "success")
                    messagebox.showinfo("Export Successful", f"Successfully exported texture '{name}' to {os.path.basename(filename)}", parent=self.root)
                except KeyError as e:
                    self.log(f"Failed to export: {str(e)}", "error")
                except Exception as e:
                    self.log(f"Failed to export texture: {str(e)}", "error")
                    messagebox.showerror("Export Error", f"Failed to export texture:\n{str(e)}", parent=self.root)
                    
        elif source == "wad_bulk":
            sel = self.tree_wad.selection()
            names = []
            for item in sel:
                vals = self.tree_wad.item(item, "values")
                if vals:
                    names.append(vals[0])
            if not names:
                return
            target_path = self.target_wad_path.get()
            if not target_path or not os.path.exists(target_path):
                return
            export_dir = filedialog.askdirectory(
                initialdir=self.workspace_dir.get(),
                title=f"Export {len(names)} Textures to Folder",
                parent=self.root
            )
            if export_dir:
                try:
                    count = backend.export_wad_entries_bulk(target_path, names, export_dir, self.wad_format.get())
                    self.log(f"Exported {count} of {len(names)} textures to '{export_dir}'", "success")
                    messagebox.showinfo("Export Complete", f"Successfully exported {count} textures to:\n{export_dir}", parent=self.root)
                except Exception as e:
                    self.log(f"Failed bulk export: {str(e)}", "error")
                    messagebox.showerror("Export Error", f"Failed bulk export:\n{str(e)}", parent=self.root)

    def on_op_replace(self):
        source = self.current_preview_source
        name = self.current_preview_name
        target_path = self.target_wad_path.get()
        
        if source == "wad" and target_path and os.path.exists(target_path):
            image_path = filedialog.askopenfilename(
                initialdir=self.workspace_dir.get(),
                title=f"Select Image to replace texture '{name}'",
                filetypes=[
                    ("All Supported Images", "*.bmp;*.png;*.tga;*.pcx;*.jpg;*.jpeg;*.gif"),
                    ("BMP Files", "*.bmp"), 
                    ("PNG Files", "*.png"), 
                    ("TGA Files", "*.tga"),
                    ("PCX Files", "*.pcx"),
                    ("JPEG Files", "*.jpg;*.jpeg"),
                    ("All Files", "*.*")
                ],
                parent=self.root
            )
            if image_path:
                try:
                    backend.replace_wad_entry(target_path, name, image_path, self.wad_format.get())
                    self.log(f"Replaced texture '{name}' inside WAD with '{os.path.basename(image_path)}'", "success")
                    self.refresh_wad()
                    # Re-select the entry
                    for item in self.tree_wad.get_children():
                        vals = self.tree_wad.item(item, "values")
                        if vals and vals[0] == name:
                            self.tree_wad.selection_set(item)
                            break
                except ValueError as e:
                    messagebox.showerror("Invalid Size", str(e), parent=self.root)
                except Exception as e:
                    self.log(f"Failed to replace texture: {str(e)}", "error")
                    messagebox.showerror("Replacement Error", f"Failed to replace texture:\n{str(e)}", parent=self.root)

    def convert_wad_format(self):
        target_path = self.target_wad_path.get()
        if not target_path or not os.path.exists(target_path):
            messagebox.showwarning("No WAD", "Please load a WAD file first.", parent=self.root)
            return
            
        current_format = self.wad_format.get()
        target_format = "WAD3" if current_format == "WAD2" else "WAD2"
        
        if messagebox.askyesno("Convert WAD Format", f"Are you sure you want to convert the open WAD from {current_format} to {target_format}?\nThis will re-save the WAD structure.", parent=self.root):
            try:
                modified = backend.convert_wad_format_file(target_path, current_format, target_format)
                self.wad_format.set(target_format)
                self.log(f"Converted WAD format to {target_format}. Modified {modified} entries.", "success")
                self.refresh_wad()
            except Exception as e:
                self.log(f"Failed to convert WAD format: {str(e)}", "error")
                messagebox.showerror("Conversion Error", f"Failed to convert WAD format:\n{str(e)}", parent=self.root)

    # ----------------------------------------------------------------------
    # Textures Packing Execution
    # ----------------------------------------------------------------------

    def pack_textures(self):
        target_path = self.target_wad_path.get()
        if not target_path:
            messagebox.showwarning("No WAD Selected", "Please select or create a WAD file before packing.")
            return
            
        selected_items = self.tree_images.selection()
        
        # If nothing is selected, prompt to pack all valid files
        if not selected_items:
            valid_images = [b for b in self.detected_images if b["valid"]]
            if not valid_images:
                messagebox.showerror("No Textures to Pack", "No valid image files were found in the workspace folder.")
                return
            reply = messagebox.askyesno("Pack All Textures?", f"No specific textures selected. Do you want to pack all {len(valid_images)} valid textures?")
            if not reply:
                return
            to_pack = valid_images
        else:
            to_pack = []
            for item in selected_items:
                vals = self.tree_images.item(item, "values")
                if vals:
                    filename = vals[0]
                    for info in self.detected_images:
                        if info["filename"] == filename:
                            if info["valid"]:
                                to_pack.append(info)
                            else:
                                self.log(f"Skipping invalid file '{filename}': {info['status']}", "warning")
                            break
                            
        if not to_pack:
            self.log("No valid textures selected for packing.", "error")
            return
            
        self.log(f"Starting compilation of {len(to_pack)} textures...", "info")
        self.pack_status_lbl.config(text=f"Packing {len(to_pack)} textures...")
        self.progress["maximum"] = len(to_pack)
        self.progress["value"] = 0
        
        def progress_cb(current, total, message, level):
            self.log(message, level)
            self.progress["value"] = current
            if current > 0:
                self.pack_status_lbl.config(text=f"Packing... {current} / {total}")
            self.root.update_idletasks()
        
        success_count = backend.pack_textures_to_wad(
            target_path, to_pack, self.wad_format.get(), progress_cb
        )
        
        if success_count > 0:
            self.log(f"WAD successfully packed! Added/Updated {success_count} textures.", "success")
            messagebox.showinfo("Packing Complete", f"Successfully packed {success_count} textures to {os.path.basename(target_path)}")
        else:
            self.log("No textures were successfully compiled.", "error")
            messagebox.showwarning("Packing Failed", "No textures were compiled.")
            
        self.progress["value"] = 0
        self.pack_status_lbl.config(text=f"Done  —  {success_count} textures packed")
        self.refresh_all()

    # ----------------------------------------------------------------------
    # Treeview Column Sorting Utility
    # ----------------------------------------------------------------------

    def sort_tree(self, tree, col, reverse):
        l = [(tree.set(k, col), k) for k in tree.get_children('')]
        
        def get_sort_key(item):
            val = item[0]
            if val.isdigit():
                return int(val)
            match = re.match(r'^(\d+)x(\d+)$', val)
            if match:
                return int(match.group(1)) * int(match.group(2))
            return val.lower()
            
        l.sort(key=get_sort_key, reverse=reverse)
        
        for index, (val, k) in enumerate(l):
            tree.move(k, '', index)
            
        tree.heading(col, command=lambda: self.sort_tree(tree, col, not reverse))
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import customtkinter as ctk
import psutil
import ctypes
import threading
import time
from PIL import Image, ImageTk
import os
import sys

class ThalixGUI:
    def __init__(self):
        
        self.root = ctk.CTk()
        self.root.title("Thalix - CPU Affinity Manager")
        self.root.geometry("1000x800")
        self.root.configure(fg_color=("#0f0f0f", "#0f0f0f"))
        
    
        try:
            icon_paths = [
                os.path.join("assets", "app_icon.ico"),
                os.path.join("assets", "icon_256x256.ico"),
                os.path.join("assets", "icon_128x128.ico"),
                os.path.join("assets", "icon_64x64.ico"),
                os.path.join("assets", "icon_32x32.ico"),
                os.path.join("assets", "elden_ring_icon.jpg"),
                os.path.join("assets", "er.png")
            ]
            
            icon_loaded = False
            for icon_path in icon_paths:
                if os.path.exists(icon_path):
                    try:
                        if icon_path.endswith('.ico'):
                            self.root.iconbitmap(icon_path)
                            print(f"Window icon loaded from: {icon_path}")
                            icon_loaded = True
                            break
                        else:
                            # Convert other formats to ico temporarily
                            img = Image.open(icon_path)
                            img = img.resize((32, 32), Image.Resampling.LANCZOS)
                            temp_icon = "temp_icon.ico"
                            img.save(temp_icon)
                            self.root.iconbitmap(temp_icon)
                            os.remove(temp_icon)
                            print(f"Window icon loaded from: {icon_path}")
                            icon_loaded = True
                            break
                    except Exception as e:
                        print(f"Failed to load icon from {icon_path}: {e}")
                        continue
            
            if not icon_loaded:
                print("No suitable icon found")
                print("Available files:", [f for f in os.listdir("assets") if f.endswith(('.ico', '.png', '.jpg'))])
                
        except Exception as e:
            print(f"Could not load window icon: {e}")
            import traceback
            traceback.print_exc()
        
        # Configure grid weights
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
        
        # Initialize variables
        self.monitoring = False
        self.monitor_thread = None
        self.process_name = tk.StringVar(value="eldenring.exe")
        self.selected_cpus = []
        self.cpu_vars = []
        self.presets = {}  # Store CPU affinity presets
        self.cpu_usage_monitoring = False
        self.cpu_usage_thread = None
        self.search_var = tk.StringVar()
        self.search_var.trace('w', self.filter_processes)
        
        # Color scheme
        self.colors = {
            'primary': '#DC143C',        # Crimson Red
            'secondary': '#8B0000',      # Dark Red
            'accent': '#FF4444',         # Bright Red
            'background': '#0f0f0f',     # Very Dark Gray
            'surface': '#1a1a1a',        # Dark Charcoal
            'surface_light': '#2d2d2d',  # Medium Gray
            'text': '#FFFFFF',           # White text
            'text_secondary': '#CCCCCC', # Light Gray
            'success': '#28A745',        # Green
            'warning': '#FFC107',        # Amber
            'error': '#DC3545',          # Red
            'border': '#DC143C',         # Crimson Border
            'shadow': '#000000'          # Black Shadow
        }
        
        # Set custom theme
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        self.create_widgets()
        self.check_admin_privileges()
        
    def create_widgets(self):
        """Create and arrange all GUI widgets"""
        # Main container with background
        self.main_frame = ctk.CTkFrame(self.root, fg_color="transparent")
        self.main_frame.grid(row=0, column=0, padx=0, pady=0, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=1)
        
        # Create background
        self.create_background()
        
        # Header section
        self.create_header()
        
        # Content section
        self.create_content()
        
        # Footer section
        self.create_footer()
        
    def create_background(self):
        """Create the background frame"""
        self.bg_frame = ctk.CTkFrame(self.main_frame, fg_color=self.colors['background'])
        self.bg_frame.grid(row=0, column=0, padx=0, pady=0, sticky="nsew")
        self.bg_frame.grid_columnconfigure(0, weight=1)
        self.bg_frame.grid_rowconfigure(0, weight=1)
        
        # Try to load background image
        try:
            bg_paths = [
                os.path.join("assets", "elden_ring_bg_optimized.jpg"),
                os.path.join("assets", "elden_ring_bg.jpg"),
                os.path.join("assets", "image1.jpg"),
            ]
            
            for bg_path in bg_paths:
                if not os.path.exists(bg_path):
                    continue
                    
                try:
                    # Load and resize image
                    img = Image.open(bg_path)
                    window_width, window_height = 1000, 800
                    
                    # Calculate aspect ratio
                    img_aspect = img.width / img.height
                    window_aspect = window_width / window_height
                    
                    # Resize to cover window
                    if img_aspect > window_aspect:
                        new_height = window_height
                        new_width = int(new_height * img_aspect)
                    else:
                        new_width = window_width
                        new_height = int(new_width / img_aspect)
                    
                    img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    
                    # Darken for better text readability
                    from PIL import ImageEnhance
                    enhancer = ImageEnhance.Brightness(img)
                    img = enhancer.enhance(0.6)
                    
                    self.bg_photo = ImageTk.PhotoImage(img)
                    self.bg_label = tk.Label(self.bg_frame, image=self.bg_photo, bg=self.colors['background'])
                    self.bg_label.place(x=0, y=0, relwidth=1, relheight=1)
                    break
                except Exception:
                    continue
                    
        except Exception:
            pass
        
    def create_header(self):
        """Create the header section"""
        header_frame = ctk.CTkFrame(
            self.bg_frame, 
            fg_color=self.colors['surface'],
            corner_radius=15,
            border_width=2,
            border_color=self.colors['border']
        )
        header_frame.grid(row=0, column=0, padx=20, pady=20, sticky="ew")
        header_frame.grid_columnconfigure(1, weight=1)
        
        title_label = ctk.CTkLabel(
            header_frame, 
            text="THALIX",
            font=ctk.CTkFont(family="Arial", size=32, weight="bold"),
            text_color=self.colors['primary']
        )
        title_label.grid(row=0, column=0, padx=30, pady=20, sticky="w")
        
        # System info panel
        sys_info_frame = ctk.CTkFrame(
            header_frame,
            fg_color=self.colors['surface_light'],
            corner_radius=10
        )
        sys_info_frame.grid(row=0, column=1, padx=15, pady=20, sticky="e")
        
        # Get system info
        cpu_count = psutil.cpu_count()
        cpu_freq = psutil.cpu_freq()
        mem = psutil.virtual_memory()
        
        sys_info_text = f"{cpu_count} Cores | {cpu_freq.current:.0f}MHz | {mem.percent:.1f}% RAM"
        
        self.sys_info_label = ctk.CTkLabel(
            sys_info_frame,
            text=sys_info_text,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=self.colors['primary']
        )
        self.sys_info_label.pack(padx=15, pady=12)
        
        # Status indicator with medieval styling
        self.status_frame = ctk.CTkFrame(
            header_frame, 
            fg_color=self.colors['surface_light'],
            corner_radius=10
        )
        self.status_frame.grid(row=0, column=2, padx=30, pady=20, sticky="e")
        
        self.status_label = ctk.CTkLabel(
            self.status_frame,
            text="READY",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=self.colors['text']
        )
        self.status_label.pack(padx=20, pady=15)
        
        self.update_system_info()
        
    def create_content(self):
        """Create the main content area"""
        content_frame = ctk.CTkFrame(
            self.bg_frame, 
            fg_color=self.colors['surface'],
            corner_radius=15,
            border_width=2,
            border_color=self.colors['border']
        )
        content_frame.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        content_frame.grid_columnconfigure(0, weight=1)
        content_frame.grid_rowconfigure(0, weight=1)
        
        # Create tabbed interface
        self.tab_view = ctk.CTkTabview(content_frame, fg_color=self.colors['surface_light'])
        self.tab_view.pack(fill="both", expand=True, padx=10, pady=10)
        
        # CPU Affinity tab
        affinity_tab = self.tab_view.add("CPU Affinity")
        affinity_tab.grid_columnconfigure((0, 1), weight=1)
        affinity_tab.grid_rowconfigure(0, weight=1)
        self.create_process_panel(affinity_tab)
        self.create_cpu_panel(affinity_tab)
        
        # Memory Editor tab
        memory_tab = self.tab_view.add("Memory Editor")
        self.create_memory_editor_tab(memory_tab)
        
    def create_process_panel(self, parent):
        """Create the process management panel"""
        process_frame = ctk.CTkFrame(
            parent, 
            fg_color=self.colors['surface_light'],
            corner_radius=12,
            border_width=1,
            border_color=self.colors['border']
        )
        process_frame.grid(row=0, column=0, padx=(20, 10), pady=20, sticky="nsew")
        process_frame.grid_columnconfigure(0, weight=1)
        process_frame.grid_rowconfigure(2, weight=1)
        
        input_frame = ctk.CTkFrame(
            process_frame,
            fg_color=self.colors['background'],
            corner_radius=8
        )
        input_frame.grid(row=0, column=0, padx=15, pady=(15, 10), sticky="ew")
        input_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(
            input_frame,
            text="TARGET PROCESS",
            font=ctk.CTkFont(family="Arial", size=16, weight="bold"),
            text_color=self.colors['primary']
        ).grid(row=0, column=0, padx=20, pady=(15, 5), sticky="w")
        
        self.process_entry = ctk.CTkEntry(
            input_frame,
            textvariable=self.process_name,
            placeholder_text="Enter process name (e.g., eldenring.exe)",
            font=ctk.CTkFont(size=14),
            height=40,
            border_width=2,
            border_color=self.colors['border'],
            fg_color=self.colors['surface'],
            text_color=self.colors['text']
        )
        self.process_entry.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="ew")
        
        priority_frame = ctk.CTkFrame(
            input_frame,
            fg_color="transparent"
        )
        priority_frame.grid(row=2, column=0, padx=20, pady=(0, 15), sticky="ew")
        priority_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(
            priority_frame,
            text="Priority:",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=self.colors['text']
        ).grid(row=0, column=0, padx=(0, 10), sticky="w")
        
        self.priority_var = tk.StringVar(value="HIGH_PRIORITY_CLASS")
        priority_menu = ctk.CTkOptionMenu(
            priority_frame,
            variable=self.priority_var,
            values=["REALTIME_PRIORITY_CLASS", "HIGH_PRIORITY_CLASS", "ABOVE_NORMAL_PRIORITY_CLASS", 
                    "NORMAL_PRIORITY_CLASS", "BELOW_NORMAL_PRIORITY_CLASS"],
            font=ctk.CTkFont(size=11),
            fg_color=self.colors['surface'],
            button_color=self.colors['primary'],
            button_hover_color="#B8941F"
        )
        priority_menu.grid(row=0, column=1, sticky="ew")
        
        info_frame = ctk.CTkFrame(
            process_frame,
            fg_color=self.colors['background'],
            corner_radius=8
        )
        info_frame.grid(row=1, column=0, padx=15, pady=(0, 10), sticky="ew")
        info_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(
            info_frame,
            text="PROCESS INFORMATION",
            font=ctk.CTkFont(family="Arial", size=16, weight="bold"),
            text_color=self.colors['primary']
        ).grid(row=0, column=0, padx=20, pady=(15, 5), sticky="w")
        
        self.process_info_label = ctk.CTkLabel(
            info_frame,
            text="No process selected",
            font=ctk.CTkFont(size=12),
            text_color=self.colors['text_secondary'],
            anchor="w",
            wraplength=300
        )
        self.process_info_label.grid(row=1, column=0, padx=20, pady=(0, 15), sticky="ew")
        
        list_frame = ctk.CTkFrame(
            process_frame,
            fg_color=self.colors['background'],
            corner_radius=8
        )
        list_frame.grid(row=2, column=0, padx=15, pady=0, sticky="nsew")
        list_frame.grid_columnconfigure(0, weight=1)
        list_frame.grid_rowconfigure(2, weight=1)
        
        ctk.CTkLabel(
            list_frame,
            text="RUNNING PROCESSES",
            font=ctk.CTkFont(family="Arial", size=16, weight="bold"),
            text_color=self.colors['primary']
        ).grid(row=0, column=0, padx=20, pady=(15, 5), sticky="w")
        
        # Search bar
        self.search_entry = ctk.CTkEntry(
            list_frame,
            textvariable=self.search_var,
            placeholder_text="Search processes...",
            font=ctk.CTkFont(size=12),
            height=30,
            border_width=2,
            border_color=self.colors['border'],
            fg_color=self.colors['surface'],
            text_color=self.colors['text']
        )
        self.search_entry.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="ew")
        
        self.process_listbox = tk.Listbox(
            list_frame,
            bg=self.colors['surface'],
            fg=self.colors['text'],
            selectbackground=self.colors['primary'],
            selectforeground="#000000",
            font=("Consolas", 11),
            height=8,
            border=0,
            highlightthickness=0,
            relief="flat"
        )
        self.process_listbox.grid(row=2, column=0, padx=20, pady=(0, 10), sticky="nsew")
        self.process_listbox.bind('<<ListboxSelect>>', self.on_process_select)
        
        self.all_processes = []
        
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.process_listbox.yview)
        scrollbar.grid(row=2, column=1, sticky="ns")
        self.process_listbox.configure(yscrollcommand=scrollbar.set)
        
        refresh_btn = ctk.CTkButton(
            list_frame,
            text="REFRESH PROCESS LIST",
            command=self.refresh_process_list,
            font=ctk.CTkFont(family="Arial", size=12, weight="bold"),
            height=35,
            fg_color=self.colors['primary'],
            hover_color=self.colors['accent'],
            border_width=2,
            border_color=self.colors['border']
        )
        refresh_btn.grid(row=3, column=0, padx=20, pady=(0, 15), sticky="ew")
        
    def create_cpu_panel(self, parent):
        """Create the CPU configuration panel"""
        cpu_frame = ctk.CTkFrame(
            parent, 
            fg_color=self.colors['surface_light'],
            corner_radius=12,
            border_width=1,
            border_color=self.colors['border']
        )
        cpu_frame.grid(row=0, column=1, padx=(10, 20), pady=20, sticky="nsew")
        cpu_frame.grid_columnconfigure(0, weight=1)
        cpu_frame.grid_rowconfigure(1, weight=1)
        
        selection_frame = ctk.CTkFrame(
            cpu_frame,
            fg_color=self.colors['background'],
            corner_radius=8
        )
        selection_frame.grid(row=0, column=0, padx=15, pady=(15, 10), sticky="ew")
        selection_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(
            selection_frame,
            text="CPU CORE SELECTION",
            font=ctk.CTkFont(family="Arial", size=16, weight="bold"),
            text_color=self.colors['primary']
        ).grid(row=0, column=0, padx=20, pady=(15, 5), sticky="w")
        
        self.cpu_container = ctk.CTkScrollableFrame(
            cpu_frame, 
            height=200,
            fg_color=self.colors['background'],
            corner_radius=8
        )
        self.cpu_container.grid(row=1, column=0, padx=15, pady=0, sticky="nsew")
        self.cpu_container.grid_columnconfigure(0, weight=1)
        
        self.create_cpu_checkboxes()
        
        quick_frame = ctk.CTkFrame(
            cpu_frame,
            fg_color=self.colors['background'],
            corner_radius=8
        )
        quick_frame.grid(row=2, column=0, padx=15, pady=(10, 15), sticky="ew")
        quick_frame.grid_columnconfigure((0, 1, 2), weight=1)
        
        ctk.CTkButton(
            quick_frame,
            text="SELECT ALL",
            command=self.select_all_cpus,
            font=ctk.CTkFont(family="Arial", size=11, weight="bold"),
            height=35,
            fg_color=self.colors['success'],
            hover_color="#218838",
            border_width=1,
            border_color=self.colors['border']
        ).grid(row=0, column=0, padx=(15, 5), pady=15, sticky="ew")
        
        ctk.CTkButton(
            quick_frame,
            text="DESELECT ALL",
            command=self.deselect_all_cpus,
            font=ctk.CTkFont(family="Arial", size=11, weight="bold"),
            height=35,
            fg_color=self.colors['error'],
            hover_color="#C82333",
            border_width=1,
            border_color=self.colors['border']
        ).grid(row=0, column=1, padx=5, pady=15, sticky="ew")
        
        ctk.CTkButton(
            quick_frame,
            text="PERFORMANCE CORES",
            command=self.select_performance_cores,
            font=ctk.CTkFont(family="Arial", size=11, weight="bold"),
            height=35,
            fg_color=self.colors['warning'],
            hover_color="#E0A800",
            border_width=1,
            border_color=self.colors['border']
        ).grid(row=0, column=2, padx=(5, 15), pady=15, sticky="ew")
        
    def create_cpu_checkboxes(self):
        """Create CPU core checkboxes with usage indicators"""
        cpu_count = psutil.cpu_count()
        self.cpu_vars = []
        self.cpu_usage_labels = []
        
        for i in range(cpu_count):
            var = tk.BooleanVar(value=True)
            self.cpu_vars.append(var)
            
            cpu_frame = ctk.CTkFrame(
                self.cpu_container,
                fg_color="transparent"
            )
            cpu_frame.pack(fill="x", padx=15, pady=3)
            cpu_frame.grid_columnconfigure(1, weight=1)
            
            checkbox = ctk.CTkCheckBox(
                cpu_frame,
                text=f"Core {i}",
                variable=var,
                font=ctk.CTkFont(family="Arial", size=13, weight="bold"),
                text_color=self.colors['text'],
                fg_color=self.colors['primary'],
                hover_color=self.colors['accent'],
                border_width=2,
                border_color=self.colors['border']
            )
            checkbox.grid(row=0, column=0, sticky="w")
            
            usage_label = ctk.CTkLabel(
                cpu_frame,
                text="0%",
                font=ctk.CTkFont(size=11),
                text_color=self.colors['text_secondary'],
                width=40
            )
            usage_label.grid(row=0, column=1, sticky="e", padx=(10, 0))
            self.cpu_usage_labels.append(usage_label)
        
        self.start_cpu_usage_monitoring()
            
    def create_footer(self):
        """Create the footer with action buttons"""
        footer_frame = ctk.CTkFrame(
            self.bg_frame, 
            fg_color=self.colors['surface'],
            corner_radius=15,
            border_width=2,
            border_color=self.colors['border']
        )
        footer_frame.grid(row=2, column=0, padx=20, pady=(10, 20), sticky="ew")
        footer_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)
        footer_frame.grid_rowconfigure((0, 1), weight=1)
        
        self.apply_button = ctk.CTkButton(
            footer_frame,
            text="APPLY AFFINITY",
            command=self.apply_affinity_and_priority,
            font=ctk.CTkFont(family="Arial", size=15, weight="bold"),
            height=50,
            fg_color=self.colors['success'],
            hover_color="#218838",
            border_width=3,
            border_color=self.colors['border'],
            corner_radius=12
        )
        self.apply_button.grid(row=0, column=0, padx=(25, 8), pady=(25, 8), sticky="ew")
        
        self.monitor_button = ctk.CTkButton(
            footer_frame,
            text="START MONITORING",
            command=self.toggle_monitoring,
            font=ctk.CTkFont(family="Arial", size=15, weight="bold"),
            height=50,
            fg_color=self.colors['warning'],
            hover_color="#E0A800",
            border_width=3,
            border_color=self.colors['border'],
            corner_radius=12
        )
        self.monitor_button.grid(row=0, column=1, padx=8, pady=(25, 8), sticky="ew")
        
        save_preset_button = ctk.CTkButton(
            footer_frame,
            text="SAVE PRESET",
            command=self.save_preset,
            font=ctk.CTkFont(family="Arial", size=15, weight="bold"),
            height=50,
            fg_color=self.colors['primary'],
            hover_color=self.colors['accent'],
            border_width=3,
            border_color=self.colors['border'],
            corner_radius=12
        )
        save_preset_button.grid(row=0, column=2, padx=8, pady=(25, 8), sticky="ew")
        
        settings_button = ctk.CTkButton(
            footer_frame,
            text="SETTINGS",
            command=self.open_settings,
            font=ctk.CTkFont(family="Arial", size=15, weight="bold"),
            height=50,
            fg_color=self.colors['secondary'],
            hover_color="#A00000",
            border_width=3,
            border_color=self.colors['border'],
            corner_radius=12
        )
        settings_button.grid(row=0, column=3, padx=(8, 25), pady=(25, 8), sticky="ew")
        
        load_preset_button = ctk.CTkButton(
            footer_frame,
            text="LOAD PRESET",
            command=self.load_preset,
            font=ctk.CTkFont(family="Arial", size=13, weight="bold"),
            height=40,
            fg_color=self.colors['surface_light'],
            hover_color=self.colors['surface'],
            border_width=2,
            border_color=self.colors['border'],
            corner_radius=10
        )
        load_preset_button.grid(row=1, column=0, columnspan=2, padx=(25, 8), pady=(8, 25), sticky="ew")
        
        stats_button = ctk.CTkButton(
            footer_frame,
            text="PERFORMANCE STATS",
            command=self.show_performance_stats,
            font=ctk.CTkFont(family="Arial", size=13, weight="bold"),
            height=40,
            fg_color=self.colors['surface_light'],
            hover_color=self.colors['surface'],
            border_width=2,
            border_color=self.colors['border'],
            corner_radius=10
        )
        stats_button.grid(row=1, column=2, columnspan=2, padx=(8, 25), pady=(8, 25), sticky="ew")
        
    def check_admin_privileges(self):
        """Check if running as administrator"""
        try:
            is_admin = ctypes.windll.shell32.IsUserAnAdmin()
            if not is_admin:
                self.update_status("Run as Administrator for full functionality", self.colors['warning'])
                self.apply_button.configure(state="disabled")
                self.monitor_button.configure(state="disabled")
            else:
                self.update_status("Administrator privileges detected", self.colors['success'])
        except:
            self.update_status("Could not check admin privileges", self.colors['error'])
            
    def update_status(self, message, color=None):
        """Update the status label"""
        if color:
            self.status_label.configure(text=message, text_color=color)
        else:
            self.status_label.configure(text=message)
            
    def refresh_process_list(self):
        """Refresh the list of running processes"""
        try:
            self.process_listbox.delete(0, tk.END)
            self.all_processes = []
            
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if proc.info['name']:
                        self.all_processes.append(f"{proc.info['name']} (PID: {proc.info['pid']})")
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
                    
            self.all_processes.sort()
            
            # Apply current filter
            search_term = self.search_var.get().lower()
            for proc in self.all_processes:
                if not search_term or search_term in proc.lower():
                    self.process_listbox.insert(tk.END, proc)
                
            self.update_status(f"Found {len(self.all_processes)} processes", self.colors['text'])
            
        except Exception as e:
            self.update_status(f"Error refreshing processes: {str(e)}", self.colors['error'])
            
    def on_process_select(self, event):
        """Handle process selection from list"""
        selection = self.process_listbox.curselection()
        if selection:
            process_text = self.process_listbox.get(selection[0])
            # Extract process name (before the PID part)
            process_name = process_text.split(' (PID:')[0]
            self.process_name.set(process_name)
            self.update_process_info(process_name)
            
    def update_process_info(self, process_name):
        """Update process information display"""
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cpu_affinity']):
                if proc.info['name'] and proc.info['name'].lower() == process_name.lower():
                    try:
                        p = psutil.Process(proc.info['pid'])
                        affinity = p.cpu_affinity()
                        info_text = f"Process: {process_name}\nPID: {proc.info['pid']}\nCurrent Affinity: {affinity}"
                        self.process_info_label.configure(text=info_text)
                        return
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
                        
            self.process_info_label.configure(text=f"Process: {process_name}\nStatus: Not found or access denied")
            
        except Exception as e:
            self.process_info_label.configure(text=f"Error: {str(e)}")
            
    def get_selected_cpus(self):
        """Get list of selected CPU cores"""
        return [i for i, var in enumerate(self.cpu_vars) if var.get()]
        
    def select_all_cpus(self):
        """Select all CPU cores"""
        for var in self.cpu_vars:
            var.set(True)
        self.update_status("All CPU cores selected", self.colors['success'])
        
    def deselect_all_cpus(self):
        """Deselect all CPU cores"""
        for var in self.cpu_vars:
            var.set(False)
        self.update_status("All CPU cores deselected", self.colors['warning'])
        
    def select_performance_cores(self):
        """Select performance cores (even-numbered cores)"""
        for i, var in enumerate(self.cpu_vars):
            var.set(i % 2 == 0)
        self.update_status("Performance cores selected", self.colors['success'])
        
    def apply_affinity(self):
        """Apply CPU affinity to the selected process"""
        process_name = self.process_name.get().strip()
        if not process_name:
            self.update_status("Please enter a process name", self.colors['error'])
            return
            
        selected_cpus = self.get_selected_cpus()
        if not selected_cpus:
            self.update_status("Please select at least one CPU core", self.colors['error'])
            return
            
        try:
            # Find the process
            target_process = None
            for proc in psutil.process_iter(['pid', 'name']):
                if proc.info['name'] and proc.info['name'].lower() == process_name.lower():
                    target_process = psutil.Process(proc.info['pid'])
                    break
                    
            if not target_process:
                self.update_status(f"Process '{process_name}' not found", self.colors['error'])
                return
                
            # Apply affinity
            target_process.cpu_affinity(selected_cpus)
            new_affinity = target_process.cpu_affinity()
            
            self.update_status(
                f"Affinity set for '{process_name}': {new_affinity}", 
                self.colors['success']
            )
            
        except psutil.AccessDenied:
            self.update_status("Access denied. Run as Administrator", self.colors['error'])
        except psutil.NoSuchProcess:
            self.update_status("Process not found or terminated", self.colors['error'])
        except Exception as e:
            self.update_status(f"Error: {str(e)}", self.colors['error'])
            
    def toggle_monitoring(self):
        """Toggle process monitoring"""
        if not self.monitoring:
            process_name = self.process_name.get().strip()
            if not process_name:
                self.update_status("Please enter a process name first", self.colors['error'])
                return
                
            self.monitoring = True
            self.monitor_button.configure(text="STOP MONITORING")
            self.apply_button.configure(state="disabled")
            
            # Start monitoring thread
            self.monitor_thread = threading.Thread(target=self.monitor_process, daemon=True)
            self.monitor_thread.start()
            
            self.update_status(f"Monitoring for '{process_name}'...", self.colors['warning'])
        else:
            self.monitoring = False
            self.monitor_button.configure(text="START MONITORING")
            self.apply_button.configure(state="normal")
            self.update_status("Monitoring stopped", self.colors['text'])
            
    def monitor_process(self):
        """Monitor for the target process and apply affinity when found"""
        process_name = self.process_name.get().strip()
        
        while self.monitoring:
            try:
                # Check if process exists
                found = False
                for proc in psutil.process_iter(['pid', 'name']):
                    if proc.info['name'] and proc.info['name'].lower() == process_name.lower():
                        found = True
                        break
                        
                if found:
                    # Apply affinity
                    self.root.after(0, self.apply_affinity)
                    self.root.after(0, lambda: self.toggle_monitoring())
                    break
                    
            except Exception as e:
                self.root.after(0, lambda: self.update_status(f"Monitor error: {str(e)}", self.colors['error']))
                
            time.sleep(2)  # Check every 2 seconds
            
    def filter_processes(self, *args):
        """Filter process list based on search query"""
        search_term = self.search_var.get().lower()
        self.process_listbox.delete(0, tk.END)
        
        for proc in self.all_processes:
            if search_term in proc.lower():
                self.process_listbox.insert(tk.END, proc)
    
    def update_system_info(self):
        """Update system information display"""
        try:
            cpu_freq = psutil.cpu_freq()
            mem = psutil.virtual_memory()
            cpu_count = psutil.cpu_count()
            
            sys_info_text = f"{cpu_count} Cores | {cpu_freq.current:.0f}MHz | {mem.percent:.1f}% RAM"
            self.sys_info_label.configure(text=sys_info_text)
        except:
            pass
        
        # Update every 2 seconds
        self.root.after(2000, self.update_system_info)
    
    def start_cpu_usage_monitoring(self):
        """Start monitoring CPU usage per core"""
        self.cpu_usage_monitoring = True
        self.cpu_usage_thread = threading.Thread(target=self.monitor_cpu_usage, daemon=True)
        self.cpu_usage_thread.start()
    
    def monitor_cpu_usage(self):
        """Monitor CPU usage for each core"""
        while self.cpu_usage_monitoring:
            try:
                cpu_percents = psutil.cpu_percent(interval=1, percpu=True)
                for i, percent in enumerate(cpu_percents):
                    if i < len(self.cpu_usage_labels):
                        color = self.colors['success'] if percent < 50 else (
                            self.colors['warning'] if percent < 80 else self.colors['error']
                        )
                        self.root.after(0, lambda idx=i, p=percent, c=color: 
                            self.cpu_usage_labels[idx].configure(
                                text=f"{p:.0f}%",
                                text_color=c
                            ))
            except:
                pass
            time.sleep(1)
    
    def apply_affinity_and_priority(self):
        """Apply both CPU affinity and process priority"""
        self.apply_affinity()
        self.set_process_priority()
    
    def set_process_priority(self):
        """Set process priority"""
        process_name = self.process_name.get().strip()
        if not process_name:
            return
        
        priority_map = {
            "REALTIME_PRIORITY_CLASS": psutil.REALTIME_PRIORITY_CLASS,
            "HIGH_PRIORITY_CLASS": psutil.HIGH_PRIORITY_CLASS,
            "ABOVE_NORMAL_PRIORITY_CLASS": psutil.ABOVE_NORMAL_PRIORITY_CLASS,
            "NORMAL_PRIORITY_CLASS": psutil.NORMAL_PRIORITY_CLASS,
            "BELOW_NORMAL_PRIORITY_CLASS": psutil.BELOW_NORMAL_PRIORITY_CLASS
        }
        
        try:
            target_process = None
            for proc in psutil.process_iter(['pid', 'name']):
                if proc.info['name'] and proc.info['name'].lower() == process_name.lower():
                    target_process = psutil.Process(proc.info['pid'])
                    break
            
            if target_process:
                priority = priority_map[self.priority_var.get()]
                target_process.nice(priority)
                self.update_status(
                    f"Priority set to {self.priority_var.get()}",
                    self.colors['success']
                )
        except Exception as e:
            self.update_status(f"Priority error: {str(e)}", self.colors['error'])
    
    def save_preset(self):
        """Save current CPU affinity configuration as a preset"""
        selected_cpus = self.get_selected_cpus()
        if not selected_cpus:
            messagebox.showwarning("No CPUs Selected", "Please select at least one CPU core")
            return
        
        # Create preset dialog
        dialog = ctk.CTkInputDialog(
            text="Enter preset name:",
            title="Save Preset"
        )
        preset_name = dialog.get_input()
        
        if preset_name:
            self.presets[preset_name] = {
                'cpus': selected_cpus,
                'priority': self.priority_var.get()
            }
            self.update_status(f"Preset '{preset_name}' saved!", self.colors['success'])
            messagebox.showinfo("Success", f"Preset '{preset_name}' saved successfully!")
    
    def load_preset(self):
        """Load a saved CPU affinity preset"""
        if not self.presets:
            messagebox.showinfo("No Presets", "No presets available. Save a preset first!")
            return
        
        # Create selection dialog
        preset_window = ctk.CTkToplevel(self.root)
        preset_window.title("Load Preset")
        preset_window.geometry("400x500")
        preset_window.configure(fg_color=self.colors['background'])
        preset_window.transient(self.root)
        preset_window.grab_set()
        
        # Center window
        preset_window.geometry("+%d+%d" % (
            self.root.winfo_rootx() + 300,
            self.root.winfo_rooty() + 150
        ))
        
        main_frame = ctk.CTkFrame(
            preset_window,
            fg_color=self.colors['surface'],
            corner_radius=15,
            border_width=2,
            border_color=self.colors['border']
        )
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(
            main_frame,
            text="LOAD PRESET",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=self.colors['primary']
        ).pack(pady=20)
        
        # Preset list
        for preset_name, preset_data in self.presets.items():
            preset_frame = ctk.CTkFrame(
                main_frame,
                fg_color=self.colors['surface_light'],
                corner_radius=10
            )
            preset_frame.pack(fill="x", padx=20, pady=10)
            
            info_text = f"{preset_name}\nCPUs: {preset_data['cpus']}\nPriority: {preset_data['priority']}"
            
            ctk.CTkLabel(
                preset_frame,
                text=info_text,
                font=ctk.CTkFont(size=12),
                text_color=self.colors['text'],
                justify="left"
            ).pack(side="left", padx=15, pady=10)
            
            ctk.CTkButton(
                preset_frame,
                text="Load",
                command=lambda p=preset_data: self.apply_preset(p, preset_window),
                width=80,
                fg_color=self.colors['primary'],
                hover_color="#B8941F"
            ).pack(side="right", padx=15, pady=10)
        
        ctk.CTkButton(
            main_frame,
            text="CLOSE",
            command=preset_window.destroy,
            fg_color=self.colors['secondary'],
            hover_color="#A0522D"
        ).pack(pady=20)
    
    def apply_preset(self, preset_data, window):
        """Apply a preset configuration"""
        # Set CPU checkboxes
        for i, var in enumerate(self.cpu_vars):
            var.set(i in preset_data['cpus'])
        
        # Set priority
        self.priority_var.set(preset_data['priority'])
        
        self.update_status("Preset loaded!", self.colors['success'])
        window.destroy()
    
    def show_performance_stats(self):
        """Show performance statistics window"""
        stats_window = ctk.CTkToplevel(self.root)
        stats_window.title("Performance Statistics")
        stats_window.geometry("600x700")
        stats_window.configure(fg_color=self.colors['background'])
        stats_window.transient(self.root)
        
        # Center window
        stats_window.geometry("+%d+%d" % (
            self.root.winfo_rootx() + 200,
            self.root.winfo_rooty() + 50
        ))
        
        main_frame = ctk.CTkFrame(
            stats_window,
            fg_color=self.colors['surface'],
            corner_radius=15,
            border_width=2,
            border_color=self.colors['border']
        )
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(
            main_frame,
            text="SYSTEM PERFORMANCE",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=self.colors['primary']
        ).pack(pady=20)
        
        # Create stats display
        stats_frame = ctk.CTkScrollableFrame(
            main_frame,
            fg_color=self.colors['surface_light'],
            corner_radius=10
        )
        stats_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Get system stats
        cpu_percent = psutil.cpu_percent(interval=1, percpu=True)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        stats_text = f"""
CPU STATISTICS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total Cores: {psutil.cpu_count()}
Physical Cores: {psutil.cpu_count(logical=False)}
CPU Frequency: {psutil.cpu_freq().current:.2f} MHz
Overall Usage: {psutil.cpu_percent()}%

Per-Core Usage:
"""
        for i, percent in enumerate(cpu_percent):
            stats_text += f"  Core {i}: {percent}%\n"
        
        stats_text += f"""
MEMORY STATISTICS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total: {mem.total / (1024**3):.2f} GB
Available: {mem.available / (1024**3):.2f} GB
Used: {mem.used / (1024**3):.2f} GB
Percentage: {mem.percent}%

DISK STATISTICS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total: {disk.total / (1024**3):.2f} GB
Used: {disk.used / (1024**3):.2f} GB
Free: {disk.free / (1024**3):.2f} GB
Percentage: {disk.percent}%
"""
        
        stats_label = ctk.CTkLabel(
            stats_frame,
            text=stats_text,
            font=ctk.CTkFont(family="Consolas", size=12),
            text_color=self.colors['text'],
            justify="left"
        )
        stats_label.pack(padx=20, pady=20, anchor="w")
        
        ctk.CTkButton(
            main_frame,
            text="CLOSE",
            command=stats_window.destroy,
            fg_color=self.colors['primary'],
            hover_color="#B8941F"
        ).pack(pady=20)
    
    def open_settings(self):
        """Open settings dialog with Elden Ring styling"""
        settings_window = ctk.CTkToplevel(self.root)
        settings_window.title("Settings")
        settings_window.geometry("500x400")
        settings_window.configure(fg_color=self.colors['background'])
        settings_window.transient(self.root)
        settings_window.grab_set()
        
        # Center the window
        settings_window.geometry("+%d+%d" % (
            self.root.winfo_rootx() + 50,
            self.root.winfo_rooty() + 50
        ))
        
        # Settings content with Elden Ring styling
        main_frame = ctk.CTkFrame(
            settings_window,
            fg_color=self.colors['surface'],
            corner_radius=15,
            border_width=2,
            border_color=self.colors['border']
        )
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(
            main_frame,
            text="THALIX SETTINGS",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=self.colors['primary']
        ).pack(pady=30)
        
        # Theme selection
        theme_frame = ctk.CTkFrame(
            main_frame,
            fg_color=self.colors['surface_light'],
            corner_radius=10
        )
        theme_frame.pack(fill="x", padx=30, pady=15)
        
        ctk.CTkLabel(
            theme_frame, 
            text="THEME",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=self.colors['primary']
        ).pack(pady=15)
        
        theme_var = tk.StringVar(value="dark")
        ctk.CTkRadioButton(
            theme_frame, 
            text="Dark", 
            variable=theme_var, 
            value="dark",
            font=ctk.CTkFont(size=14),
            text_color=self.colors['text']
        ).pack(pady=5)
        ctk.CTkRadioButton(
            theme_frame, 
            text="Light", 
            variable=theme_var, 
            value="light",
            font=ctk.CTkFont(size=14),
            text_color=self.colors['text']
        ).pack(pady=5)
        
        # Auto-refresh setting
        refresh_frame = ctk.CTkFrame(
            main_frame,
            fg_color=self.colors['surface_light'],
            corner_radius=10
        )
        refresh_frame.pack(fill="x", padx=30, pady=15)
        
        auto_refresh_var = tk.BooleanVar()
        ctk.CTkCheckBox(
            refresh_frame, 
            text="Auto-refresh process list every 30 seconds",
            variable=auto_refresh_var,
            font=ctk.CTkFont(size=14),
            text_color=self.colors['text']
        ).pack(pady=15)
        
        # Close button with Elden Ring styling
        ctk.CTkButton(
            main_frame,
            text="CLOSE",
            command=settings_window.destroy,
            width=120,
            height=40,
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color=self.colors['primary'],
            hover_color="#B8941F",
            border_width=2,
            border_color=self.colors['border']
        ).pack(pady=30)
        
    def create_memory_editor_tab(self, parent):
        """Create the memory editor tab"""
        import sys
        import os
        sys.path.insert(0, os.path.dirname(__file__))
        from gui.memory_editor_tab import MemoryEditorTab
        self.memory_editor = MemoryEditorTab(parent, self.colors)
    
    def open_memory_editor(self):
        """Open the memory editor window"""
        messagebox.showinfo("Coming Soon", "Memory editor feature is currently under development.")
    
    def run(self):
        """Start the application"""
        # Load initial process list
        self.refresh_process_list()
        
        # Start the main loop
        self.root.mainloop()

def main():
    """Main entry point"""
    app = ThalixGUI()
    app.run()

if __name__ == "__main__":
    main()
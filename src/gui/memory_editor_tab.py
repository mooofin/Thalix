"""
Memory Editor Tab - Integrated into Thalix GUI.
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import customtkinter as ctk
import threading
import logging
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core import (
    ProcessManager, MemoryManager, MemoryRegionManager,
    ScanEngine, AOBScanner, AddressTableManager, FreezerManager,
    DataType, ComparisonType, ValueParser, ValuePacker, ValueFormatter
)

logger = logging.getLogger(__name__)


class MemoryEditorTab(ctk.CTkFrame):
    """Memory editor integrated into Thalix."""
    
    def __init__(self, parent, colors):
        super().__init__(parent, fg_color="transparent")
        self.colors = colors
        
        # Core managers
        self.process_manager = ProcessManager()
        self.process_handle = None
        self.memory_manager = None
        self.region_manager = None
        self.scan_engine = None
        self.aob_scanner = None
        self.address_table_manager = None
        self.freezer_manager = None
        
        # Scan state
        self.current_results = None
        self.scan_thread = None
        
        self.pack(fill="both", expand=True)
        self.create_widgets()
    
    def create_widgets(self):
        """Create memory editor widgets."""
        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        
        # Top panel - Process selection
        self.create_process_panel()
        
        # Bottom panel - Scanner and Address Table
        bottom_frame = ctk.CTkFrame(self, fg_color="transparent")
        bottom_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        bottom_frame.grid_columnconfigure((0, 1), weight=1)
        bottom_frame.grid_rowconfigure(0, weight=1)
        
        self.create_scanner_panel(bottom_frame)
        self.create_address_table_panel(bottom_frame)
    
    def create_process_panel(self):
        """Create process selection panel."""
        process_frame = ctk.CTkFrame(self, fg_color=self.colors['surface_light'], corner_radius=10)
        process_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        process_frame.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(
            process_frame,
            text="Process:",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=self.colors['text']
        ).grid(row=0, column=0, padx=10, pady=10)
        
        self.process_combo = ctk.CTkComboBox(
            process_frame,
            values=["Select a process..."],
            command=self.on_process_select,
            width=300,
            fg_color=self.colors['surface'],
            button_color=self.colors['primary']
        )
        self.process_combo.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        
        ctk.CTkButton(
            process_frame,
            text="Refresh",
            command=self.refresh_processes,
            width=100,
            fg_color=self.colors['primary'],
            hover_color=self.colors['accent']
        ).grid(row=0, column=2, padx=10, pady=10)
        
        ctk.CTkButton(
            process_frame,
            text="Attach",
            command=self.attach_process,
            width=100,
            fg_color=self.colors['success'],
            hover_color="#218838"
        ).grid(row=0, column=3, padx=10, pady=10)
        
        self.status_label = ctk.CTkLabel(
            process_frame,
            text="Not attached",
            font=ctk.CTkFont(size=12),
            text_color=self.colors['text_secondary']
        )
        self.status_label.grid(row=0, column=4, padx=10, pady=10)
        
        # Initial refresh
        self.refresh_processes()
    
    def create_scanner_panel(self, parent):
        """Create scanner panel."""
        scanner_frame = ctk.CTkFrame(parent, fg_color=self.colors['surface_light'], corner_radius=10)
        scanner_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        scanner_frame.grid_columnconfigure(0, weight=1)
        scanner_frame.grid_rowconfigure(2, weight=1)
        
        # Title
        ctk.CTkLabel(
            scanner_frame,
            text="MEMORY SCANNER",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=self.colors['primary']
        ).grid(row=0, column=0, pady=10)
        
        # Controls
        controls = ctk.CTkFrame(scanner_frame, fg_color="transparent")
        controls.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
        controls.grid_columnconfigure(1, weight=1)
        
        # Scan type
        ctk.CTkLabel(controls, text="Type:", text_color=self.colors['text']).grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.scan_type_var = tk.StringVar(value="Exact Value")
        ctk.CTkComboBox(
            controls,
            variable=self.scan_type_var,
            values=["Exact Value", "Increased", "Decreased", "Changed", "Unchanged"],
            width=150,
            fg_color=self.colors['surface'],
            button_color=self.colors['primary']
        ).grid(row=0, column=1, padx=5, pady=2, sticky="w")
        
        # Data type
        ctk.CTkLabel(controls, text="Data Type:", text_color=self.colors['text']).grid(row=1, column=0, padx=5, pady=2, sticky="w")
        self.data_type_var = tk.StringVar(value="INT32")
        ctk.CTkComboBox(
            controls,
            variable=self.data_type_var,
            values=[dt.name for dt in DataType],
            width=150,
            fg_color=self.colors['surface'],
            button_color=self.colors['primary']
        ).grid(row=1, column=1, padx=5, pady=2, sticky="w")
        
        # Value
        ctk.CTkLabel(controls, text="Value:", text_color=self.colors['text']).grid(row=2, column=0, padx=5, pady=2, sticky="w")
        self.value_var = tk.StringVar()
        ctk.CTkEntry(
            controls,
            textvariable=self.value_var,
            width=150,
            fg_color=self.colors['surface']
        ).grid(row=2, column=1, padx=5, pady=2, sticky="w")
        
        # Buttons
        btn_frame = ctk.CTkFrame(controls, fg_color="transparent")
        btn_frame.grid(row=3, column=0, columnspan=2, pady=10)
        
        self.first_scan_btn = ctk.CTkButton(
            btn_frame,
            text="First Scan",
            command=self.first_scan,
            state="disabled",
            width=100,
            fg_color=self.colors['primary']
        )
        self.first_scan_btn.pack(side="left", padx=5)
        
        self.next_scan_btn = ctk.CTkButton(
            btn_frame,
            text="Next Scan",
            command=self.next_scan,
            state="disabled",
            width=100,
            fg_color=self.colors['warning']
        )
        self.next_scan_btn.pack(side="left", padx=5)
        
        self.new_scan_btn = ctk.CTkButton(
            btn_frame,
            text="New Scan",
            command=self.new_scan,
            state="disabled",
            width=100,
            fg_color=self.colors['secondary']
        )
        self.new_scan_btn.pack(side="left", padx=5)
        
        # Progress
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ctk.CTkProgressBar(controls, variable=self.progress_var, width=300)
        self.progress_bar.grid(row=4, column=0, columnspan=2, padx=5, pady=5, sticky="ew")
        self.progress_bar.set(0)
        
        # Results
        results_frame = ctk.CTkFrame(scanner_frame, fg_color=self.colors['background'])
        results_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=10)
        
        # Create treeview for results
        self.results_tree = ttk.Treeview(
            results_frame,
            columns=("Address", "Value"),
            show="headings",
            height=10
        )
        self.results_tree.heading("Address", text="Address")
        self.results_tree.heading("Value", text="Value")
        self.results_tree.pack(side="left", fill="both", expand=True)
        
        scrollbar = ttk.Scrollbar(results_frame, orient="vertical", command=self.results_tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.results_tree.configure(yscrollcommand=scrollbar.set)
        
        # Add to table button
        ctk.CTkButton(
            scanner_frame,
            text="Add Selected to Address Table",
            command=self.add_to_table,
            fg_color=self.colors['success']
        ).grid(row=3, column=0, pady=10)
    
    def create_address_table_panel(self, parent):
        """Create address table panel."""
        table_frame = ctk.CTkFrame(parent, fg_color=self.colors['surface_light'], corner_radius=10)
        table_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        table_frame.grid_columnconfigure(0, weight=1)
        table_frame.grid_rowconfigure(2, weight=1)
        
        # Title
        ctk.CTkLabel(
            table_frame,
            text="ADDRESS TABLE",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=self.colors['primary']
        ).grid(row=0, column=0, pady=10)
        
        # Controls
        controls = ctk.CTkFrame(table_frame, fg_color="transparent")
        controls.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
        
        ctk.CTkButton(
            controls,
            text="Add Address",
            command=self.add_address_manual,
            state="disabled",
            width=100,
            fg_color=self.colors['primary']
        ).pack(side="left", padx=5)
        self.add_addr_btn = controls.winfo_children()[-1]
        
        ctk.CTkButton(
            controls,
            text="Remove",
            command=self.remove_address,
            state="disabled",
            width=100,
            fg_color=self.colors['error']
        ).pack(side="left", padx=5)
        self.remove_addr_btn = controls.winfo_children()[-1]
        
        ctk.CTkButton(
            controls,
            text="Refresh",
            command=self.refresh_table,
            state="disabled",
            width=100,
            fg_color=self.colors['warning']
        ).pack(side="left", padx=5)
        self.refresh_table_btn = controls.winfo_children()[-1]
        
        # Address table
        table_container = ctk.CTkFrame(table_frame, fg_color=self.colors['background'])
        table_container.grid(row=2, column=0, sticky="nsew", padx=10, pady=10)
        
        self.address_tree = ttk.Treeview(
            table_container,
            columns=("Address", "Type", "Value", "Frozen", "Description"),
            show="headings",
            height=10
        )
        self.address_tree.heading("Address", text="Address")
        self.address_tree.heading("Type", text="Type")
        self.address_tree.heading("Value", text="Value")
        self.address_tree.heading("Frozen", text="Frozen")
        self.address_tree.heading("Description", text="Description")
        
        self.address_tree.column("Address", width=120)
        self.address_tree.column("Type", width=80)
        self.address_tree.column("Value", width=100)
        self.address_tree.column("Frozen", width=60)
        self.address_tree.column("Description", width=150)
        
        self.address_tree.pack(side="left", fill="both", expand=True)
        
        scrollbar = ttk.Scrollbar(table_container, orient="vertical", command=self.address_tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.address_tree.configure(yscrollcommand=scrollbar.set)
        
        # Double-click to edit
        self.address_tree.bind("<Double-1>", lambda e: self.edit_value())
        
        # Context menu
        self.context_menu = tk.Menu(self.address_tree, tearoff=0)
        self.context_menu.add_command(label="Edit Value", command=self.edit_value)
        self.context_menu.add_command(label="Toggle Freeze", command=self.toggle_freeze)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Remove", command=self.remove_address)
        
        self.address_tree.bind("<Button-3>", self.show_context_menu)
        
        # Store mapping
        self.item_to_id = {}
    
    def refresh_processes(self):
        """Refresh process list."""
        try:
            processes = self.process_manager.enumerate_processes()
            process_names = [f"{p.name} (PID: {p.pid})" for p in processes]
            process_names.sort()
            self.process_combo.configure(values=process_names)
            self.all_processes = processes
        except Exception as e:
            logger.error(f"Failed to refresh processes: {e}")
    
    def on_process_select(self, choice):
        """Handle process selection."""
        pass  # Just update the combo
    
    def attach_process(self):
        """Attach to selected process."""
        selection = self.process_combo.get()
        if not selection or selection == "Select a process...":
            messagebox.showerror("Error", "Please select a process")
            return
        
        try:
            # Extract PID
            pid = int(selection.split("PID: ")[1].rstrip(")"))
            
            # Attach
            self.process_handle = self.process_manager.open_process(pid)
            self.memory_manager = MemoryManager(self.process_handle)
            self.region_manager = MemoryRegionManager(self.memory_manager)
            self.scan_engine = ScanEngine(self.memory_manager, self.region_manager)
            self.aob_scanner = AOBScanner(self.memory_manager)
            self.address_table_manager = AddressTableManager(self.memory_manager)
            self.freezer_manager = FreezerManager(self.memory_manager)
            self.freezer_manager.start()
            
            # Enable controls
            self.first_scan_btn.configure(state="normal")
            self.new_scan_btn.configure(state="normal")
            self.add_addr_btn.configure(state="normal")
            self.remove_addr_btn.configure(state="normal")
            self.refresh_table_btn.configure(state="normal")
            
            self.status_label.configure(text=f"Attached to PID {pid}", text_color=self.colors['success'])
            messagebox.showinfo("Success", f"Attached to process (PID: {pid})")
            
        except Exception as e:
            logger.error(f"Failed to attach: {e}")
            messagebox.showerror("Error", f"Failed to attach to process:\n{e}")
    
    def first_scan(self):
        """Perform first scan."""
        if self.scan_type_var.get() != "Exact Value":
            messagebox.showerror("Error", "First scan must be 'Exact Value'")
            return
        
        value_str = self.value_var.get().strip()
        if not value_str:
            messagebox.showerror("Error", "Please enter a value")
            return
        
        try:
            data_type = DataType[self.data_type_var.get()]
            value = ValueParser.parse_value(value_str, data_type)
        except Exception as e:
            messagebox.showerror("Error", f"Invalid value: {e}")
            return
        
        # Show scanning message
        self.status_label.configure(
            text=f"Scanning... This may take 30-60 seconds",
            text_color=self.colors['warning']
        )
        
        # Disable controls
        self.first_scan_btn.configure(state="disabled")
        self.next_scan_btn.configure(state="disabled")
        self.new_scan_btn.configure(state="disabled")
        
        # Start scan
        self.scan_thread = threading.Thread(target=self._perform_first_scan, args=(value, data_type), daemon=True)
        self.scan_thread.start()
        
        logger.info(f"Started scan thread for value {value}")
    
    def _perform_first_scan(self, value, data_type):
        """Perform first scan in background."""
        try:
            logger.info(f"Starting first scan for value {value} of type {data_type.name}")
            
            def progress_callback(scan_progress):
                # scan_progress is a ScanProgress object
                try:
                    if scan_progress.total_regions > 0:
                        progress = scan_progress.regions_scanned / scan_progress.total_regions
                        # Use a copy of progress to avoid closure issues
                        self.after(0, lambda p=progress: self.progress_var.set(p))
                        logger.debug(f"Scan progress: {scan_progress.regions_scanned}/{scan_progress.total_regions} regions")
                except Exception as e:
                    logger.error(f"Progress callback error: {e}")
            
            # Set progress callback on scan engine
            self.scan_engine.set_progress_callback(progress_callback)
            
            logger.info("Calling scan_exact_value...")
            results = self.scan_engine.scan_exact_value(value, data_type)
            logger.info(f"Scan complete! Found {len(results.addresses)} results")
            
            self.current_results = results
            self.after(0, self._update_results, results)
        except Exception as e:
            logger.error(f"Scan error: {e}")
            import traceback
            traceback.print_exc()
            self.after(0, lambda e=e: messagebox.showerror("Error", f"Scan failed: {e}"))
            self.after(0, self._enable_controls)
    
    def next_scan(self):
        """Perform next scan."""
        if not self.current_results:
            return
        
        scan_type = self.scan_type_var.get()
        comparison_map = {
            "Exact Value": ComparisonType.EXACT,
            "Increased": ComparisonType.INCREASED,
            "Decreased": ComparisonType.DECREASED,
            "Changed": ComparisonType.CHANGED,
            "Unchanged": ComparisonType.UNCHANGED
        }
        comparison = comparison_map[scan_type]
        
        value = None
        if comparison == ComparisonType.EXACT:
            value_str = self.value_var.get().strip()
            if not value_str:
                messagebox.showerror("Error", "Please enter a value")
                return
            try:
                data_type = DataType[self.data_type_var.get()]
                value = ValueParser.parse_value(value_str, data_type)
            except Exception as e:
                messagebox.showerror("Error", f"Invalid value: {e}")
                return
        
        # Disable controls
        self.first_scan_btn.configure(state="disabled")
        self.next_scan_btn.configure(state="disabled")
        self.new_scan_btn.configure(state="disabled")
        
        # Start scan
        self.scan_thread = threading.Thread(target=self._perform_next_scan, args=(comparison, value))
        self.scan_thread.start()
    
    def _perform_next_scan(self, comparison, value):
        """Perform next scan in background."""
        try:
            def progress_callback(scan_progress):
                # scan_progress is a ScanProgress object
                if scan_progress.total_regions > 0:
                    progress = scan_progress.regions_scanned / scan_progress.total_regions
                    self.after(0, lambda p=progress: self.progress_var.set(p))
            
            # Set progress callback on scan engine
            self.scan_engine.set_progress_callback(progress_callback)
            
            if comparison == ComparisonType.EXACT:
                # For exact value on previous results, we need to manually filter
                # Read all previous addresses and check if they match the new value
                filtered_addresses = []
                for addr in self.current_results.addresses:
                    data, success = self.memory_manager.read_memory(addr, self.current_results.data_type.size)
                    if success and len(data) == self.current_results.data_type.size:
                        try:
                            current_value = ValuePacker.unpack(data, self.current_results.data_type)
                            if current_value == value:
                                filtered_addresses.append(addr)
                        except:
                            pass
                
                import numpy as np
                from datetime import datetime
                from core.scan_engine import ScanResults, ScanType
                
                results = ScanResults(
                    addresses=np.array(filtered_addresses, dtype=np.uint64),
                    data_type=self.current_results.data_type,
                    scan_type=ScanType.EXACT_VALUE,
                    timestamp=datetime.now(),
                    region_count=0,
                    bytes_scanned=0
                )
            elif comparison == ComparisonType.INCREASED:
                results = self.scan_engine.scan_increased(self.current_results)
            elif comparison == ComparisonType.DECREASED:
                results = self.scan_engine.scan_decreased(self.current_results)
            elif comparison == ComparisonType.CHANGED:
                results = self.scan_engine.scan_changed(self.current_results)
            elif comparison == ComparisonType.UNCHANGED:
                results = self.scan_engine.scan_unchanged(self.current_results)
            
            self.current_results = results
            self.after(0, self._update_results, results)
        except Exception as e:
            logger.error(f"Scan error: {e}")
            self.after(0, lambda: messagebox.showerror("Error", f"Scan failed: {e}"))
            self.after(0, self._enable_controls)
    
    def new_scan(self):
        """Start new scan."""
        self.current_results = None
        self.results_tree.delete(*self.results_tree.get_children())
        self.progress_var.set(0)
        self.next_scan_btn.configure(state="disabled")
    
    def _update_results(self, results):
        """Update results display."""
        self.results_tree.delete(*self.results_tree.get_children())
        
        count = min(len(results.addresses), 1000)
        for i in range(count):
            addr = results.addresses[i]
            data, success = self.memory_manager.read_memory(addr, results.data_type.size)
            if success:
                value = ValuePacker.unpack(data, results.data_type)
                value_str = ValueFormatter.format_decimal(value, results.data_type)
            else:
                value_str = "???"
            
            self.results_tree.insert("", "end", values=(f"0x{addr:X}", value_str))
        
        self.progress_var.set(1.0)
        self._enable_controls()
    
    def _enable_controls(self):
        """Enable controls after scan."""
        self.first_scan_btn.configure(state="normal")
        self.new_scan_btn.configure(state="normal")
        if self.current_results:
            self.next_scan_btn.configure(state="normal")
    
    def add_to_table(self):
        """Add selected results to address table."""
        selection = self.results_tree.selection()
        if not selection:
            messagebox.showinfo("Info", "Please select addresses to add")
            return
        
        for item in selection:
            values = self.results_tree.item(item)['values']
            addr = int(values[0], 16)
            data_type = DataType[self.data_type_var.get()]
            self.address_table_manager.add_address(addr, data_type, description="Scan result")
        
        self.refresh_table()
        messagebox.showinfo("Success", f"Added {len(selection)} address(es)")
    
    def add_address_manual(self):
        """Add address manually."""
        addr_str = simpledialog.askstring("Add Address", "Enter address (hex):")
        if not addr_str:
            return
        
        try:
            addr = int(addr_str.replace("0x", ""), 16)
        except ValueError:
            messagebox.showerror("Error", "Invalid address")
            return
        
        type_str = simpledialog.askstring("Add Address", "Enter data type (e.g., INT32):")
        if not type_str:
            return
        
        try:
            data_type = DataType[type_str.upper()]
        except KeyError:
            messagebox.showerror("Error", f"Invalid data type")
            return
        
        desc = simpledialog.askstring("Add Address", "Enter description (optional):") or ""
        self.address_table_manager.add_address(addr, data_type, description=desc)
        self.refresh_table()
    
    def remove_address(self):
        """Remove selected addresses."""
        selection = self.address_tree.selection()
        if not selection:
            return
        
        for item in selection:
            entry_id = self.item_to_id.get(item)
            if entry_id:
                entry = self.address_table_manager.get_address(entry_id)
                if entry and entry.is_frozen:
                    for freeze_id, freeze in self.freezer_manager.get_all_freezes().items():
                        if freeze.address == entry.address:
                            self.freezer_manager.remove_freeze(freeze_id)
                            break
                self.address_table_manager.remove_address(entry_id)
        
        self.refresh_table()
    
    def refresh_table(self):
        """Refresh address table."""
        if not self.address_table_manager:
            return
        
        self.address_tree.delete(*self.address_tree.get_children())
        self.item_to_id.clear()
        
        entries = self.address_table_manager.get_all_addresses()
        self.address_table_manager.read_all_values()
        
        for entry in entries:
            value_str = self.address_table_manager.format_value(entry.id, "decimal") or "???"
            frozen_str = "Yes" if entry.is_frozen else "No"
            
            item = self.address_tree.insert("", "end", values=(
                f"0x{entry.address:X}",
                entry.data_type.name,
                value_str,
                frozen_str,
                entry.description
            ))
            self.item_to_id[item] = entry.id
    
    def edit_value(self):
        """Edit value of selected address."""
        selection = self.address_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        entry_id = self.item_to_id.get(item)
        if not entry_id:
            return
        
        entry = self.address_table_manager.get_address(entry_id)
        if not entry:
            return
        
        new_value_str = simpledialog.askstring("Edit Value", f"Enter new value for 0x{entry.address:X}:")
        if not new_value_str:
            return
        
        try:
            new_value = ValueParser.parse_value(new_value_str, entry.data_type)
            self.address_table_manager.write_value(entry_id, new_value)
            self.refresh_table()
            messagebox.showinfo("Success", "Value written")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to write: {e}")
    
    def toggle_freeze(self):
        """Toggle freeze for selected address."""
        selection = self.address_tree.selection()
        if not selection:
            return
        
        for item in selection:
            entry_id = self.item_to_id.get(item)
            if not entry_id:
                continue
            
            entry = self.address_table_manager.get_address(entry_id)
            if not entry:
                continue
            
            if entry.is_frozen:
                for freeze_id, freeze in self.freezer_manager.get_all_freezes().items():
                    if freeze.address == entry.address:
                        self.freezer_manager.remove_freeze(freeze_id)
                        entry.is_frozen = False
                        break
            else:
                value = self.address_table_manager.read_value(entry_id)
                if value is not None:
                    self.freezer_manager.add_freeze(entry.address, value, entry.data_type, original_value=value)
                    entry.is_frozen = True
        
        self.refresh_table()
    
    def show_context_menu(self, event):
        """Show context menu."""
        item = self.address_tree.identify_row(event.y)
        if item:
            self.address_tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)

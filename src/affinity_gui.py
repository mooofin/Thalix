import tkinter
import customtkinter
import psutil
import ctypes
import threading
import time

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except AttributeError:
        return False

class AffinityApp(customtkinter.CTk):
    def __init__(self):
        super().__init__()

        self.title("Advanced CPU Affinity Manager")
        self.geometry("700x550")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.monitoring = False
        self.monitor_thread = None
        self.all_processes = []
        self.process_buttons = []
        self.cpu_checkboxes = []

        self.status_font = customtkinter.CTkFont(size=14)
        self.color_success = "#2ECC71"
        self.color_error = "#E74C3C"
        self.color_info = "#3498DB"
        self.color_warning = "#F39C12"
        self.color_default = customtkinter.ThemeManager.theme["CTkLabel"]["text_color"]

        self.main_frame = customtkinter.CTkFrame(self)
        self.main_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.main_frame.grid_columnconfigure((0, 1), weight=1)
        self.main_frame.grid_rowconfigure(0, weight=1)

        self.process_side_frame = customtkinter.CTkFrame(self.main_frame, fg_color="transparent")
        self.process_side_frame.grid(row=0, column=0, padx=(10,5), pady=10, sticky="nsew")
        self.process_side_frame.grid_rowconfigure(3, weight=1)

        process_filter_frame = customtkinter.CTkFrame(self.process_side_frame)
        process_filter_frame.grid(row=0, column=0, padx=0, pady=(0,10), sticky="ew")
        process_filter_frame.grid_columnconfigure(0, weight=1)
        customtkinter.CTkLabel(process_filter_frame, text="Find Process").pack(anchor="w", padx=10, pady=(5,0))
        self.process_filter_entry = customtkinter.CTkEntry(process_filter_frame, placeholder_text="Type to filter...")
        self.process_filter_entry.pack(fill="x", expand=True, padx=10, pady=(0,10))
        self.process_filter_entry.bind("<KeyRelease>", self.filter_process_list)

        process_selection_frame = customtkinter.CTkFrame(self.process_side_frame)
        process_selection_frame.grid(row=1, column=0, padx=0, pady=(0,10), sticky="ew")
        process_selection_frame.grid_columnconfigure(0, weight=1)
        customtkinter.CTkLabel(process_selection_frame, text="Selected Process").pack(anchor="w", padx=10, pady=(5,0))
        self.process_entry = customtkinter.CTkEntry(process_selection_frame, placeholder_text="e.g., eldenring.exe")
        self.process_entry.pack(fill="x", expand=True, padx=10, pady=(0,10))
        
        process_info_frame = customtkinter.CTkFrame(self.process_side_frame)
        process_info_frame.grid(row=2, column=0, padx=0, pady=(0,10), sticky="ew")
        process_info_frame.grid_columnconfigure(1, weight=1)
        customtkinter.CTkLabel(process_info_frame, text="Current Affinity:", font=customtkinter.CTkFont(weight="bold")).grid(row=0, column=0, sticky="w", padx=(10,5), pady=5)
        self.current_affinity_label = customtkinter.CTkLabel(process_info_frame, text="N/A", anchor="w", wraplength=180)
        self.current_affinity_label.grid(row=0, column=1, sticky="ew", padx=(0,10), pady=5)

        self.process_list_frame = customtkinter.CTkScrollableFrame(self.process_side_frame, label_text="Running Processes")
        self.process_list_frame.grid(row=3, column=0, sticky="nsew")

        self.cpu_side_frame = customtkinter.CTkFrame(self.main_frame, fg_color="transparent")
        self.cpu_side_frame.grid(row=0, column=1, padx=(5, 10), pady=10, sticky="nsew")
        self.cpu_side_frame.grid_rowconfigure(0, weight=1)
        self.cpu_side_frame.grid_columnconfigure(0, weight=1)
        
        self.tab_view = customtkinter.CTkTabview(self.cpu_side_frame)
        self.tab_view.grid(row=0, column=0, sticky="nsew")
        self.tab_view.add("Manual Select")
        self.tab_view.add("Common Presets")
        self.tab_view.tab("Manual Select").grid_columnconfigure(0, weight=1)
        self.tab_view.tab("Manual Select").grid_rowconfigure(0, weight=1)
        self.tab_view.tab("Common Presets").grid_columnconfigure(0, weight=1)
        
        self.cpu_list_frame = customtkinter.CTkScrollableFrame(self.tab_view.tab("Manual Select"), label_text="Available Cores")
        self.cpu_list_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        manual_button_frame = customtkinter.CTkFrame(self.tab_view.tab("Manual Select"))
        manual_button_frame.grid(row=1, column=0, sticky="ew", padx=5, pady=5)
        manual_button_frame.grid_columnconfigure((0,1), weight=1)
        customtkinter.CTkButton(manual_button_frame, text="Select All", command=self.select_all_cpus).grid(row=0, column=0, padx=(0,5), sticky="ew")
        customtkinter.CTkButton(manual_button_frame, text="Deselect All", command=self.deselect_all_cpus).grid(row=0, column=1, padx=(5,0), sticky="ew")

        preset_frame = customtkinter.CTkFrame(self.tab_view.tab("Common Presets"), fg_color="transparent")
        preset_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        preset_frame.grid_columnconfigure(0, weight=1)
        
        customtkinter.CTkButton(preset_frame, text="Performance Cores Only (Even)", command=lambda: self.apply_preset("p_cores")).pack(fill="x", pady=4, expand=True)
        customtkinter.CTkButton(preset_frame, text="Efficiency Cores Only (Odd)", command=lambda: self.apply_preset("e_cores")).pack(fill="x", pady=4, expand=True)
        customtkinter.CTkButton(preset_frame, text="First Core Only (CPU 0)", command=lambda: self.apply_preset("first_core")).pack(fill="x", pady=4, expand=True)
        customtkinter.CTkButton(preset_frame, text="First Half of Cores", command=lambda: self.apply_preset("first_half")).pack(fill="x", pady=4, expand=True)
        customtkinter.CTkButton(preset_frame, text="Last Half of Cores", command=lambda: self.apply_preset("last_half")).pack(fill="x", pady=4, expand=True)
        customtkinter.CTkButton(preset_frame, text="Disable SMT/Hyper-Threading (Even)", command=lambda: self.apply_preset("no_smt")).pack(fill="x", pady=4, expand=True)

        self.bottom_frame = customtkinter.CTkFrame(self)
        self.bottom_frame.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
        self.bottom_frame.grid_columnconfigure(0, weight=1)

        action_frame = customtkinter.CTkFrame(self.bottom_frame, fg_color="transparent")
        action_frame.grid(row=0, column=0, padx=10, pady=5, sticky="ew")
        action_frame.grid_columnconfigure((0,1,2), weight=1)

        self.apply_button = customtkinter.CTkButton(action_frame, text="Apply Affinity", command=self.apply_affinity)
        self.apply_button.grid(row=0, column=0, padx=(0,5), sticky="ew")
        self.refresh_button = customtkinter.CTkButton(action_frame, text="Refresh List", command=self.populate_process_list)
        self.refresh_button.grid(row=0, column=1, padx=5, sticky="ew")
        self.monitor_switch = customtkinter.CTkSwitch(action_frame, text="Monitor Process", command=self.toggle_monitoring)
        self.monitor_switch.grid(row=0, column=2, padx=(5,0), sticky="e")
        
        self.progress_bar = customtkinter.CTkProgressBar(self.bottom_frame, orientation="horizontal")
        
        self.status_label = customtkinter.CTkLabel(self.bottom_frame, text="Welcome! Run as Admin for full functionality.", font=self.status_font, anchor="w")
        self.status_label.grid(row=2, column=0, padx=10, pady=5, sticky="ew")

        theme_frame = customtkinter.CTkFrame(self.bottom_frame, fg_color="transparent")
        theme_frame.grid(row=3, column=0, padx=10, pady=5, sticky="ew")
        customtkinter.CTkLabel(theme_frame, text="Theme:").pack(side="left")
        customtkinter.CTkSwitch(theme_frame, text="Light/Dark", command=lambda: customtkinter.set_appearance_mode("dark" if self.appearance_mode_var.get() else "light")).pack(side="left")
        self.appearance_mode_var = tkinter.BooleanVar(value=customtkinter.get_appearance_mode() == "Dark")

        self.populate_cpu_list()
        self.populate_process_list()
        
        if not is_admin():
            self.show_admin_warning()
        else:
            self.update_status("Administrator privileges detected.", self.color_info)
    
    def on_process_selected(self, proc_name, proc_pid):
        self.process_entry.delete(0, 'end')
        self.process_entry.insert(0, proc_name)
        try:
            p = psutil.Process(proc_pid)
            affinity = p.cpu_affinity()
            self.current_affinity_label.configure(text=f"PID: {proc_pid} | Using: {affinity}")
        except psutil.NoSuchProcess:
            self.current_affinity_label.configure(text=f"PID: {proc_pid} | (Process has terminated)")
        except psutil.AccessDenied:
            self.current_affinity_label.configure(text=f"PID: {proc_pid} | (Access Denied)")
        except Exception as e:
            self.current_affinity_label.configure(text=f"PID: {proc_pid} | Error: {type(e).__name__}")

    def filter_process_list(self, event=None):
        filter_term = self.process_filter_entry.get().lower()
        for i, proc_info in enumerate(self.all_processes):
            button = self.process_buttons[i]
            if filter_term in proc_info['name'].lower():
                button.pack(fill="x", padx=5, pady=2)
            else:
                button.pack_forget()

    def show_admin_warning(self):
        self.update_status("WARNING: Please restart as Administrator to modify processes.", self.color_warning)
        self.apply_button.configure(state="disabled")
        self.monitor_switch.configure(state="disabled")

    def populate_process_list(self):
        self.process_filter_entry.delete(0, 'end')
        for button in self.process_buttons:
            button.destroy()
        self.process_buttons.clear()
        self.all_processes.clear()

        try:
            all_procs = [p for p in psutil.process_iter(['name', 'pid']) if p.info['name']]
            self.all_processes = sorted(all_procs, key=lambda p: p.info['name'].lower())
        
            for process in self.all_processes:
                proc_name = process.info['name']
                proc_pid = process.info['pid']
                button = customtkinter.CTkButton(
                    self.process_list_frame,
                    text=f"{proc_name}",
                    fg_color="transparent", text_align="left",
                    command=lambda name=proc_name, pid=proc_pid: self.on_process_selected(name, pid)
                )
                button.pack(fill="x", padx=5, pady=2)
                self.process_buttons.append(button)
            self.filter_process_list()
        except Exception as e:
            self.update_status(f"Could not load processes: {e}", self.color_error)

    def populate_cpu_list(self):
        for i in range(psutil.cpu_count()):
            var = tkinter.IntVar(value=1)
            cb = customtkinter.CTkCheckBox(self.cpu_list_frame, text=f"CPU {i}", variable=var)
            cb.pack(anchor="w", padx=10, pady=2)
            self.cpu_checkboxes.append((var, cb))
    
    def apply_preset(self, preset_name):
        cpu_count = len(self.cpu_checkboxes)
        for i, (var, cb) in enumerate(self.cpu_checkboxes):
            if preset_name == "p_cores" or preset_name == "no_smt":
                var.set(1 if i % 2 == 0 else 0)
            elif preset_name == "e_cores":
                var.set(1 if i % 2 != 0 else 0)
            elif preset_name == "first_core":
                var.set(1 if i == 0 else 0)
            elif preset_name == "first_half":
                var.set(1 if i < cpu_count / 2 else 0)
            elif preset_name == "last_half":
                var.set(1 if i >= cpu_count / 2 else 0)
        self.update_status(f"Preset '{preset_name}' prepared. Click 'Apply'.", self.color_info)

    def get_selected_cpus(self):
        return [i for i, (var, _) in enumerate(self.cpu_checkboxes) if var.get() == 1]

    def select_all_cpus(self):
        for var, _ in self.cpu_checkboxes:
            var.set(1)

    def deselect_all_cpus(self):
        for var, _ in self.cpu_checkboxes:
            var.set(0)

    def apply_affinity(self):
        process_name = self.process_entry.get()
        if not process_name:
            self.update_status("Error: Process name cannot be empty.", self.color_error)
            return False

        selected_cpus = self.get_selected_cpus()
        if not selected_cpus:
            self.update_status("Error: At least one CPU core must be selected.", self.color_error)
            return False

        target_process = None
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                if proc.info['name'].lower() == process_name.lower():
                    target_process = psutil.Process(proc.pid)
                    break 
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as e:
            self.update_status(f"Error while scanning for process: {e}", self.color_error)
            return False

        if not target_process:
            self.update_status(f"Error: Process '{process_name}' not found.", self.color_error)
            return False

        try:
            target_process.cpu_affinity(selected_cpus)
            new_affinity = target_process.cpu_affinity()
            self.update_status(f"Success! Affinity for '{process_name}' set to: {new_affinity}", self.color_success)
            self.on_process_selected(target_process.name(), target_process.pid)
            return True
        except psutil.AccessDenied:
            self.update_status(f"Access Denied for '{process_name}'. Run as Administrator.", self.color_error)
        except psutil.NoSuchProcess:
            self.update_status(f"Error: Process '{process_name}' terminated unexpectedly.", self.color_error)
        except ValueError:
            self.update_status("Error: Invalid CPU cores selected for this process.", self.color_error)
        except Exception as e:
            self.update_status(f"An unexpected error occurred: {type(e).__name__}", self.color_error)
        
        return False

    def toggle_monitoring(self):
        if self.monitor_switch.get() == 1:
            if not self.process_entry.get():
                self.update_status("Enter a process name before starting monitor.", self.color_error)
                self.monitor_switch.deselect()
                return

            self.monitoring = True
            self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.monitor_thread.start()
            self.progress_bar.grid(row=1, column=0, padx=10, pady=(5,0), sticky="ew")
            self.progress_bar.start()
            self.apply_button.configure(state="disabled")
            self.process_entry.configure(state="disabled")
            self.update_status(f"Monitoring for '{self.process_entry.get()}'...", self.color_info)
        else:
            self.monitoring = False
            self.progress_bar.stop()
            self.progress_bar.grid_forget()
            self.apply_button.configure(state="normal")
            self.process_entry.configure(state="normal")
            self.update_status("Monitoring stopped.", self.color_default)

    def _monitor_loop(self):
        while self.monitoring:
            if self.apply_affinity():
                self.update_status(f"Monitored process found! Affinity set. Stopping.", self.color_success)
                self.monitor_switch.deselect()
                self.after(0, self.toggle_monitoring)
                break
            time.sleep(2)

    def update_status(self, message, color):
        def _update():
            self.status_label.configure(text=message, text_color=color)
        self.after(0, _update)

if __name__ == "__main__":
    customtkinter.set_appearance_mode("System")
    customtkinter.set_default_color_theme("blue")
    
    app = AffinityApp()
    app.mainloop()

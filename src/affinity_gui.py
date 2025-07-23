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

        self.title("CPU Affinity Setter")
        self.geometry("600x480")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.monitoring = False
        self.monitor_thread = None
        self.cpu_checkboxes = []
        self.process_buttons = []

        self.status_font = customtkinter.CTkFont(size=14)
        self.info_font = customtkinter.CTkFont(size=12, slant="italic")
        self.color_success = "#2ECC71"
        self.color_error = "#E74C3C"
        self.color_info = "#3498DB"
        self.color_default = self.cget("fg_color")

        self.main_frame = customtkinter.CTkFrame(self)
        self.main_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.main_frame.grid_columnconfigure((0, 1), weight=1)

        self.status_frame = customtkinter.CTkFrame(self)
        self.status_frame.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")

        process_frame = customtkinter.CTkFrame(self.main_frame)
        process_frame.grid(row=0, column=0, padx=(10, 5), pady=10, sticky="nsew")
        process_frame.grid_rowconfigure(2, weight=1)

        customtkinter.CTkLabel(process_frame, text="Process Name", font=customtkinter.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=2, padx=10, pady=(10, 5))
        self.process_entry = customtkinter.CTkEntry(process_frame, placeholder_text="e.g., eldenring.exe")
        self.process_entry.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky="ew")

        self.process_list_frame = customtkinter.CTkScrollableFrame(process_frame, label_text="Running Processes")
        self.process_list_frame.grid(row=2, column=0, columnspan=2, padx=10, pady=5, sticky="nsew")

        cpu_frame = customtkinter.CTkFrame(self.main_frame)
        cpu_frame.grid(row=0, column=1, padx=(5, 10), pady=10, sticky="nsew")
        cpu_frame.grid_rowconfigure(1, weight=1)

        customtkinter.CTkLabel(cpu_frame, text="Select CPU Cores", font=customtkinter.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=2, padx=10, pady=(10, 5))
        self.cpu_list_frame = customtkinter.CTkScrollableFrame(cpu_frame, label_text="Available Cores")
        self.cpu_list_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky="nsew")

        select_all_button = customtkinter.CTkButton(cpu_frame, text="Select All", command=self.select_all_cpus)
        select_all_button.grid(row=2, column=0, padx=(10, 5), pady=10, sticky="ew")
        deselect_all_button = customtkinter.CTkButton(cpu_frame, text="Deselect All", command=self.deselect_all_cpus)
        deselect_all_button.grid(row=2, column=1, padx=(5, 10), pady=10, sticky="ew")

        self.status_frame.grid_columnconfigure(0, weight=1)
        
        action_frame = customtkinter.CTkFrame(self.status_frame, fg_color="transparent")
        action_frame.grid(row=0, column=0, padx=10, pady=5, sticky="ew")
        action_frame.grid_columnconfigure(0, weight=1)

        self.apply_button = customtkinter.CTkButton(action_frame, text="Apply Affinity", command=self.apply_affinity)
        self.apply_button.grid(row=0, column=0, padx=(0,5), sticky="ew")

        self.refresh_button = customtkinter.CTkButton(action_frame, text="Refresh Processes", command=self.populate_process_list)
        self.refresh_button.grid(row=0, column=1, padx=(5,0), sticky="ew")
        
        monitor_frame = customtkinter.CTkFrame(self.status_frame, fg_color="transparent")
        monitor_frame.grid(row=1, column=0, padx=10, pady=5, sticky="ew")

        self.monitor_switch = customtkinter.CTkSwitch(monitor_frame, text="Monitor Process", command=self.toggle_monitoring)
        self.monitor_switch.pack(side="right")
        
        self.status_label = customtkinter.CTkLabel(self.status_frame, text="Welcome!", font=self.status_font, anchor="w")
        self.status_label.grid(row=2, column=0, padx=10, pady=10, sticky="ew")

        self.populate_cpu_list()
        self.populate_process_list()
        
        if not is_admin():
            self.show_admin_warning()
        else:
            self.update_status("Ready. Please run as Administrator for full functionality.", self.color_info)

    def show_admin_warning(self):
        self.update_status("ERROR: Please restart the application as an Administrator.", self.color_error)
        self.apply_button.configure(state="disabled")
        self.monitor_switch.configure(state="disabled")
        self.process_entry.configure(state="disabled")

    def populate_process_list(self):
        for button in self.process_buttons:
            button.destroy()
        self.process_buttons.clear()

        processes = sorted(psutil.process_iter(['name']), key=lambda p: p.info['name'].lower() if p.info['name'] else '')
        
        for process in processes:
            if process.info['name']:
                proc_name = process.info['name']
                button = customtkinter.CTkButton(
                    self.process_list_frame,
                    text=proc_name,
                    fg_color="transparent",
                    text_align="left",
                    command=lambda name=proc_name: self.process_entry.delete(0, 'end') or self.process_entry.insert(0, name)
                )
                button.pack(fill="x", padx=5, pady=2)
                self.process_buttons.append(button)

    def populate_cpu_list(self):
        cpu_count = psutil.cpu_count()
        for i in range(cpu_count):
            var = tkinter.IntVar(value=1)
            cb = customtkinter.CTkCheckBox(self.cpu_list_frame, text=f"CPU {i}", variable=var)
            cb.pack(anchor="w", padx=10, pady=2)
            self.cpu_checkboxes.append((var, cb))
    
    def get_selected_cpus(self):
        selected_cpus = []
        for i, (var, _) in enumerate(self.cpu_checkboxes):
            if var.get() == 1:
                selected_cpus.append(i)
        return selected_cpus

    def select_all_cpus(self):
        for var, _ in self.cpu_checkboxes:
            var.set(1)

    def deselect_all_cpus(self):
        for var, _ in self.cpu_checkboxes:
            var.set(0)

    def apply_affinity(self):
        process_name = self.process_entry.get()
        if not process_name:
            self.update_status("Error: Please enter a process name.", self.color_error)
            return

        selected_cpus = self.get_selected_cpus()
        if not selected_cpus:
            self.update_status("Error: You must select at least one CPU core.", self.color_error)
            return

        target_process = None
        for process in psutil.process_iter(['pid', 'name']):
            if process.info['name'].lower() == process_name.lower():
                target_process = process
                break
        
        if not target_process:
            self.update_status(f"'{process_name}' not found. Make sure it is running.", self.color_error)
            return False

        try:
            p = psutil.Process(target_process.pid)
            p.cpu_affinity(selected_cpus)
            self.update_status(f"Affinity for '{process_name}' set to CPUs: {selected_cpus}", self.color_success)
            return True
        except psutil.AccessDenied:
            self.update_status(f"Access Denied for '{process_name}'. Run as Administrator.", self.color_error)
        except psutil.NoSuchProcess:
            self.update_status(f"Process '{process_name}' disappeared before affinity could be set.", self.color_error)
        except Exception as e:
            self.update_status(f"An unexpected error occurred: {e}", self.color_error)
        
        return False

    def toggle_monitoring(self):
        if self.monitor_switch.get() == 1:
            self.monitoring = True
            self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.monitor_thread.start()
            self.apply_button.configure(state="disabled")
            self.process_entry.configure(state="disabled")
            self.update_status(f"Monitoring for '{self.process_entry.get()}'...", self.color_info)
        else:
            self.monitoring = False
            if self.monitor_thread:
                self.monitor_thread.join(timeout=0.1)
            self.apply_button.configure(state="normal")
            self.process_entry.configure(state="normal")
            self.update_status("Monitoring stopped.", self.color_default)

    def _monitor_loop(self):
        while self.monitoring:
            if self.apply_affinity():
                self.update_status(f"Monitored process found! Affinity set. Stopping monitor.", self.color_success)
                self.monitor_switch.deselect()
                self.toggle_monitoring()
                break
            time.sleep(3)

    def update_status(self, message, color):
        def _update():
            self.status_label.configure(text=message, text_color=color)
        self.after(0, _update)

if __name__ == "__main__":
    customtkinter.set_appearance_mode("System")
    customtkinter.set_default_color_theme("blue")
    
    app = AffinityApp()
    app.mainloop()

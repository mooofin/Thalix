import os
import sys
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk

# Attempt to import the project's cheat engine integration parser
try:
    from cheat_engine_integration import CheatEngineIntegration, CheatEngineTable
except Exception:
    CheatEngineIntegration = None
    CheatEngineTable = None


class CEWrapperApp:
    def __init__(self, root):
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self.root = root
        self.root.title("Cheat Engine - Small Wrapper")
        self.root.geometry("760x260")

        # Auto-detect Cheat Engine path
        detected_ce = self.find_cheat_engine()
        self.ce_path = tk.StringVar(value=detected_ce if detected_ce else "")
        # Pre-fill the user's provided cheat table path as a helpful default
        self.ct_path = tk.StringVar(value=r"C:\Users\SIDDHARTH U\Downloads\1FRDarkSoulsRemastered.CT")

        self.create_widgets()
    
    def find_cheat_engine(self):
        """Auto-detect Cheat Engine installation"""
        common_paths = [
            r"C:\Program Files\Cheat Engine 7.5\cheatengine-x86_64.exe",
            r"C:\Program Files (x86)\Cheat Engine 7.5\cheatengine-x86_64.exe",
            r"C:\Program Files\Cheat Engine 7.4\cheatengine-x86_64.exe",
            r"C:\Program Files (x86)\Cheat Engine 7.4\cheatengine-x86_64.exe",
        ]
        for path in common_paths:
            if os.path.exists(path):
                return path
        return None

    def create_widgets(self):
        frame = ctk.CTkFrame(self.root, corner_radius=8)
        frame.pack(fill="both", expand=True, padx=12, pady=12)

        ctk.CTkLabel(frame, text="Cheat Engine executable:").grid(row=0, column=0, sticky="w", padx=8, pady=(8, 4))
        ce_entry = ctk.CTkEntry(frame, textvariable=self.ce_path, width=520)
        ce_entry.grid(row=1, column=0, padx=8, pady=(0, 8), sticky="w")
        ctk.CTkButton(frame, text="Browse...", command=self.browse_ce).grid(row=1, column=1, padx=8, pady=(0,8))
        ctk.CTkButton(frame, text="Open CE", command=self.open_cheat_engine, fg_color="#4CAF50").grid(row=1, column=2, padx=8, pady=(0,8))

        ctk.CTkLabel(frame, text="Cheat table (.ct):").grid(row=2, column=0, sticky="w", padx=8, pady=(8, 4))
        ct_entry = ctk.CTkEntry(frame, textvariable=self.ct_path, width=520)
        ct_entry.grid(row=3, column=0, padx=8, pady=(0, 8), sticky="w")
        ctk.CTkButton(frame, text="Browse...", command=self.browse_ct).grid(row=3, column=1, padx=8, pady=(0,8))
        ctk.CTkButton(frame, text="Open .ct in CE", command=self.open_ct_in_ce, fg_color="#DC143C").grid(row=3, column=2, padx=8, pady=(0,8))

        ctk.CTkButton(frame, text="Parse .ct (preview)", command=self.parse_ct, fg_color="#1E90FF").grid(row=4, column=0, padx=8, pady=(6,8), sticky="w")
        self.status = ctk.CTkLabel(frame, text="Ready")
        self.status.grid(row=4, column=1, columnspan=2, sticky="e", padx=8, pady=(6,8))

    def browse_ce(self):
        p = filedialog.askopenfilename(title="Select Cheat Engine executable", filetypes=[('Executables', '*.exe'), ('All files','*.*')])
        if p:
            self.ce_path.set(p)

    def browse_ct(self):
        p = filedialog.askopenfilename(title="Select Cheat Table (.ct)", filetypes=[('Cheat Table','*.ct'), ('All files','*.*')])
        if p:
            self.ct_path.set(p)

    def open_cheat_engine(self):
        exe = self.ce_path.get()
        if not exe:
            messagebox.showwarning("Missing path", "Please select a Cheat Engine executable first")
            return
        if not os.path.exists(exe):
            messagebox.showerror("Not found", f"Executable not found: {exe}")
            return
        try:
            # Launch with admin privileges using PowerShell
            cmd = f'Start-Process "{exe}" -Verb RunAs'
            subprocess.Popen(['powershell', '-Command', cmd], shell=False)
            self.status.configure(text="Launched Cheat Engine (Admin)")
        except Exception as e:
            messagebox.showerror("Launch failed", str(e))
            self.status.configure(text="Launch failed")

    def open_ct_in_ce(self):
        exe = self.ce_path.get()
        ct = self.ct_path.get()
        if not exe:
            messagebox.showwarning("Missing path", "Please select a Cheat Engine executable first")
            return
        if not ct:
            messagebox.showwarning("Missing .ct", "Please select a .ct file to open")
            return
        if not os.path.exists(exe):
            messagebox.showerror("Not found", f"Executable not found: {exe}")
            return
        if not os.path.exists(ct):
            messagebox.showerror("Not found", f"Cheat table not found: {ct}")
            return
        try:
            # Launch with admin privileges using PowerShell
            cmd = f'Start-Process "{exe}" -ArgumentList "{ct}" -Verb RunAs'
            subprocess.Popen(['powershell', '-Command', cmd], shell=False)
            self.status.configure(text="Launched CE with .ct (Admin)")
        except Exception as e:
            messagebox.showerror("Launch failed", str(e))
            self.status.configure(text="Launch failed")

    def parse_ct(self):
        ct = self.ct_path.get()
        if not ct or not os.path.exists(ct):
            messagebox.showwarning("Missing .ct", "Please provide an existing .ct file to parse")
            return

        if CheatEngineTable:
            try:
                table = CheatEngineTable()
                ok = table.load_ct_file(ct)
                if ok:
                    count = len(table.entries)
                    messagebox.showinfo("Parse result", f"Parsed {count} entries from {os.path.basename(ct)}")
                    self.status.configure(text=f"Parsed {count} entries")
                else:
                    messagebox.showerror("Parse failed", "Failed to parse the .ct file")
                    self.status.configure(text="Parse failed")
            except Exception as e:
                messagebox.showerror("Parse error", str(e))
                self.status.configure(text="Parse failed")
        else:
            # Fallback: try to open file and look for strings
            try:
                with open(ct, 'r', errors='ignore') as f:
                    data = f.read()
                # crude heuristic: count occurrences of '<CheatEntry>' or 'CheatEntry'
                count = data.count('CheatEntry')
                messagebox.showinfo("Parse (heuristic)", f"Found approx {count} entries (heuristic)")
                self.status.configure(text=f"Heuristic parsed {count}")
            except Exception as e:
                messagebox.showerror("Parse error", str(e))
                self.status.configure(text="Parse failed")


if __name__ == '__main__':
    root = ctk.CTk()
    app = CEWrapperApp(root)
    root.mainloop()

import time
import os
import threading
import subprocess
from pathlib import Path
from PIL import Image
from flasher.config import RUN_MODE, BASE_PATH
import flasher.config as config

if RUN_MODE == "PC":
    import customtkinter as ctk
    from tkinter import messagebox, filedialog
    from flasher.core import UploaderCore
    from flasher.utils import get_arduino_ports

    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("blue")

    class WindowsGuiApp(ctk.CTk):
        def __init__(self):
            super().__init__()
            self.title("Dual-Mode Arduino Uploader - Professional")
            self.geometry("700x700")

            self.core = UploaderCore(self.gui_log, self.gui_status_update)
            self.core.load_app_settings()

            self.default_sketch_path_var = ctk.StringVar(value=self.core.settings["default_sketch_path"])
            self.custom_sketch_path_var = ctk.StringVar(value=self.core.settings["custom_sketch_path"])
            self.baud_rate_var = ctk.StringVar(value=self.core.settings["baud_rate"])
            self.port_var = ctk.StringVar(value=self.core.settings["port"])
            self.fqbn_var = ctk.StringVar(value=self.core.settings["fqbn"])
            self.first_port_check_done = False

            self._load_icons()
            self._create_widgets()

            self.refresh_ports()
            self.periodic_port_check()
            self.protocol("WM_DELETE_WINDOW", self.on_closing)

        def _load_icons(self):
            try:
                self.settings_icon = ctk.CTkImage(light_image=Image.open(BASE_PATH / "icons/settings.png"), size=(16, 16))
                self.browse_icon = ctk.CTkImage(light_image=Image.open(BASE_PATH / "icons/folder.png"), size=(16, 16))
                self.log_icon = ctk.CTkImage(light_image=Image.open(BASE_PATH / "icons/log.png"), size=(16, 16))
                self.clear_icon = ctk.CTkImage(light_image=Image.open(BASE_PATH / "icons/clear.png"), size=(16, 16))
                self.about_icon = ctk.CTkImage(light_image=Image.open(BASE_PATH / "icons/about.png"), size=(16, 16))
            except Exception as e:
                print(f"Error loading icons: {e}")
                self.settings_icon, self.browse_icon, self.log_icon, self.clear_icon, self.about_icon = None, None, None, None, None

        def _create_widgets(self):
            self.grid_columnconfigure(0, weight=1)
            self.grid_rowconfigure(2, weight=1)

            quick_frame = ctk.CTkFrame(self, corner_radius=10)
            quick_frame.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
            quick_frame.grid_columnconfigure(1, weight=1)
            ctk.CTkLabel(quick_frame, text="1. Quick Upload (Color Sensor)", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, columnspan=4, padx=15, pady=(15, 10), sticky="w")
            ctk.CTkLabel(quick_frame, text="Default Sketch Path:").grid(row=1, column=0, padx=15, pady=(0, 5), sticky="w")
            ctk.CTkLabel(quick_frame, textvariable=self.default_sketch_path_var, text_color="gray", wraplength=400, justify="left").grid(row=1, column=1, columnspan=2, sticky="w", padx=10)
            ctk.CTkButton(quick_frame, text="Set/Change", command=self.set_default_sketch, image=self.browse_icon, width=120, fg_color="transparent", border_width=1, text_color=("gray10", "#DCE4EE")).grid(row=1, column=3, padx=15, sticky="e")
            ctk.CTkLabel(quick_frame, text="COM Port:").grid(row=2, column=0, padx=15, pady=(15, 0), sticky="w")
            self.port_menu = ctk.CTkOptionMenu(quick_frame, variable=self.port_var, values=["No ports"])
            self.port_menu.grid(row=3, column=0, padx=15, pady=(0, 15), sticky="w")
            ctk.CTkLabel(quick_frame, text="Baud Rate:").grid(row=2, column=1, padx=10, pady=(15, 0), sticky="w")
            ctk.CTkEntry(quick_frame, textvariable=self.baud_rate_var, width=100).grid(row=3, column=1, padx=10, pady=(0, 15), sticky="w")
            ctk.CTkButton(quick_frame, text="Refresh Ports", command=self.refresh_ports, fg_color="transparent", border_width=1, text_color=("gray10", "#DCE4EE")).grid(row=3, column=2, padx=10, pady=(0, 15), sticky="w")
            self.quick_upload_button = ctk.CTkButton(quick_frame, text="Upload Color Sensor Sketch", command=lambda: self.start_upload_thread(use_default=True), fg_color="#2FA572", hover_color="#106A43")
            self.quick_upload_button.grid(row=4, column=0, columnspan=4, padx=15, pady=(0, 15), sticky="ew")

            custom_frame = ctk.CTkFrame(self, corner_radius=10)
            custom_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
            custom_frame.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(custom_frame, text="2. Custom Upload (Other sketch)", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, columnspan=2, padx=15, pady=(15, 10), sticky="w")
            ctk.CTkLabel(custom_frame, text="Sketch to Upload:").grid(row=1, column=0, padx=15, pady=0, sticky="w")
            sketch_input_frame = ctk.CTkFrame(custom_frame, fg_color="transparent")
            sketch_input_frame.grid(row=2, column=0, columnspan=2, padx=15, pady=5, sticky="ew")
            sketch_input_frame.grid_columnconfigure(0, weight=1)
            ctk.CTkEntry(sketch_input_frame, textvariable=self.custom_sketch_path_var).grid(row=0, column=0, sticky="ew", padx=(0, 10))
            ctk.CTkButton(sketch_input_frame, text="Browse...", command=self.select_custom_sketch, image=self.browse_icon, width=100).grid(row=0, column=1)
            self.custom_upload_button = ctk.CTkButton(custom_frame, text="Upload Selected Sketch", command=lambda: self.start_upload_thread(use_default=False))
            self.custom_upload_button.grid(row=3, column=0, columnspan=2, padx=15, pady=(10, 15), sticky="ew")

            log_frame = ctk.CTkFrame(self, corner_radius=10)
            log_frame.grid(row=2, column=0, padx=20, pady=(10, 20), sticky="nsew")
            log_frame.grid_columnconfigure(0, weight=1)
            log_frame.grid_rowconfigure(1, weight=1)
            log_buttons = ctk.CTkFrame(log_frame, fg_color="transparent")
            log_buttons.grid(row=0, column=0, padx=15, pady=10, sticky="ew")
            ctk.CTkButton(log_buttons, text="About", command=self.show_about_dialog, image=self.about_icon, width=80, fg_color="transparent", border_width=1, text_color=("gray10", "#DCE4EE")).pack(side="left", padx=(0, 5))
            ctk.CTkButton(log_buttons, text="Clear Log", command=self.clear_log_display, image=self.clear_icon, width=100, fg_color="transparent", border_width=1, text_color=("gray10", "#DCE4EE")).pack(side="left", padx=5)
            ctk.CTkButton(log_buttons, text="View Log (.csv)", command=self.open_log_file, image=self.log_icon, width=120, fg_color="transparent", border_width=1, text_color=("gray10", "#DCE4EE")).pack(side="left", padx=5)
            ctk.CTkButton(log_buttons, text="Config...", command=self.open_settings_window, image=self.settings_icon, width=100, fg_color="transparent", border_width=1, text_color=("gray10", "#DCE4EE")).pack(side="right")
            self.log_area = ctk.CTkTextbox(log_frame, wrap="word", corner_radius=5)
            self.log_area.grid(row=1, column=0, padx=15, pady=(0, 15), sticky="nsew")

        def gui_log(self, msg):
            if "ERROR" in msg: print(msg)
            self.log_area.configure(state="normal")
            if any(k in msg for k in ("Compiling", "Uploading", "Writing", "Reading")):
                 self.log_area.insert("end", msg + "\n")
                 self.update_idletasks()
            else:
                 self.log_area.insert("end", f"{time.strftime('%H:%M:%S')} - {msg}\n")
            self.log_area.see("end")
            self.log_area.configure(state="disabled")

        def gui_status_update(self, status):
            if status == "UPLOADING":
                self.quick_upload_button.configure(state="disabled")
                self.custom_upload_button.configure(state="disabled")
            else:
                self.quick_upload_button.configure(state="normal")
                self.custom_upload_button.configure(state="normal")
                if status == "FAIL": messagebox.showerror("Upload Failed", "Upload failed. Check log.")

        def on_closing(self):
            self.core.settings.update({
                "default_sketch_path": self.default_sketch_path_var.get(),
                "custom_sketch_path": self.custom_sketch_path_var.get(),
                "baud_rate": self.baud_rate_var.get(),
                "port": self.port_var.get(),
                "fqbn": self.fqbn_var.get()
            })
            self.core.save_app_settings()
            self.destroy()

        def set_default_sketch(self):
            path = filedialog.askopenfilename(title="Select default COLOR-SENSOR.ino", filetypes=[("Arduino Files", "*.ino")])
            if path:
                self.default_sketch_path_var.set(path)
                self.gui_log(f"New default sketch: {path}")

        def select_custom_sketch(self):
            path = filedialog.askopenfilename(title="Select custom Arduino Sketch", filetypes=[("Arduino Files", "*.ino")])
            if path:
                self.custom_sketch_path_var.set(path)
                self.gui_log(f"Custom sketch selected: {path}")

        def refresh_ports(self):
            self.gui_log("Scanning COM ports...")
            ports = get_arduino_ports()
            last_port = self.port_var.get()
            if ports:
                self.port_menu.configure(values=ports)
                self.port_var.set(last_port if last_port in ports else ports[0])
                self.gui_log(f"Ports found: {', '.join(ports)}")
            else:
                self.port_menu.configure(values=["No ports"])
                self.port_var.set("No ports")
                self.gui_log("No compatible ports detected.")

        def start_upload_thread(self, use_default=False):
            self.clear_log_display()
            sketch_path = self.default_sketch_path_var.get() if use_default else self.custom_sketch_path_var.get()
            if not Path(sketch_path).is_file():
                messagebox.showerror("Error", f"Sketch file not found:\n{sketch_path}")
                return
            threading.Thread(target=self.core.start_compile_and_upload, args=(sketch_path, self.port_var.get(), self.baud_rate_var.get(), self.fqbn_var.get()), daemon=True).start()
        
        def periodic_port_check(self):
            if not self.first_port_check_done:
                self.first_port_check_done = True
                self.after(2000, self.periodic_port_check)
                return
            try:
                ports_in_menu = self.port_menu.cget("values")
                current_ports = get_arduino_ports()
                if ports_in_menu == ["No ports"] and not current_ports: pass
                elif sorted(ports_in_menu) != sorted(current_ports):
                    self.gui_log("Port change detected! Refreshing...")
                    self.refresh_ports()
                self.after(2000, self.periodic_port_check)
            except Exception as e: print(f"Error during port check: {e}")

        def open_settings_window(self):
            settings_win = ctk.CTkToplevel(self)
            settings_win.title("Configure Paths")
            settings_win.geometry("550x300")
            settings_win.grab_set()

            cli_path_var, log_path_var, fqbn_var = ctk.StringVar(value=self.core.settings["arduino_cli_path"]), ctk.StringVar(value=self.core.settings["log_csv_path"]), ctk.StringVar(value=self.core.settings["fqbn"])

            def save_paths():
                self.core.settings.update({"arduino_cli_path": cli_path_var.get(), "log_csv_path": log_path_var.get(), "fqbn": fqbn_var.get()})
                self.fqbn_var.set(fqbn_var.get())
                self.core.save_app_settings()
                messagebox.showinfo("Saved", "Paths have been updated.", parent=settings_win)
                settings_win.destroy()

            ctk.CTkLabel(settings_win, text="Arduino CLI Path:", font=ctk.CTkFont(weight="bold")).pack(pady=(20, 5), padx=20, anchor="w")
            cli_frame = ctk.CTkFrame(settings_win, fg_color="transparent")
            cli_frame.pack(fill="x", padx=20)
            ctk.CTkEntry(cli_frame, textvariable=cli_path_var).pack(side="left", expand=True, fill="x", padx=(0, 10))
            ctk.CTkButton(cli_frame, text="Browse...", command=lambda: cli_path_var.set(p) if (p:=filedialog.askopenfilename()) else None, width=80).pack(side="right")
            
            ctk.CTkLabel(settings_win, text="Log CSV Path:", font=ctk.CTkFont(weight="bold")).pack(pady=(15, 5), padx=20, anchor="w")
            log_frame_settings = ctk.CTkFrame(settings_win, fg_color="transparent")
            log_frame_settings.pack(fill="x", padx=20)
            ctk.CTkEntry(log_frame_settings, textvariable=log_path_var).pack(side="left", expand=True, fill="x", padx=(0, 10))
            ctk.CTkButton(log_frame_settings, text="Browse...", command=lambda: log_path_var.set(p) if (p:=filedialog.asksaveasfilename()) else None, width=80).pack(side="right")

            ctk.CTkLabel(settings_win, text="Default FQBN:", font=ctk.CTkFont(weight="bold")).pack(pady=(15, 5), padx=20, anchor="w")
            ctk.CTkEntry(settings_win, textvariable=fqbn_var).pack(fill="x", padx=20)
            ctk.CTkButton(settings_win, text="Save and Close", command=save_paths, fg_color="#2FA572", hover_color="#106A43").pack(pady=25)

        def open_log_file(self):
            if config.LOG_CSV_PATH.exists():
                self.gui_log(f"Opening log: {config.LOG_CSV_PATH}")
                try: os.startfile(config.LOG_CSV_PATH)
                except AttributeError: subprocess.run(['open', config.LOG_CSV_PATH])
            else:
                self.gui_log("Log file does not exist.")
                messagebox.showinfo("Info", "Log file does not exist. Upload a sketch to create it.")

        def clear_log_display(self):
            self.log_area.configure(state="normal")
            self.log_area.delete('1.0', "end")
            self.log_area.configure(state="disabled")

        def show_about_dialog(self):
            messagebox.showinfo("About", "Dual-Mode Arduino Uploader (Professional)\nVersion 3.0 (Modular)\nAuthor: Diego Gallegos")

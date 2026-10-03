import sys
from flasher.config import RUN_MODE, ARDUINO_CLI_PATH

if __name__ == "__main__":
    if not ARDUINO_CLI_PATH.exists():
        err_msg = f"Fatal Error: arduino-cli not found at:\n{ARDUINO_CLI_PATH}\n\n" \
                  f"Please ensure it is in the 'arduino-cli' folder next to the executable."
        if RUN_MODE == "PC":
            try:
                import tkinter as tk
                from tkinter import messagebox
                root = tk.Tk()
                root.withdraw()
                messagebox.showerror("Fatal Error", err_msg)
            except:
                print(err_msg)
        else:
            print(err_msg)
        sys.exit(1)

    if RUN_MODE == "PC":
        from flasher.gui import WindowsGuiApp
        print("Starting in PC (GUI) mode...")
        app = WindowsGuiApp()
        app.mainloop()
    elif RUN_MODE == "PI":
        from flasher.hardware import PiHardwareApp
        print("Starting in Raspberry Pi mode...")
        app = PiHardwareApp()
        app.run()

import time
import sys
import subprocess
import threading
from flasher.config import RUN_MODE

if RUN_MODE == "PI":
    import RPi.GPIO as GPIO
    from RPLCD.i2c import CharLCD
    from flasher.core import UploaderCore
    from flasher.utils import get_arduino_ports
    import flasher.config as config

    class PiHardwareApp:
        def __init__(self):
            self.is_busy = False
            self.core = UploaderCore(self.lcd_log, self.lcd_status_update)
            self.core.load_app_settings()
            self.setup_gpio()
            try:
                self.lcd = CharLCD(i2c_expander='PCF8574', address=0x27, port=1, cols=16, rows=2, charmap='A00', auto_linebreaks=True)
                self.lcd.clear()
                self.lcd.write_string("Uploader Ready!")
            except Exception as e:
                print(f"Fatal Error: Could not init I2C LCD at 0x27. Error: {e}")
                sys.exit(1)

            self.menus = {
                "main": {"title": "Main Menu", "items": [("Quick Upload", self.action_quick_upload), ("Select Port", self.action_menu_ports), ("View Info", self.action_menu_info), ("Shutdown Pi", self.action_shutdown)]},
                "ports": {"title": "Select COM Port", "items": []},
                "info": {"title": "System Info", "items": [(f"FQBN: {self.core.settings['fqbn'][:16]}", None), ("Back", self.action_menu_main)]}
            }
            self.menu_stack = ["main"]
            self.current_selection = 0
            time.sleep(1)

        def setup_gpio(self):
            GPIO.setmode(GPIO.BCM)
            for pin in [config.PIN_BTN_UP, config.PIN_BTN_DOWN, config.PIN_BTN_OK, config.PIN_BTN_BACK]:
                GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                GPIO.add_event_detect(pin, GPIO.FALLING, callback=self.on_button_press, bouncetime=300)

        def lcd_log(self, msg):
            if any(k in msg for k in ("Writing", "Leaving", "Done")): return
            print(f"[LOG] {msg}")
            self.lcd.clear()
            if "Compiling" in msg: self.lcd.write_string("Compiling...")
            elif "Uploading" in msg: self.lcd.write_string("Uploading...")
            elif "Reading" in msg: self.lcd.write_string("Reading serial...")
            elif "ERROR" in msg:
                self.lcd.write_string("Error!")
                time.sleep(1)
                self.lcd.crlf()
                self.lcd.write_string(msg.split(":")[-1][:16])
            else: self.lcd.write_string(msg[:16])
            time.sleep(0.1)

        def lcd_status_update(self, status):
            self.is_busy = (status == "UPLOADING")
            if status in ("SUCCESS", "FAIL"):
                self.lcd.clear()
                self.lcd.write_string("Success!" if status == "SUCCESS" else "Failed!\nCheck csv log")
                time.sleep(2 if status == "SUCCESS" else 3)
                self.display_menu()

        def display_menu(self):
            if self.is_busy: return
            menu = self.menus[self.menu_stack[-1]]
            items = menu["items"]
            if not items:
                self.lcd.clear()
                self.lcd.write_string(f"{menu['title']}\nNo items!")
                return
            self.current_selection %= len(items)
            self.lcd.clear()
            self.lcd.write_string(f">{items[self.current_selection][0][:15]}")
            if self.current_selection + 1 < len(items):
                self.lcd.crlf()
                self.lcd.write_string(f" {items[self.current_selection + 1][0][:15]}")

        def on_button_press(self, pin):
            if self.is_busy: return
            items = self.menus[self.menu_stack[-1]]["items"]
            if pin == config.PIN_BTN_DOWN: self.current_selection = (self.current_selection + 1) % len(items)
            elif pin == config.PIN_BTN_UP: self.current_selection = (self.current_selection - 1) % len(items)
            elif pin == config.PIN_BTN_BACK and len(self.menu_stack) > 1:
                self.menu_stack.pop()
                self.current_selection = 0
            elif pin == config.PIN_BTN_OK:
                action = items[self.current_selection][1]
                if action: action()
            self.display_menu()

        def action_menu_main(self): self.menu_stack = ["main"]; self.current_selection = 0
        def action_menu_ports(self):
            self.lcd.clear()
            self.lcd.write_string("Scanning...")
            ports = get_arduino_ports() or ["No ports found"]
            self.menus["ports"]["items"] = [(p, lambda p=p: self.action_set_port(p)) for p in ports] + [("Back", self.action_menu_main)]
            self.menu_stack.append("ports")
            self.current_selection = 0

        def action_menu_info(self): self.menu_stack.append("info"); self.current_selection = 0
        def action_set_port(self, port):
            if port != "No ports found":
                self.core.settings["port"] = port
                self.core.save_app_settings()
                self.lcd.clear()
                self.lcd.write_string(f"Port set:\n{port}")
                time.sleep(2)
            self.menu_stack.pop()
            self.current_selection = 0
            self.display_menu()

        def action_quick_upload(self):
            self.lcd.clear()
            self.lcd.write_string("Starting...")
            threading.Thread(target=self.core.start_compile_and_upload, args=(self.core.settings["default_sketch_path"], self.core.settings["port"], self.core.settings["baud_rate"], self.core.settings["fqbn"]), daemon=True).start()
        
        def action_shutdown(self):
            self.lcd.clear()
            self.lcd.write_string("Shutting down...")
            GPIO.cleanup()
            subprocess.run(["sudo", "shutdown", "-h", "now"])
            sys.exit()

        def run(self):
            self.display_menu()
            try:
                while True: time.sleep(1)
            except KeyboardInterrupt: print("Closing...")
            finally:
                self.lcd.clear()
                GPIO.cleanup()

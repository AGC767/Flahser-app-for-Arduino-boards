import os
import sys
import json
from pathlib import Path

# --- PLATFORM DETECTION ---
try:
    import RPi.GPIO as GPIO
    from RPLCD.i2c import CharLCD
    RUN_MODE = "PI"
except (ImportError, RuntimeError):
    RUN_MODE = "PC"

# --- GPIO PINS (PI ONLY) ---
if RUN_MODE == "PI":
    PIN_LCD_SDA = 2
    PIN_LCD_SCL = 3
    PIN_BTN_UP = 17
    PIN_BTN_DOWN = 27
    PIN_BTN_OK = 22
    PIN_BTN_BACK = 23

# --- GLOBAL UTILS ---
def get_base_path():
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS)
    else:
        # Since this is in flasher/, we go up one level to the root
        return Path(__file__).parent.parent

BASE_PATH = get_base_path()
SETTINGS_FILE = Path.home() / "dual_uploader_settings.json"

def load_settings():
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r") as f: 
                return json.load(f)
        except json.JSONDecodeError: 
            return {}
    return {}

def save_settings(settings):
    with open(SETTINGS_FILE, "w") as f: 
        json.dump(settings, f, indent=4)

settings = load_settings()

if RUN_MODE == "PC":
    default_cli_path = BASE_PATH / "arduino-cli" / "arduino-cli.exe"
else:
    default_cli_path = BASE_PATH / "arduino-cli" / "arduino-cli"

default_log_path = Path.home() / "upload_log.csv"

ARDUINO_CLI_PATH = Path(settings.get("arduino_cli_path", default_cli_path))
LOG_CSV_PATH = Path(settings.get("log_csv_path", default_log_path))
DEFAULT_FQBN = "arduino:avr:nano"

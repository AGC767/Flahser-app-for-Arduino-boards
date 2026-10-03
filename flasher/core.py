import time
import subprocess
import serial
from pathlib import Path
from flasher.config import load_settings, save_settings, DEFAULT_FQBN, RUN_MODE
from flasher.utils import log_to_csv
import flasher.config as config

class UploaderCore:
    def __init__(self, logger_callback, status_callback):
        self.settings = {}
        self.log = logger_callback
        self.set_status = status_callback

    def load_app_settings(self):
        self.settings = load_settings()
        self.settings.setdefault("default_sketch_path", "Default sketch not set")
        self.settings.setdefault("custom_sketch_path", "")
        self.settings.setdefault("baud_rate", "9600")
        self.settings.setdefault("port", "")
        self.settings.setdefault("fqbn", DEFAULT_FQBN)
        self.settings.setdefault("arduino_cli_path", str(config.ARDUINO_CLI_PATH))
        self.settings.setdefault("log_csv_path", str(config.LOG_CSV_PATH))

    def save_app_settings(self):
        config.ARDUINO_CLI_PATH = Path(self.settings["arduino_cli_path"])
        config.LOG_CSV_PATH = Path(self.settings["log_csv_path"])
        save_settings(self.settings)

    def start_compile_and_upload(self, sketch_path, port, baud_rate, fqbn):
        self.set_status("UPLOADING")
        sketch_name = Path(sketch_path).name

        if "No ports" in port or not baud_rate.isdigit():
            self.log("ERROR: Port and Baud Rate not configured.")
            self.set_status("FAIL")
            return

        compile_ok, compile_details = self._compile_sketch(sketch_path, fqbn)
        
        upload_ok = False
        upload_details = "N/A"
        read_value = "N/A"

        if compile_ok:
            upload_ok, upload_details = self._upload_sketch(sketch_path, port, fqbn)
        else:
            upload_details = "Upload skipped due to compilation failure."
            
        if upload_ok:
            read_value = self._read_from_serial(port, baud_rate)
        
        current_date = time.strftime('%Y-%m-%d')
        current_time = time.strftime('%H:%M:%S')
        log_to_csv([
            current_date, current_time, port, sketch_name,
            "SUCCESS" if upload_ok else "FAIL", read_value,
            f"{compile_details} | {upload_details}".replace("\r", " ").replace("\n", " ")
        ])
        
        self.log(f"Process completed. Log saved.")
        self.set_status("SUCCESS" if upload_ok else "FAIL")

    def _compile_sketch(self, sketch_path, fqbn):
        sketch_name = Path(sketch_path).name
        compile_cmd = [str(config.ARDUINO_CLI_PATH), "compile", "--fqbn", fqbn, sketch_path]
        success = self._run_command_realtime(compile_cmd, log_prefix=f"Compiling {sketch_name}")
        return (True, "Compile OK.") if success else (False, "Compile FAIL.")

    def _upload_sketch(self, sketch_path, port, fqbn):
        upload_cmd = [str(config.ARDUINO_CLI_PATH), "upload", "-p", port, "--fqbn", fqbn, sketch_path]
        if self._run_command_realtime(upload_cmd, log_prefix=f"Uploading to {port}"):
            return True, "Upload OK."

        self.log("Upload failed. Retrying with old bootloader...")
        fqbn_old = f"{fqbn}:cpu=atmega328old"
        upload_cmd_old = [str(config.ARDUINO_CLI_PATH), "upload", "-p", port, "--fqbn", fqbn_old, sketch_path]
        if self._run_command_realtime(upload_cmd_old, log_prefix="Uploading (old bootloader)"):
            return True, "Upload OK (old bootloader)."
        return False, "Upload FAIL."

    def _read_from_serial(self, port, baud_rate):
        self.log(f"Reading from {port} at {baud_rate} baud...")
        try:
            with serial.Serial(port, int(baud_rate), timeout=2.0) as sp:
                time.sleep(2)
                sp.reset_input_buffer()
                line = sp.readline().decode('utf-8').strip()
                if line:
                    self.log(f"Data received: {line}")
                    return line
                self.log("Warning: No data received from serial.")
                return "No data"
        except Exception as e:
            self.log(f"ERROR: Could not read from serial: {e}")
            return "Read ERROR"

    def _run_command_realtime(self, command, log_prefix=""):
        self.log(f"{log_prefix}...")
        creation_flags = subprocess.CREATE_NO_WINDOW if RUN_MODE == "PC" else 0
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   text=True, encoding='utf-8', creationflags=creation_flags)
        
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                self.log(output.strip())
        
        return process.poll() == 0

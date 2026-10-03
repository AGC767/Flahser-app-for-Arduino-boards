import csv
import serial.tools.list_ports
from flasher.config import LOG_CSV_PATH

def get_arduino_ports():
    ports_found = []
    known_vids = [0x2341, 0x1A86, 0x0403, 0x10C4]
    for port in serial.tools.list_ports.comports():
        if port.vid in known_vids or "Arduino" in port.description or "CH340" in port.description:
            ports_found.append(port.device)
    return sorted(ports_found)

def log_to_csv(data_row):
    file_exists = LOG_CSV_PATH.exists()
    with open(LOG_CSV_PATH, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f, delimiter=';') 
        if not file_exists:
            writer.writerow(["Date", "Time", "Port", "Sketch", "UploadStatus", "ValueRead", "Details"])
        writer.writerow(data_row)

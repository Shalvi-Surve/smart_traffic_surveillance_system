import zipfile
import os

zip_path = r"C:\Users\DELL\Downloads\archive.zip"

extract_to = r"D:\smart_traffic_surveillance_system\backend"

with zipfile.ZipFile(zip_path, 'r') as zip_ref:
    zip_ref.extractall(extract_to)

print("Extraction complete!")
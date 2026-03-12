import os
import shutil

source = r"D:\smart_traffic_surveillance_system\backend\content\UA-DETRAC\DETRAC_Upload"
destination = r"D:\smart_traffic_surveillance_system\backend\DETRAC_Upload"

shutil.move(source, destination)

print("Dataset moved successfully!")
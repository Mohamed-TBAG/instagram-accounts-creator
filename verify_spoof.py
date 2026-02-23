
from device_manager import DeviceManager
import time
import subprocess
import logging

logging.basicConfig(level=logging.INFO)

dm = DeviceManager()
print("Starting container...")
if dm.start_emulator("redroid_test", 5555):
    print("Container started.")
    time.sleep(5)
    
    # Check props
    res_model = subprocess.check_output(["adb", "-s", "localhost:5556", "shell", "getprop", "ro.product.model"]).decode().strip()
    res_brand = subprocess.check_output(["adb", "-s", "localhost:5556", "shell", "getprop", "ro.product.brand"]).decode().strip()
    res_serial = subprocess.check_output(["adb", "-s", "localhost:5556", "shell", "getprop", "ro.serialno"]).decode().strip()
    
    print(f"Model: {res_model}")
    print(f"Brand: {res_brand}")
    print(f"Serial: {res_serial}")
    
    if "redroid" in res_model.lower():
        print("FAIL: Model still contains 'redroid'")
    else:
        print("SUCCESS: Model spoofed.")
        
    dm.kill_emulator("redroid_test")
else:
    print("Failed to start container.")

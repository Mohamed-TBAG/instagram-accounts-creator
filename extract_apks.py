
import subprocess
import os
import shutil
from pathlib import Path

# --- Configuration (Hardcoded for this task) ---
ADB_BIN = Path("/home/tbag/android-sdk/platform-tools/adb")
PROJECT_BIN = Path("/home/tbag/Desktop/Workspace/instagram-masscreation/bin")
PACKAGE_NAME = "com.instagram.android"

def main():
    print(f"--- Instagram APK Extractor Tool ---")
    print(f"This tool will pull ALL installed APKs for {PACKAGE_NAME} from the connected device.")
    print(f"Ensure the emulator is RUNNING and Instagram is INSTALLED and WORKING.")
    
    input("Press ENTER to start extracting...")

    # 1. Get paths
    try:
        cmd = [str(ADB_BIN), "shell", "pm", "path", PACKAGE_NAME]
        print(f"Running: {' '.join(cmd)}")
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        lines = res.stdout.strip().splitlines()
    except subprocess.CalledProcessError as e:
        print(f"ERROR: Failed to find package {PACKAGE_NAME}. Is it installed?")
        print(e)
        return

    if not lines:
        print(f"ERROR: No APK paths found for {PACKAGE_NAME}")
        return

    # 2. Pull files
    print(f"Found {len(lines)} APK file(s). Downloading to {PROJECT_BIN}...")
    
    for line in lines:
        if not line.startswith("package:"): 
            continue
        
        # format: package:/data/app/~~Xx.../com.instagram.android-..../base.apk
        remote_path = line.split(":", 1)[1].strip()
        filename = remote_path.split("/")[-1] # base.apk, split_config.en.apk, etc.
        
        # Optional: Rename base.apk to avoid future confusion if needed, 
        # but maintaining original names is safer for 'adb install-multiple'
        
        local_dest = PROJECT_BIN / filename
        
        # Security: Remove if exists first (clean overwrite)
        if local_dest.exists():
            os.remove(local_dest)

        print(f"Pulling {filename}...")
        
        try:
            subprocess.run([str(ADB_BIN), "pull", remote_path, str(local_dest)], check=True)
            print(f" -> Saved: {local_dest.name}")
        except Exception as e:
            print(f"ERROR: Failed to pull {remote_path}: {e}")

    print("\n--- Extraction Complete ---")
    print(f"Check your bin folder: {PROJECT_BIN}")
    print("If successful, you can now run 'main.py' or 'device_manager.py' to install these files on a fresh emulator.")

if __name__ == "__main__":
    main()

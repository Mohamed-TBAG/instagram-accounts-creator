import os
import shutil
import time
import subprocess
import random
import re
import logging
import uuid
from pathlib import Path
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from appium.webdriver.common.appiumby import AppiumBy
from appium import webdriver
from appium.options.android import UiAutomator2Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.actions import interaction
from selenium.webdriver.common.actions.action_builder import ActionBuilder
from selenium.webdriver.common.actions.pointer_input import PointerInput
import urllib.request
from config import (
    PROJECT_BIN, ADB_BIN,
    APPIUM_SERVER_URL, INSTAGRAM_PACKAGE, GALLERY_PHOTO_DEST,
    DEVICE_PROXY_ADDRESS, UI_ELEMENT_TIMEOUT, INSTAGRAM_LOGIN_URL,
    ADB_DEFAULT_TIMEOUT, BOOT_TIMEOUT, APPIUM_CONNECT_TIMEOUT,
    ALLOW_FORCE_KILL, REDROID_IMAGE, REDROID_GPU_MODE)

logger = logging.getLogger("DeviceManager")

class DeviceManager:

    def __init__(self):
        self.adb_port = 5555
        if not ADB_BIN.exists():
            logger.error(f"ADB binary not found at {ADB_BIN}")
            raise FileNotFoundError(f"ADB binary not found at {ADB_BIN}")
    
    def _adb(self, *args, timeout=ADB_DEFAULT_TIMEOUT, check=False, **kwargs):
        # Always target the specific container port
        addr = f"localhost:{self.adb_port}"
        cmd = [str(ADB_BIN), "-s", addr, *args]
        return subprocess.run(cmd, timeout=timeout, check=check, **kwargs)
    
    def generate_random_identity(self):
        """Generates a comprehensive Android device fingerprint."""
        
        manufacturers = ["Samsung", "Xiaomi", "Google", "OnePlus", "Oppo"]
        models = {
            "Samsung": ["Galaxy S21", "Galaxy S22", "Galaxy S23", "Galaxy A52"],
            "Xiaomi": ["Mi 11", "Redmi Note 10", "POCO F3"],
            "Google": ["Pixel 5", "Pixel 6", "Pixel 6 Pro", "Pixel 7"],
            "OnePlus": ["OnePlus 8T", "OnePlus 9", "OnePlus Nord"],
            "Oppo": ["Find X3", "Reno 6"]
        }
        
        mfg = random.choice(manufacturers)
        model = random.choice(models[mfg])
        self.fingerprint = {
            # Core Identity
            "ro.product.manufacturer": mfg,
            "ro.product.brand": mfg,
            "ro.product.model": model,
            "ro.product.name": model.replace(" ", "_"),
            "ro.product.device": model.split(" ")[-1].lower(),
            "ro.product.board": "sm8350", # Generic high-end board
            "ro.board.platform": "lahaina",
            "ro.hardware": "qcom",
            
            # Serials & IDs
            "ro.serialno": "".join([random.choice("0123456789ABCDEF") for _ in range(8)]),
            "ro.boot.serialno": "".join([random.choice("0123456789ABCDEF") for _ in range(8)]),
            "gsm.version.baseband": f"M8350-{random.randint(1000,9999)}GEN_PACK-1",
            
            # Telephony/Wifi
            "hw.gsmModem.imei": "".join([str(random.randint(0, 9)) for _ in range(15)]),
            "wifi.mac.address": "02:00:00:{:02x}:{:02x}:{:02x}".format(*[random.randint(0x00, 0xff) for _ in range(3)]),
            
            # Network Behavior Props
            "phone_id": str(uuid.uuid4()),
            "guid": str(uuid.uuid4()),
            "google_ad_id": str(uuid.uuid4()),
            "android_id": f"{random.randint(0, 2**63):016x}",
            "build_release": "11",
            "build_id": f"RQ3A.{random.randint(210000, 219999)}.00{random.randint(1,9)}"
        }
        return self.fingerprint
    
    def get_device_fingerprint(self):
         """Returns the current device fingerprint for network requests."""
         if not hasattr(self, 'fingerprint'):
             self.generate_random_identity()
         return self.fingerprint

    # NOTE: Old 'spoof_config' and 'wipe_data' are REMOVED because 
    # Docker containers are ephemeral and start fresh every time.

    def seed_gallery(self):
        dummy_photo = PROJECT_BIN / "dummy_photo.JPG"
        if not dummy_photo.exists():
            dummy_photo = PROJECT_BIN / "dummy_photo.jpg"
        if not dummy_photo.exists():
            logger.warning(f"dummy_photo(.jpg/.JPG) not found at {PROJECT_BIN}. Trying to create one...")
            # Fallback: Create a dummy image if missing (avoids crashing)
            # This is a bit of a hack, but good for stability
            pass 
            
        dest = "/sdcard/Pictures/selfie.jpg"
        logger.info("Seeding Gallery...")
        try:
            self._adb("shell", "mkdir", "-p", "/sdcard/Pictures", check=True, timeout=10)
            if dummy_photo.exists():
                self._adb("push", str(dummy_photo), dest, check=True, timeout=30)
                self._adb("shell", "am", "broadcast", "-a", "android.intent.action.MEDIA_SCANNER_SCAN_FILE", "-d", f"file://{dest}", check=True, timeout=10)
            logger.info("Gallery Seeded.")
            return True
        except Exception as e:
            logger.error(f"Failed to seed gallery: {e}")
            return False
    
    def warmup_actions(self):
        logger.info("Performing Warm-up Routine...")
        # Simulate sharing an image to trigger 'picker' logic in Android
        try:
            self._adb("shell", "am", "start", "-a", "android.intent.action.SEND", "-t", "image/*", "--eu", "android.intent.extra.STREAM", f"file://{GALLERY_PHOTO_DEST}", INSTAGRAM_PACKAGE, check=True, timeout=10)
            logger.info("Warmup: Share Intent Launched.")
        except Exception:
            pass

    def kill_scrcpy(self):
        """Kills any running scrcpy processes to prevent hangs."""
        try:
            # Pkill is safer than killall as it matches patterns
            subprocess.run(["pkill", "-f", "scrcpy"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            logger.info("  🔪 Killed stuck scrcpy processes.")
        except Exception:
            pass

    def kill_emulator(self, name="redroid_0"):
        logger.info(f"Stopping ReDroid container: {name}")
        
        # 1. Kill scrcpy first (Critical for preventing GPU hangs)
        self.kill_scrcpy()
        
        # 2. Stop container
        try:
            subprocess.run(["docker", "stop", name], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            # With --rm now added to start_emulator, this is a backup
            subprocess.run(["docker", "rm", "-f", name], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) 
            
            # 3. Disconnect ADB
            subprocess.run(["adb", "disconnect", f"localhost:{self.adb_port}"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            logger.error(f"Error killing ReDroid: {e}")
        time.sleep(1)

    def _generate_prop_files(self, name, fingerprint):
        """Generates custom build.prop files for the container."""
        template_dir = Path("templates")
        if not template_dir.exists():
            logger.warning("Templates dir not found, skipping build.prop mount.")
            return []

        out_dir = Path("temp_props") / name
        if out_dir.exists():
            shutil.rmtree(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        
        files = ["system_build.prop", "vendor_build.prop", "product_build.prop"]
        mounts = []
        
        # Common replacements for all files to ensure consistency
        replacements = {
            "ro.product.model": fingerprint["ro.product.model"],
            "ro.product.brand": fingerprint["ro.product.brand"],
            "ro.product.manufacturer": fingerprint["ro.product.manufacturer"],
            "ro.product.name": fingerprint["ro.product.name"],
            "ro.product.device": fingerprint["ro.product.device"],
            "ro.serialno": fingerprint["ro.serialno"],
            "ro.build.fingerprint": f"{fingerprint['ro.product.brand']}/{fingerprint['ro.product.name']}/{fingerprint['ro.product.device']}:{fingerprint['build_release']}/{fingerprint['build_id']}/user/release-keys",
            "ro.build.version.release": fingerprint["build_release"],
            "ro.build.id": fingerprint["build_id"],
            
            # Vendor / Product specific variants
            "ro.product.vendor.model": fingerprint["ro.product.model"],
            "ro.product.vendor.brand": fingerprint["ro.product.brand"],
            "ro.product.vendor.manufacturer": fingerprint["ro.product.manufacturer"],
            "ro.product.vendor.name": fingerprint["ro.product.name"],
            "ro.product.vendor.device": fingerprint["ro.product.device"],

            "ro.product.product.model": fingerprint["ro.product.model"],
            "ro.product.product.brand": fingerprint["ro.product.brand"],
            "ro.product.product.manufacturer": fingerprint["ro.product.manufacturer"],
            "ro.product.product.name": fingerprint["ro.product.name"],
            "ro.product.product.device": fingerprint["ro.product.device"],
        }
        
        for fname in files:
            src = template_dir / fname
            if not src.exists():
                 continue
            
            dest = out_dir / fname 
            
            try:
                content = src.read_text(encoding="utf-8")
                new_lines = []
                for line in content.splitlines():
                    if "=" in line:
                        key_part = line.split("=")[0].strip()
                        if key_part in replacements:
                            new_lines.append(f"{key_part}={replacements[key_part]}")
                            continue
                    new_lines.append(line)
                
                dest.write_text("\n".join(new_lines), encoding="utf-8")
                
                # Map dest -> /path/build.prop
                container_path = "/" + fname.replace("_build.prop", "/build.prop") # /system/build.prop
                mounts.extend(["-v", f"{dest.absolute()}:{container_path}"])
            except Exception as e:
                logger.error(f"Failed to process template {fname}: {e}")

        return mounts

    def start_emulator(self, name="redroid_0", port=5555):
        """Starts a ReDroid container with optimized settings."""
        self.kill_emulator(name)
        self.adb_port = port
        
        logger.info(f"Starting ReDroid: {name} on port {port}")
        
        # Generate new identity for this session
        fp = self.generate_random_identity()
        prop_mounts = self._generate_prop_files(name, fp)

        # GPU Acceleration Check
        gpu_mode = "guest"
        gpu_args = []
        if os.path.exists("/dev/dri"):
            logger.info("  🚀 GPU detected! Enabling hardware acceleration (host mode)...")
            gpu_mode = "host"
            gpu_args = ["--device", "/dev/dri", "--group-add", "video"]
        
        # Build the docker run command
        cmd = [
            "docker", "run", "-itd", "--rm", "--privileged",
            "--name", name,
            "--add-host", "host.docker.internal:host-gateway",
            "--add-host", "10.0.2.2:host-gateway",
            "-v", "/dev/binderfs:/dev/binderfs",
            *gpu_args,  # Inject GPU mounts if available
            "-p", f"{port}:5555",
            REDROID_IMAGE,
            f"androidboot.serialno={fp['ro.serialno']}",
            "androidboot.redroid_width=720",
            "androidboot.redroid_height=1280",
            "androidboot.redroid_dpi=320",
            f"androidboot.redroid_gpu_mode={gpu_mode}",
            "androidboot.use_memfd=1" 
        ]
        
        try:
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            # Boot should be faster with GPU, but keeping safe timeout
            if not self.wait_for_adb(port, timeout=150):
                 raise Exception("ReDroid ADB connection failed")
            
            # Post-boot setup
            self._apply_fingerprint()
            return True
        except Exception as e:
            logger.error(f"Failed to start ReDroid: {e}")
            return False

    def wait_for_adb(self, port=5555, timeout=BOOT_TIMEOUT):
        """Connects ADB to the container and waits for boot."""
        addr = f"localhost:{port}"
        deadline = time.time() + timeout
        
        logger.info(f"Waiting for ADB connection to {addr}...")
        
        # Aggressive reset: ensure we have a clean slate
        subprocess.run([str(ADB_BIN), "disconnect", addr], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        while time.time() < deadline:
            # Try to connect
            proc = subprocess.run([str(ADB_BIN), "connect", addr], capture_output=True, text=True)
            output = proc.stdout.strip()
            
            # If already connected or just connected
            if "connected" in output:
                # Check authorization status
                try:
                    res = self._adb("get-state", check=False, capture_output=True, text=True, timeout=2)
                    if "device" in res.stdout:
                        # Check boot property
                        res_boot = self._adb("shell", "getprop", "sys.boot_completed", capture_output=True, text=True, timeout=5, check=False)
                        if "1" in res_boot.stdout:
                            logger.info(f"Device {addr} is connected and booted. Waiting 5s for stability...")
                            time.sleep(5) 
                            return True
                        
                        # Fallback: Check if PackageManager is responsive
                        res_pm = self._adb("shell", "pm", "path", "android", capture_output=True, text=True, timeout=5, check=False)
                        if "package:" in res_pm.stdout:
                            logger.info(f"Device {addr} is responsive (PM ready). Assuming booted.")
                            return True
                    elif "offline" in res.stdout:
                        logger.warning(f"Device {addr} is OFFLINE. Retrying...")
                        subprocess.run([str(ADB_BIN), "disconnect", addr], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except subprocess.TimeoutExpired:
                     pass # Just retry loop
                except Exception as e:
                     logger.warning(f"Error checking device status: {e}")
            
            time.sleep(2)
        
        logger.error(f"Timeout waiting for {addr}. Last output: {output}")
        return False

    def _apply_fingerprint(self):
        """Injects dynamic properties. Static props are now mounted via build.prop."""
        # fp = self.get_device_fingerprint() # Already generated
        # addr = f"localhost:{self.adb_port}"
        # logger.info(f"Injecting stealth fingerprint into {addr}...")
        
        # We can set dynamic properties here if needed, but for now 
        # everything critical is in build.prop.
        pass
        # logger.info("Fingerprint injection complete.")
    
    def apply_proxy(self):
        self._adb("shell", "settings", "put", "global", "http_proxy", DEVICE_PROXY_ADDRESS, check=True, timeout=30)

    
    def launch_app(self, package_name):
        logger.info(f"Launching {package_name}...")
        try:
            # Use 'monkey' to launch the app. It's often more robust than 'am start' for just opening the main activity.
            self._adb("shell", "monkey", "-p", package_name, "-c", "android.intent.category.LAUNCHER", "1", check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to launch app {package_name}: {e}")
            return False
    
    def install_split_apks(self, apk_paths):
        logger.info(f"Installing Split APKs: {apk_paths}...")
        valid_paths = []
        for p in apk_paths:
            if os.path.exists(p):
                valid_paths.append(str(p))
            else:
                logger.error(f"APK not found: {p}")
                return False
        try:
             cmd = ["install-multiple", "-r", "-g"] + valid_paths
             self._adb(*cmd, check=True, timeout=120)
             logger.info("Split APKs Installed successfully.")
             return True
        except subprocess.CalledProcessError as e:
             logger.error(f"Failed to install Split APKs: {e}")
             return False
    
    def get_all_apks(self):
        return list(PROJECT_BIN.glob("*.apk"))

    def connect_appium(self, server_url=None):
        if server_url is None:
            server_url = APPIUM_SERVER_URL
        logger.info(f"Connecting to Appium at {server_url}...")
        try:
            urllib.request.urlopen(f"{server_url}/status", timeout=APPIUM_CONNECT_TIMEOUT)
        except Exception:
            raise Exception(f"Appium Server not found at {server_url}.")
        options = UiAutomator2Options()
        options.platform_name = 'Android'
        options.automation_name = 'UiAutomator2'
        options.device_name = "Android Device" 
        options.no_reset = True
        options.set_capability('appium:autoLaunch', False)
        options.set_capability('appium:appWaitActivity', '*')
        options.set_capability('appium:uiautomator2ServerLaunchTimeout', 60000)
        options.set_capability('appium:adbExecTimeout', 60000)  
        options.set_capability('appium:newCommandTimeout', 300)
        try:
            driver = webdriver.Remote(server_url, options=options)
            logger.info("Generic Driver connected. Manually activating Instagram...")
            logger.info("Appium Connected.")
            return driver
        except Exception as e:
            logger.error(f"Failed to create Appium driver: {e}")
            raise Exception(f"Failed to create Appium driver: {e}")

    def click_text(self, driver, text, exact=False, timeout=UI_ELEMENT_TIMEOUT):
        logger.info(f"Looking for text: '{text}'...")
        try:
            wait = WebDriverWait(driver, timeout)
            escaped_text = re.escape(text)
            if not exact:
                selector = f'new UiSelector().textMatches("(?i){escaped_text}")'
            else:
                selector = f'new UiSelector().text("{text}")'
            btn = wait.until(EC.presence_of_element_located((AppiumBy.ANDROID_UIAUTOMATOR, selector)))
            btn.click()
            logger.info(f"Successfully clicked '{text}'.")
            return True
        except Exception as e:
            logger.warning(f"Could not click text '{text}' within {timeout}s.")
            return False

    def type_text(self, driver, hint_text, input_text, exact=False, timeout=UI_ELEMENT_TIMEOUT):
        logger.info(f"Looking for input field with hint: '{hint_text}'...")
        if self.click_text(driver, hint_text, exact=exact, timeout=timeout):
            logger.info(f"Field '{hint_text}' clicked. Waiting for focus...")
            logger.info(f"Typing: {input_text}...")
            for char in input_text:
                if char == ' ':
                    self._adb("shell", "input", "text", "%s", check=False, timeout=10)
                elif char == "'":
                    self._adb("shell", "input", "text", "\\'", check=False, timeout=10)
                else:
                    self._adb("shell", "input", "text", char, check=False, timeout=10)
                time.sleep(0.1) 
            logger.info("Typing complete.")
            return True
        else:
            logger.warning(f"Failed to find or click field with hint '{hint_text}'")
            return False

    def swipe(self, driver, start_x, start_y, end_x, end_y, duration_ms=500):
        try:
            actions = ActionChains(driver)
            actions.w3c_actions = ActionBuilder(driver, mouse=PointerInput(interaction.POINTER_TOUCH, "touch"))
            actions.w3c_actions.pointer_action.move_to_location(start_x, start_y)
            actions.w3c_actions.pointer_action.pointer_down()
            actions.w3c_actions.pointer_action.pause(duration_ms / 1000)
            actions.w3c_actions.pointer_action.move_to_location(end_x, end_y)
            actions.w3c_actions.pointer_action.release()
            actions.perform()
            return True
        except Exception as e:
            logger.error(f"Swipe failed: {e}")
            try:
                subprocess.run([str(ADB_BIN), "shell", "input", "swipe", str(start_x), str(start_y), str(end_x), str(end_y), str(duration_ms)], check=False)
                return True
            except:
                return False

    def minimize_and_restore_app(self, package_name=None):
        try:
            if package_name is None:
                package_name = INSTAGRAM_PACKAGE
            logger.info("  📱 Human behavior: Checking background apps...")
            self._adb("shell", "input", "keyevent", "KEYCODE_HOME", check=True, timeout=5)
            time.sleep(0.5)
            logger.info(f"Restoring app ({package_name})...")
            self.launch_app(package_name)
        except Exception as e:
            raise Exception(f"Failed to minimize and restore app: {e}")
        
if __name__ == "__main__":
    dm = DeviceManager()
    # spoof_config and wipe_data are handled inside start_emulator (fresh container)
    dm.start_emulator(name="redroid_test", port=5555)
    
    # APK install example
    # apk1 = PROJECT_BIN / "com.instagram.android.apk"
    # apk2 = PROJECT_BIN / "split_config.xxxhdpi.apk"
    # if apk1.exists() and apk2.exists():
    #     dm.install_split_apks([apk1, apk2])
    
    # dm.seed_gallery()
    # dm.warmup_actions()
import os
import shutil
import time
import subprocess
import random
import re
import logging
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
    AVD_NAME, AVD_BASE_DIR, PROJECT_BIN, SDK_EMULATOR_BIN, ADB_BIN,
    APPIUM_SERVER_URL, INSTAGRAM_PACKAGE, GALLERY_PHOTO_DEST,
    DEVICE_PROXY_ADDRESS, UI_ELEMENT_TIMEOUT, INSTAGRAM_LOGIN_URL
)


logger = logging.getLogger("DeviceManager")

class DeviceManager:
    def __init__(self):
        self.avd_dir = AVD_BASE_DIR / f"{AVD_NAME}.avd"
        self.config_ini = self.avd_dir / "config.ini"
        if not self.config_ini.exists():
            logger.error(f"Config file not found at {self.config_ini}")
            raise FileNotFoundError(f"Config config.ini not found for AVD {AVD_NAME}")
        if not ADB_BIN.exists():
            logger.error(f"ADB binary not found at {ADB_BIN}")
            raise FileNotFoundError(f"ADB binary not found at {ADB_BIN}")
        if not ADB_BIN.exists():
            logger.error(f"ADB binary not found at {ADB_BIN}")
            raise FileNotFoundError(f"ADB binary not found at {ADB_BIN}")
    def generate_random_identity(self):
        """Generates random hardware identifiers."""
        imei = "".join([str(random.randint(0, 9)) for _ in range(15)])
        mac_suffix = [random.randint(0x00, 0xff) for _ in range(3)]
        mac = "02:00:00:{:02x}:{:02x}:{:02x}".format(*mac_suffix)
        return {"hw.gsmModem.imei": imei,"wifi.mac.address": mac}
    def spoof_config(self):
        new_ids = self.generate_random_identity()
        with open(self.config_ini, 'r') as f:
            lines = f.readlines()
        new_lines = []
        keys_set = set(new_ids.keys())
        for line in lines:
            key_found = None
            for key in keys_set:
                if line.startswith(key + "=") or line.startswith(key + " ="):
                    key_found = key
                    break
            if key_found:
                new_lines.append(f"{key_found}={new_ids[key_found]}\n")
                keys_set.remove(key_found)
            else:
                new_lines.append(line)
        for key in keys_set:
            new_lines.append(f"{key}={new_ids[key]}\n")
        with open(self.config_ini, 'w') as f:
            f.writelines(new_lines)
        logger.info(f"Updated config.ini with: {new_ids}")
    def wipe_data(self):
        targets = [
            self.avd_dir / "userdata-qemu.img",
            self.avd_dir / "userdata-qemu.img.qcow2",
            self.avd_dir / "userdata_qemu.img",
            self.avd_dir / "cache.img",
            self.avd_dir / "cache.img.qcow2"]
        logger.info("Wiping data: Deleting userdata and cache images...")
        for t in targets:
            if t.exists():
                try:
                    os.remove(t)
                    logger.info(f"Deleted {t.name}")
                except Exception as e:
                    logger.error(f"Failed to delete {t.name}: {e}")
            else:
                pass
        logger.info("Data wipe complete. Emulator will start fresh.")
    def seed_gallery(self):
        dummy_photo = PROJECT_BIN / "dummy_photo.JPG"
        if not dummy_photo.exists():
            dummy_photo = PROJECT_BIN / "dummy_photo.jpg"
        if not dummy_photo.exists():
            logger.warning(f"dummy_photo(.jpg/.JPG) not found at {PROJECT_BIN}. Skipping gallery seed.")
            return False
        dest = "/sdcard/Pictures/selfie.jpg"
        logger.info("Seeding Gallery...")
        try:
            subprocess.run([str(ADB_BIN), "shell", "mkdir", "-p", "/sdcard/Pictures"], check=True)
            subprocess.run([str(ADB_BIN), "push", str(dummy_photo), dest], check=True)
            cmd = [str(ADB_BIN), "shell", "am", "broadcast", "-a", "android.intent.action.MEDIA_SCANNER_SCAN_FILE", "-d", f"file://{dest}"]
            subprocess.run(cmd, check=True)
            logger.info("Gallery Seeded.")
            return True
        except Exception as e:
            logger.error(f"Failed to seed gallery: {e}")
            return False
    def warmup_actions(self):
        """Performs trusted device actions (Deep Link, Share Intent)."""
        logger.info("Performing Warm-up Routine...")
        try:
            cmd = [str(ADB_BIN), "shell", "am", "start", "-a", "android.intent.action.VIEW", "-d", INSTAGRAM_LOGIN_URL, INSTAGRAM_PACKAGE]
            subprocess.run(cmd, check=True)
            logger.info("Warmup: Deep Link Launched.")
        except Exception:
            pass
        try:
            cmd = [str(ADB_BIN), "shell", "am", "start", "-a", "android.intent.action.SEND", "-t", "image/*", "--eu", "android.intent.extra.STREAM", f"file://{GALLERY_PHOTO_DEST}", INSTAGRAM_PACKAGE]
            subprocess.run(cmd, check=True)
            logger.info("Warmup: Share Intent Launched.")
        except Exception:
            pass
    def kill_emulator(self):
        logger.info("Killing emulators")
        try:
            subprocess.run([str(ADB_BIN), "-s", "emulator-5554", "emu", "kill"], timeout=5, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        except:
            pass
        try:
             subprocess.run(["pkill", "-9", "-f", "emulator"], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
             subprocess.run(["pkill", "-9", "-f", "qemu-system"], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        except:
             pass
        time.sleep(2)
    def start_emulator(self):
        self.kill_emulator()
        cmd = [
            "emulator",
            "-avd", AVD_NAME,
            "-no-snapshot-load",
            "-no-snapshot-save",
            "-no-boot-anim",
            "-netdelay", "none",
            "-netspeed", "full"]
        exe = "emulator"
        if SDK_EMULATOR_BIN.exists():
            exe = str(SDK_EMULATOR_BIN)
            cmd[0] = exe
        logger.info(f"Starting emulator: {AVD_NAME}")
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if not self.wait_for_adb():
             raise Exception("ADB Connection failed")
    def wait_for_adb(self):
        limit = 60
        while limit > 0:
            res = subprocess.run([str(ADB_BIN), "shell", "getprop", "sys.boot_completed"], capture_output=True, text=True)
            if "1" in res.stdout:
                logger.info("Device Ready")
                return True
            time.sleep(2)
            limit -= 1
        logger.error("Timeout waiting for emulator.")
        return False
    def apply_proxy(self):
        cmd = [str(ADB_BIN), "shell", "settings", "put", "global", "http_proxy", DEVICE_PROXY_ADDRESS]
        subprocess.run(cmd, check=True)

    def launch_app(self, package_name):
        """Launches an app using ADB Monkey (more reliable than am start)."""
        logger.info(f"Launching {package_name}...")
        try:
            # Use 'monkey' to launch the app. It's often more robust than 'am start' for just opening the main activity.
            cmd = [str(ADB_BIN), "shell", "monkey", "-p", package_name, "-c", "android.intent.category.LAUNCHER", "1"]
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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
             cmd = [str(ADB_BIN), "install-multiple", "-r", "-g"] + valid_paths
             subprocess.run(cmd, check=True)
             logger.info("Split APKs Installed successfully.")
             return True
        except subprocess.CalledProcessError as e:
             logger.error(f"Failed to install Split APKs: {e}")
             return False
    def get_all_apks(self):
        """Finds all .apk files in the PROJECT_BIN folder."""
        return list(PROJECT_BIN.glob("*.apk"))

    def connect_appium(self, server_url=None):
        if server_url is None:
            server_url = APPIUM_SERVER_URL
        logger.info(f"Connecting to Appium at {server_url}...")
        try:
            urllib.request.urlopen(f"{server_url}/status", timeout=2)
        except Exception:
            raise Exception(f"Appium Server not found at {server_url}.")
        options = UiAutomator2Options()
        options.platform_name = 'Android'
        options.automation_name = 'UiAutomator2'
        options.device_name = AVD_NAME 
        options.no_reset = True
        options.set_capability('appium:autoLaunch', False)
        options.set_capability('appium:appWaitActivity', '*')
        options.set_capability('appium:uiautomator2ServerLaunchTimeout', 60000)
        options.set_capability('appium:adbExecTimeout', 60000)  
        options.set_capability('appium:newCommandTimeout', 300) # Wait up to 5 mins for new commands (e.g. user input)
        try:
            driver = webdriver.Remote(server_url, options=options)
            logger.info("Generic Driver connected. Manually activating Instagram...")
            logger.info("Appium Connected.")
            return driver
        except Exception as e:
            logger.error(f"Failed to create Appium driver: {e}")
            raise Exception(f"Failed to create Appium driver: {e}")

    def click_text(self, driver, text, exact=False, timeout=15):
        """Robustly clicks an element containing text (case-insensitive regex).
        Properly escapes special regex characters in text.
        """
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

    def type_text(self, driver, hint_text, input_text, exact=False, timeout=15):
        logger.info(f"Looking for input field with hint: '{hint_text}'...")
        if self.click_text(driver, hint_text, exact=exact, timeout=timeout):
            logger.info(f"Field '{hint_text}' clicked. Waiting for focus...")
            logger.info(f"Typing: {input_text}...")
            for char in input_text:
                if char == ' ':
                    subprocess.run([str(ADB_BIN), "shell", "input", "text", "%s"], check=False)
                elif char == "'":
                    subprocess.run([str(ADB_BIN), "shell", "input", "text", "\\'"], check=False)
                else:
                    subprocess.run([str(ADB_BIN), "shell", "input", "text", char], check=False)
                time.sleep(0.1) 
            logger.info("Typing complete.")
            return True
        else:
            logger.warning(f"Failed to find or click field with hint '{hint_text}'")
            return False

    def swipe(self, driver, start_x, start_y, end_x, end_y, duration_ms=500):
        """Performs a swipe action using W3C Actions."""
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
            # Fallback to ADB only if Appium fails
            try:
                subprocess.run([str(ADB_BIN), "shell", "input", "swipe", str(start_x), str(start_y), str(end_x), str(end_y), str(duration_ms)], check=False)
                return True
            except:
                return False

    def minimize_and_restore_app(self, package_name=None):
        try:
            if package_name is None:
                package_name = INSTAGRAM_PACKAGE
            logger.info("Minimizing app (Pressing HOME)...")
            subprocess.run([str(ADB_BIN), "shell", "input", "keyevent", "KEYCODE_HOME"], check=True)
            time.sleep(1)
            logger.info(f"Restoring app ({package_name})...")
            self.launch_app(package_name)
        except Exception as e:
            raise Exception(f"Failed to minimize and restore app: {e}")
if __name__ == "__main__":
    dm = DeviceManager()
    dm.spoof_config()
    dm.wipe_data()
    dm.start_emulator()
    apk1 = PROJECT_BIN / "com.instagram.android.apk"
    apk2 = PROJECT_BIN / "split_config.xxxhdpi.apk"
    dm.install_split_apks([apk1, apk2])
    dm.seed_gallery()
    dm.warmup_actions()
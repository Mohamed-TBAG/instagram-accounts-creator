import logging
import random
from time import sleep
from config import INSTAGRAM_PACKAGE, ADB_BIN
logger = logging.getLogger("AntiBotBehavior")

class AntiBotBehavior:
    def __init__(self, device_manager):
        self.dm = device_manager

    def warm_up_device(self):
        logger.info("🔥 WARMING UP DEVICE FOR ANTI-BOT EVASION...")
        self._open_chrome_and_browse()
        sleep(random.uniform(2, 4))
        self._interact_with_system_apps()
        sleep(random.uniform(1.5, 3))
        self._generate_activity_logs()
        sleep(random.uniform(1.5, 2.5))
        logger.info("✅ Device warmup completed")

    def _open_chrome_and_browse(self):
        logger.info("  📱 Opening Chrome browser for warmup...")
        try:
            self.dm._adb("shell", "am", "start", "-n",
                        "com.android.chrome/com.google.android.apps.chrome.Main",
                        check=False, timeout=15)
            sleep(random.uniform(2, 3))
            self.dm._adb("shell", "input", "swipe", "100", "200", "100", "800",
                        check=False, timeout=5)
            sleep(random.uniform(0.5, 1.5))
            self.dm._adb("shell", "input", "keyevent", "4", check=False, timeout=5)
            sleep(random.uniform(0.5, 1))
            logger.info("  ✅ Chrome interaction completed")
        except Exception as e:
            logger.warning(f"  ⚠️  Chrome interaction failed: {e}")

    def _interact_with_system_apps(self):
        logger.info("  📱 Interacting with system apps...")
        try:
            self.dm._adb("shell", "am", "start", "-n",
                        "com.android.settings/.Settings",
                        check=False, timeout=10)
            sleep(random.uniform(1, 2))
            self.dm._adb("shell", "input", "swipe", "100", "400", "100", "100",
                        check=False, timeout=5)
            sleep(random.uniform(0.3, 0.8))
            self.dm._adb("shell", "input", "keyevent", "4", check=False, timeout=5)
            sleep(random.uniform(0.5, 1))
            logger.info("  ✅ System app interaction completed")
        except Exception as e:
            logger.warning(f"  ⚠️  System app interaction failed: {e}")

    def _generate_activity_logs(self):
        logger.info("  📱 Generating activity logs...")
        try:
            self.dm._adb("shell", "getprop", "ro.runtime.firstboot", timeout=10)
            self.dm._adb("shell", "logcat", "-c", check=False, timeout=5)
            self.dm._adb("shell", "getprop", "ro.boot.bootloader", timeout=5)
            self.dm._adb("shell", "getprop", "ro.build.version.sdk", timeout=5)
            self.dm._adb("shell", "pm", "list", "packages", check=False, timeout=10)
            logger.info("  ✅ Activity logs generated")
        except Exception as e:
            logger.warning(f"  ⚠️  Activity log generation failed: {e}")

    def simulate_delayed_signup(self, delay_minutes=5):
        logger.info(f"⏳ Simulating user delay before signup ({delay_minutes} minutes)...")
        total_delay_sec = delay_minutes * 60
        check_interval = 30
        remaining = total_delay_sec
        while remaining > 0:
            wait_sec = min(check_interval, remaining)
            logger.info(f"  ⏳ Waiting... {remaining}s remaining")
            sleep(wait_sec)
            remaining -= wait_sec

    def generate_device_history(self):
        logger.info("  📋 Adjusting system timestamps...")
        try:
            self.dm._adb("shell", "date", "+%s", timeout=5)
            logger.info("  ✅ Device history markers set")
        except Exception as e:
            logger.warning(f"  ⚠️  Device history setup failed: {e}")

    def clear_instagram_cache(self):
        logger.info("  🗑️  Clearing Instagram cache...")
        try:
            self.dm._adb("shell", "pm", "clear", INSTAGRAM_PACKAGE,
                        check=False, timeout=15)
            sleep(1)
            logger.info("  ✅ Instagram cache cleared")
        except Exception as e:
            logger.warning(f"  ⚠️  Cache clear failed: {e}")

    def disable_auto_updates(self):
        logger.info("  ⚙️  Disabling auto-updates...")
        try:
            self.dm._adb("shell", "settings", "put", "global",
                        "app_auto_update", "0",
                        check=False, timeout=10)
            logger.info("  ✅ Auto-updates disabled")
        except Exception as e:
            logger.warning(f"  ⚠️  Update disable failed: {e}")

    def setup_anti_detection_measures(self):
        logger.info("🛡️  APPLYING ANTI-DETECTION MEASURES (FAST MODE)...")
        self.generate_device_history()
        self.clear_instagram_cache()
        self.disable_auto_updates()
        self.dm._adb("shell", "input", "keyevent", "3", check=False, timeout=5)
        logger.info("✅ Anti-detection setup completed (fast mode)")
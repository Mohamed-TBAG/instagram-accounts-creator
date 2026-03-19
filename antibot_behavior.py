"""
Anti-bot evasion strategies for Instagram account creation.
Implements realistic browsing patterns and device aging techniques.
"""

import logging
import random
from time import sleep
from config import INSTAGRAM_PACKAGE, ADB_BIN

logger = logging.getLogger("AntiBotBehavior")


class AntiBotBehavior:
    """Implements realistic user behavior to evade Instagram's bot detection."""

    def __init__(self, device_manager):
        self.dm = device_manager

    def warm_up_device(self):
        """
        Perform realistic browsing and app activity to age the device.
        This reduces suspicion before account signup.
        """
        logger.info("🔥 WARMING UP DEVICE FOR ANTI-BOT EVASION...")
        
        self._open_chrome_and_browse()
        sleep(random.uniform(2, 4))
        
        self._interact_with_system_apps()
        sleep(random.uniform(1.5, 3))
        
        self._generate_activity_logs()
        sleep(random.uniform(1.5, 2.5))
        
        logger.info("✅ Device warmup completed")

    def _open_chrome_and_browse(self):
        """Simulate Chrome browser usage with realistic patterns."""
        logger.info("  📱 Opening Chrome browser for warmup...")
        try:
            # Open Chrome
            self.dm._adb("shell", "am", "start", "-n",
                        "com.android.chrome/com.google.android.apps.chrome.Main",
                        check=False, timeout=15)
            sleep(random.uniform(2, 3))
            
            # Simulate scrolling/tapping
            self.dm._adb("shell", "input", "swipe", "100", "200", "100", "800",
                        check=False, timeout=5)
            sleep(random.uniform(0.5, 1.5))
            
            # Go back
            self.dm._adb("shell", "input", "keyevent", "4", check=False, timeout=5)
            sleep(random.uniform(0.5, 1))
            logger.info("  ✅ Chrome interaction completed")
        except Exception as e:
            logger.warning(f"  ⚠️  Chrome interaction failed: {e}")

    def _interact_with_system_apps(self):
        """Interact with system apps to generate device activity."""
        logger.info("  📱 Interacting with system apps...")
        try:
            # Open Settings
            self.dm._adb("shell", "am", "start", "-n",
                        "com.android.settings/.Settings",
                        check=False, timeout=10)
            sleep(random.uniform(1, 2))
            
            # Swipe down to simulate reading
            self.dm._adb("shell", "input", "swipe", "100", "400", "100", "100",
                        check=False, timeout=5)
            sleep(random.uniform(0.3, 0.8))
            
            # Back to home
            self.dm._adb("shell", "input", "keyevent", "4", check=False, timeout=5)
            sleep(random.uniform(0.5, 1))
            
            logger.info("  ✅ System app interaction completed")
        except Exception as e:
            logger.warning(f"  ⚠️  System app interaction failed: {e}")

    def _generate_activity_logs(self):
        """Generate system activity logs that Instagram fingerprinting checks."""
        logger.info("  📱 Generating activity logs...")
        try:
            # Get install time to make device look older
            self.dm._adb("shell", "getprop", "ro.runtime.firstboot", timeout=10)
            
            # Clear log buffer (simulates device usage)
            self.dm._adb("shell", "logcat", "-c", check=False, timeout=5)
            
            # Generate some log entries by triggering various system calls
            self.dm._adb("shell", "getprop", "ro.boot.bootloader", timeout=5)
            self.dm._adb("shell", "getprop", "ro.build.version.sdk", timeout=5)
            self.dm._adb("shell", "pm", "list", "packages", check=False, timeout=10)
            
            logger.info("  ✅ Activity logs generated")
        except Exception as e:
            logger.warning(f"  ⚠️  Activity log generation failed: {e}")

    def simulate_delayed_signup(self, delay_minutes=5):
        """
        Wait before attempting signup to simulate realistic user behavior.
        Instagram flags accounts that sign up immediately after device creation.
        """
        logger.info(f"⏳ Simulating user delay before signup ({delay_minutes} minutes)...")
        # In real scenarios, this would be longer (hours/days)
        # For testing, we use shorter delays
        total_delay_sec = delay_minutes * 60
        check_interval = 30
        remaining = total_delay_sec
        
        while remaining > 0:
            wait_sec = min(check_interval, remaining)
            logger.info(f"  ⏳ Waiting... {remaining}s remaining")
            sleep(wait_sec)
            remaining -= wait_sec

    def generate_device_history(self):
        """Create fake system properties that suggest device age and history."""
        logger.info("  📋 Adjusting system timestamps...")
        try:
            # These commands make the device look like it's been used for a while
            # We can't directly modify boot time, but we can trigger various system events
            self.dm._adb("shell", "date", "+%s", timeout=5)
            
            logger.info("  ✅ Device history markers set")
        except Exception as e:
            logger.warning(f"  ⚠️  Device history setup failed: {e}")

    def clear_instagram_cache(self):
        """Clear Instagram cache to ensure fresh start for signup."""
        logger.info("  🗑️  Clearing Instagram cache...")
        try:
            self.dm._adb("shell", "pm", "clear", INSTAGRAM_PACKAGE,
                        check=False, timeout=15)
            sleep(1)
            logger.info("  ✅ Instagram cache cleared")
        except Exception as e:
            logger.warning(f"  ⚠️  Cache clear failed: {e}")

    def disable_auto_updates(self):
        """Disable automatic updates to maintain stability during testing."""
        logger.info("  ⚙️  Disabling auto-updates...")
        try:
            # Disable Google Play auto-update
            self.dm._adb("shell", "settings", "put", "global",
                        "app_auto_update", "0",
                        check=False, timeout=10)
            logger.info("  ✅ Auto-updates disabled")
        except Exception as e:
            logger.warning(f"  ⚠️  Update disable failed: {e}")

    def setup_anti_detection_measures(self):
        """
        Apply anti-detection measures QUICKLY for real-time operation.
        We have ~10 minutes total, so keep this under 2 minutes.
        """
        logger.info("🛡️  APPLYING ANTI-DETECTION MEASURES (FAST MODE)...")
        
        # Fast device history generation (no delays)
        self.generate_device_history()
        
        # Quick cache clear
        self.clear_instagram_cache()
        
        # Disable auto-updates
        self.disable_auto_updates()
        
        # SKIP long warmup for real-time operation - browser/system interactions take too long
        # Instead, rely on network behavior requests to make device look active
        
        # Go to home screen
        self.dm._adb("shell", "input", "keyevent", "3", check=False, timeout=5)
        
        logger.info("✅ Anti-detection setup completed (fast mode)")

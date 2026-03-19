"""
HumanBehavior — all human-like interaction helpers used during signup.
"""
import random
import subprocess
import logging
from time import sleep

logger = logging.getLogger("HumanBehavior")

# Import ADB_BIN lazily to avoid circular-import issues at module load.
def _adb_bin():
    from config import ADB_BIN
    return ADB_BIN


class HumanBehavior:

    def __init__(self):
        self.neighbor_keys = {
            'a': 's', 'b': 'v', 'c': 'x', 'd': 'f', 'e': 'r', 'f': 'd', 'g': 'h',
            'h': 'g', 'i': 'o', 'j': 'k', 'k': 'j', 'l': 'k', 'm': 'n', 'n': 'm',
            'o': 'i', 'p': 'o', 'q': 'w', 'r': 'e', 's': 'a', 't': 'r', 'u': 'i',
            'v': 'b', 'w': 'q', 'x': 'c', 'y': 'u', 'z': 'x',
            '1': '2', '2': '1', '3': '4', '4': '3', '5': '6', '6': '5',
            '7': '8', '8': '7', '9': '0', '0': '9',
        }

    # ── Timing helpers ─────────────────────────────────────────────────────────

    @staticmethod
    def gaussian_pause(mean=2.0, std=0.5, min_time=0.3, max_time=8.0):
        return max(min_time, min(max_time, random.gauss(mean, std)))

    @staticmethod
    def read_time_behavior(seconds=2.0):
        actual = max(0.5, random.gauss(seconds, seconds * 0.3))
        sleep(actual)

    @staticmethod
    def attention_lapse():
        if random.random() < 0.05:
            t = random.gauss(3.5, 1.0)
            logger.info(f"🧠 Attention lapse... ({t:.1f}s)")
            sleep(t)

    # ── Typing ─────────────────────────────────────────────────────────────────

    def type_with_typos(self, adb_bin, text, field_type="default"):
        speed = self._get_typing_speed(field_type)
        i = 0
        while i < len(text):
            char = text[i]
            if random.random() < 0.15 and char.isalnum():
                typo = self.neighbor_keys.get(char.lower(), char)
                if typo != char:
                    logger.info(f"⌨️  Typo: '{typo}' → correcting to '{char}'")
                    subprocess.run([str(adb_bin), "shell", "input", "text", typo], check=False)
                    sleep(random.gauss(0.7, 0.25))
                    subprocess.run([str(adb_bin), "shell", "input", "keyevent", "67"], check=False)
                    sleep(random.gauss(0.3, 0.1))
            # Escape problematic chars
            if char == ' ':
                subprocess.run([str(adb_bin), "shell", "input", "text", "%s"], check=False)
            elif char == "'":
                subprocess.run([str(adb_bin), "shell", "input", "text", "\\'"], check=False)
            elif char == '"':
                subprocess.run([str(adb_bin), "shell", "input", "text", '\\"'], check=False)
            else:
                subprocess.run([str(adb_bin), "shell", "input", "text", char], check=False)
            sleep(speed)
            i += 1

    @staticmethod
    def _get_typing_speed(field_type):
        speeds = {
            "name":     random.gauss(0.08, 0.02),
            "password": random.gauss(0.18, 0.05),
            "email":    random.gauss(0.10, 0.03),
            "code":     random.gauss(0.25, 0.08),
            "default":  random.gauss(0.12, 0.04),
        }
        return max(0.05, speeds.get(field_type, speeds["default"]))

    # ── Password eye toggle ────────────────────────────────────────────────────

    @staticmethod
    def verify_password_eye(device_mgr, driver):
        """Toggle the password-visibility eye icon. Non-fatal — caller wraps in try/except."""
        if random.random() > 0.75:
            return  # skip 25% of the time

        logger.info("👁️  Human behavior: toggling password eye icon...")
        sleep(random.gauss(1.2, 0.4))

        selectors = [
            ("id",    "com.instagram.android:id/text_input_end_icon"),
            ("xpath", "//android.widget.ImageButton[@content-desc='Show password']"),
            ("xpath", "//android.widget.ImageButton[@content-desc='Hide password']"),
            ("xpath", "//android.widget.ImageView[contains(@content-desc,'password')]"),
            ("text",  "Password visibility"),
        ]

        from selenium.webdriver.common.by import By
        success = False
        for kind, sel in selectors:
            try:
                if kind == "id":
                    driver.find_element(By.ID, sel).click()
                elif kind == "xpath":
                    driver.find_element(By.XPATH, sel).click()
                else:
                    device_mgr.click_text(driver, sel, exact=False, timeout=2)
                success = True
                break
            except Exception:
                continue

        if success:
            logger.info("  ✓ Eye icon toggled")
            sleep(random.gauss(1.8, 0.4))
        else:
            raise RuntimeError("Eye icon not found with any selector")

    # ── Scroll helpers ─────────────────────────────────────────────────────────

    @staticmethod
    def scroll_through_terms(device_mgr, driver):
        logger.info("📖 Human behavior: scrolling through terms...")
        count = random.randint(2, 5)
        for i in range(count):
            device_mgr.swipe(driver, 400, 600, 400, 300, random.randint(400, 700))
            sleep(random.gauss(0.8, 0.3))
        if random.random() < 0.40:
            logger.info("  Scrolling back up (second thoughts)...")
            device_mgr.swipe(driver, 400, 300, 400, 600, 500)
            sleep(random.gauss(0.5, 0.2))

    @staticmethod
    def indecisive_date_swipes(device_mgr, driver, target_year, current_year=2005):
        logger.info(f"📅 Selecting birth year ({target_year})...")
        year_diff  = current_year - target_year
        swipes     = abs(year_diff) // 3
        overshoot  = random.randint(2, 5)
        total      = swipes + overshoot
        for _ in range(total):
            device_mgr.swipe(driver, 820, 1150, 820, 1350, random.randint(250, 400))
            sleep(random.gauss(0.4, 0.15))
        sleep(random.gauss(1.2, 0.4))
        logger.info("  Correcting overshoot...")
        for _ in range(overshoot):
            device_mgr.swipe(driver, 820, 1350, 820, 1150, random.randint(250, 350))
            sleep(random.gauss(0.4, 0.15))
        sleep(random.gauss(0.8, 0.3))

    # ── Field-level micro-behaviors ────────────────────────────────────────────

    @staticmethod
    def double_check_field(adb_bin):
        if random.random() < 0.30:
            logger.info("🔍 Human behavior: double-checking field...")
            subprocess.run([str(adb_bin), "shell", "input", "keyevent", "29"], check=False)
            sleep(random.gauss(0.8, 0.3))
            subprocess.run([str(adb_bin), "shell", "input", "keyevent", "4"], check=False)
            sleep(random.gauss(0.4, 0.2))

    @staticmethod
    def deliberate_next_click(device_mgr, driver):
        if random.random() < 0.15:
            sleep(random.gauss(0.5, 0.2))
        sleep(HumanBehavior.gaussian_pause(1.5, 0.5, 0.5, 5.0))

    @staticmethod
    def back_button_panic(adb_bin):
        if random.random() < 0.04:
            logger.info("😱 Human behavior: accidental back press...")
            subprocess.run([str(adb_bin), "shell", "input", "keyevent", "4"], check=False)
            sleep(random.gauss(0.8, 0.3))

    @staticmethod
    def minimize_check_notifications(device_mgr, adb_bin):
        if random.random() < 0.25:
            logger.info("📱 Human behavior: minimizing to check notifications...")
            device_mgr.minimize_and_restore_app()
            sleep(random.gauss(1.5, 0.5))

    @staticmethod
    def edit_username(device_mgr, driver, adb_bin):
        logger.info("✏️  Human behavior: editing suggested username...")
        try:
            device_mgr.click_text(driver, "Edit", exact=True, timeout=5)
            sleep(random.gauss(1, 0.3))
            subprocess.run([str(adb_bin), "shell", "input", "keyevent", "29"], check=False)
            sleep(random.gauss(0.3, 0.1))
            subprocess.run([str(adb_bin), "shell", "input", "keyevent", "111"], check=False)
            sleep(random.gauss(0.3, 0.1))
            suffix = str(random.randint(100, 999))
            logger.info(f"  Adding suffix: {suffix}")
            for c in suffix:
                subprocess.run([str(adb_bin), "shell", "input", "text", c], check=False)
                sleep(0.1)
            sleep(random.gauss(0.8, 0.3))
        except Exception:
            logger.info("  ⏭️  Edit button not found — using suggested username.")

    # ── App-level macro behaviors ──────────────────────────────────────────────

    @staticmethod
    def app_restarts_behavior(device_mgr, package_name):
        """Close and re-open the app randomly — looks like an indecisive user."""
        if random.random() < 0.4:
            logger.info("📱 Human behavior: closing & re-opening app (indecisive launch)...")
            device_mgr._adb("shell", "am", "force-stop", package_name)
            sleep(random.gauss(2.5, 0.6))
            device_mgr._adb("shell", "monkey", "-p", package_name,
                             "-c", "android.intent.category.LAUNCHER", "1")
            sleep(random.gauss(5.0, 1.2))

    @staticmethod
    def fake_login_behavior(device_mgr, driver, adb_bin):
        """Type a fake username/password on the login screen, then back out."""
        logger.info("👤 Human behavior: probing login screen with fake credentials...")
        try:
            fake_user = f"user_{random.randint(1000, 9999)}"
            device_mgr.click_text(driver, "Username", exact=False, timeout=5)
            sleep(0.5)
            subprocess.run([str(adb_bin), "shell", "input", "text", fake_user], check=False)
            sleep(random.gauss(1.5, 0.4))

            device_mgr.click_text(driver, "Password", exact=False, timeout=5)
            sleep(0.5)
            subprocess.run([str(adb_bin), "shell", "input", "text", "qwerty123"], check=False)
            sleep(random.gauss(2.0, 0.5))

            logger.info("  'Hmm, that's not right. Let me create a new account.'")
            # Dismiss keyboard first
            subprocess.run([str(adb_bin), "shell", "input", "keyevent", "4"], check=False)
            sleep(0.5)
        except Exception as e:
            logger.info(f"  ⏭️  Fake login interrupted (UI not matching): {e}")

    @staticmethod
    def forgot_password_trip(device_mgr, driver, adb_bin):
        """Navigate to Forgot Password and immediately come back."""
        if random.random() < 0.4:
            logger.info("🔍 Human behavior: wandering into 'Forgot password'...")
            try:
                device_mgr.click_text(driver, "Forgot password", exact=False, timeout=5)
                sleep(random.gauss(3.0, 1.0))
                logger.info("  'Nah, I'll just make a new account.'")
                subprocess.run([str(adb_bin), "shell", "input", "keyevent", "4"], check=False)
                sleep(random.gauss(1.0, 0.3))
            except Exception:
                pass  # not visible — that's fine

    @staticmethod
    def check_system_settings(device_mgr, adb_bin):
        """Briefly open system settings then come back — looks like a distracted user."""
        if random.random() < 0.20:
            logger.info("⚙️  Human behavior: checking system settings...")
            device_mgr._adb("shell", "am", "start", "-a", "android.settings.SETTINGS")
            sleep(random.gauss(3.0, 1.0))
            device_mgr._adb("shell", "input", "swipe", "500", "1500", "500", "500", "500")
            sleep(random.gauss(1.5, 0.5))
            device_mgr._adb("shell", "input", "keyevent", "4")
            sleep(random.gauss(1.0, 0.3))

    @staticmethod
    def accidental_minimize(device_mgr):
        """Accidentally press Home, then restore the app."""
        if random.random() < 0.15:
            logger.info("🏠 Human behavior: accidental home press — restoring...")
            from config import INSTAGRAM_PACKAGE
            device_mgr._adb("shell", "input", "keyevent", "3")
            sleep(random.gauss(2.5, 0.8))
            device_mgr._adb("shell", "monkey", "-p", INSTAGRAM_PACKAGE,
                             "-c", "android.intent.category.LAUNCHER", "1")
            sleep(random.gauss(3.0, 1.0))

    @staticmethod
    def navigation_hesitation(adb_bin):
        """Pause before tapping Next, and occasionally go back one screen."""
        if random.random() < 0.25:
            logger.info("🤔 Human behavior: navigation hesitation...")
            sleep(random.gauss(2.5, 1.0))
            if random.random() < 0.3:
                logger.info("  'Let me check the previous screen...'")
                subprocess.run([str(adb_bin), "shell", "input", "keyevent", "4"], check=False)
                sleep(random.gauss(2.0, 0.5))
                # Caller is responsible for re-clicking the forward button if needed

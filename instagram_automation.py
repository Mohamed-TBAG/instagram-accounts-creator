import random
import logging
import re
from time import sleep
import names
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from config import ADB_BIN, INSTAGRAM_PACKAGE, APPIUM_SERVER_URL
from human_behavior import HumanBehavior
from network_behavior import NetworkBehavior
from email_client import EmailClient
from antibot_behavior import AntiBotBehavior
logger = logging.getLogger("InstagramAutomation")
MONTH_NAMES = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

def _adb(device_mgr, *args):
    device_mgr._adb(*args)

class InstagramSignUpFlow:

    def __init__(self, device_mgr):
        self.device_mgr    = device_mgr
        self.driver        = None
        self.human         = HumanBehavior()
        self.network       = NetworkBehavior(device_mgr)
        self.antibot       = AntiBotBehavior(device_mgr)
        self.email_client  = EmailClient()
        self.email_address = None
        self.password      = "Pp66778899"
        self.manual_email_mode = False

    def run(self):
        logger.info(">>> 🤖 STARTING INSTAGRAM SIGNUP AUTOMATION <<<")
        logger.info("\n[ANTI-BOT] Preparing device...")
        self.antibot.setup_anti_detection_measures()
        self.network.send_pigeon_log("app_start", async_mode=True)
        self.network.send_launcher_sync(async_mode=True)
        logger.info("\n[HUMANIZATION] Pre-Appium behavioral warmup...")
        self._adb_warmup()
        logger.info("\n[APP LAUNCH] Connecting Appium...")
        self._connect_appium()
        self._onboarding_phase()
        self._email_phase()
        self.network.send_prefill_check(async_mode=True)
        self.network.send_pigeon_log("verification_attempt", async_mode=True)
        self._verification_phase()
        self._password_phase()
        self._dob_phase()
        self._fullname_phase()
        self._username_phase()
        self.network.send_qe_sync(async_mode=True)
        self.network.send_mock_browser_request(async_mode=True)
        self._terms_phase()
        logger.info("✅ ACCOUNT SUCCESSFULLY CREATED!")

    def _is_package_installed(self, package_name):
        try:
            res = self.device_mgr._adb("shell", "pm", "path", package_name, timeout=10)
            return "package:" in (res.stdout or "")
        except Exception:
            return False

    def _get_foreground_package_preappium(self):
        probes = [
            ("shell", "dumpsys", "window", "windows"),
            ("shell", "dumpsys", "activity", "activities"),]
        for probe in probes:
            try:
                result = self.device_mgr._adb(*probe, timeout=10)
                blob = ((result.stdout or "") + "\n" + (result.stderr or ""))
                lines = blob.splitlines()
                focus_lines = [
                    line for line in lines
                    if any(marker in line for marker in ("mCurrentFocus", "mFocusedApp", "topResumedActivity", "ResumedActivity"))]
                joined = "\n".join(focus_lines or lines[:40]).lower()
                if INSTAGRAM_PACKAGE.lower() in joined:
                    return INSTAGRAM_PACKAGE
                if "com.android.launcher3" in joined:
                    return "com.android.launcher3"
                match = re.search(r" ([a-z0-9._]+)/", joined)
                if match:
                    return match.group(1)
            except Exception:
                continue
        return None

    def _launch_instagram_preappium(self):
        for _ in range(3):
            if random.random() < 0.6:
                logger.info("  🌐 Launching via Deep-Link Intent (Browser Origin)...")
                self.device_mgr._adb(
                    "shell", "am", "start", "-W", "-a", "android.intent.action.VIEW",
                    "-d", "https://www.instagram.com/cristiano/", INSTAGRAM_PACKAGE,
                    timeout=20,)
            else:
                logger.info("  📱 Launching via Standard Intent...")
                self.device_mgr._adb(
                    "shell", "am", "start", "-W", "-n",
                    f"{INSTAGRAM_PACKAGE}/com.instagram.mainactivity.LauncherActivity",
                    timeout=20,)
            sleep(max(5.0, random.gauss(6.0, 1.0)))
            if self._get_foreground_package_preappium() == INSTAGRAM_PACKAGE:
                return True
            self.device_mgr._adb("shell", "monkey", "-p", INSTAGRAM_PACKAGE,
                                  "-c", "android.intent.category.LAUNCHER", "1")
            sleep(3.0)
            if self._get_foreground_package_preappium() == INSTAGRAM_PACKAGE:
                return True
        logger.warning("  ⚠️  Instagram did not reach foreground during pre-Appium launch")
        return False

    def _warmup_instagram_read_only(self):
        logger.info("  📱 Warmup: Instagram read-only session...")
        if not self._launch_instagram_preappium():
            raise RuntimeError("Instagram not foreground for read-only warmup")
        for _ in range(random.randint(1, 3)):
            self.device_mgr._adb("shell", "input", "swipe",
                                  "540", "1650", "540", "980",
                                  str(random.randint(300, 550)))
            sleep(random.gauss(1.6, 0.5))
            if random.random() < 0.55:
                self.device_mgr._adb("shell", "input", "swipe",
                                      "540", "980", "540", "1450",
                                      str(random.randint(260, 430)))
                sleep(random.gauss(1.1, 0.3))

    def _warmup_instagram_hesitation_typing(self):
        logger.info("  ✍️  Warmup: hesitant typing on Instagram login...")
        if not self._launch_instagram_preappium():
            raise RuntimeError("Instagram not foreground for hesitant typing warmup")
        self.device_mgr._adb("shell", "input", "tap", "540", "820") 
        sleep(random.gauss(0.8, 0.2))
        fake_user = f"user{random.randint(1000, 9999)}"
        self.device_mgr._adb("shell", "input", "text", fake_user)
        sleep(random.gauss(1.0, 0.3))
        for _ in range(random.randint(2, 5)):
            self.device_mgr._adb("shell", "input", "keyevent", "67")
            sleep(random.gauss(0.18, 0.05))
        self.device_mgr._adb("shell", "input", "keyevent", "111")   
        sleep(0.5)

    def _warmup_instagram_task_switch(self):
        logger.info("  🔄 Warmup: task switching around Instagram...")
        if not self._launch_instagram_preappium():
            raise RuntimeError("Instagram not foreground for task-switch warmup")
        self.device_mgr._adb("shell", "input", "keyevent", "3") 
        sleep(random.gauss(1.7, 0.4))
        self.device_mgr._adb("shell", "input", "keyevent", "187") 
        sleep(random.gauss(1.2, 0.3))
        self.device_mgr._adb("shell", "input", "tap", "540", "360")
        sleep(random.gauss(1.5, 0.4))
        if not self._launch_instagram_preappium():
            raise RuntimeError("Instagram failed to restore after task switch")

    def _warmup_instagram_random_touch_noise(self):
        logger.info("  👆 Warmup: random touch noise inside Instagram...")
        if not self._launch_instagram_preappium():
            raise RuntimeError("Instagram not foreground for random-touch warmup")
        touch_points = [(130, 300), (930, 300), (540, 620), (540, 1420), (220, 1720), (850, 1720)]
        for _ in range(random.randint(2, 5)):
            x, y = random.choice(touch_points)
            self.device_mgr._adb("shell", "input", "tap", str(x), str(y))
            sleep(random.gauss(0.9, 0.25))
            if random.random() < 0.45:
                self.device_mgr._adb("shell", "input", "swipe",
                                      "540", "1500", "540", "1200",
                                      str(random.randint(180, 320)))
                sleep(random.gauss(0.8, 0.2))

    def _warmup_system_settings(self):
        logger.info("  ⚙️  Checking system settings...")
        self.device_mgr._adb("shell", "am", "start", "-a", "android.settings.DEVICE_INFO_SETTINGS")
        sleep(random.gauss(3.0, 1.0))
        self.device_mgr._adb("shell", "input", "swipe", "500", "1200", "500", "600", "400")
        sleep(random.gauss(2.0, 0.5))
        self.device_mgr._adb("shell", "am", "start", "-a", "android.settings.WIFI_SETTINGS")
        sleep(random.gauss(3.0, 1.0))
        self.device_mgr._adb("shell", "input", "keyevent", "3")  # HOME
        sleep(1.0)

    def _warmup_notifications(self):
        logger.info("  🔔 Checking notifications...")
        for _ in range(random.randint(1, 3)):
            self.device_mgr._adb("shell", "cmd", "statusbar", "expand-notifications")
            sleep(random.gauss(2.0, 0.6))
            self.device_mgr._adb("shell", "cmd", "statusbar", "collapse")
            sleep(random.gauss(1.0, 0.3))

    def _warmup_instagram_probe(self):
        logger.info("  🧭 Warmup: probing Instagram login journey...")
        if not self._launch_instagram_preappium():
            raise RuntimeError("Instagram not foreground for probe warmup")
        self.device_mgr._adb("shell", "input", "tap", "540", "800")
        sleep(0.8)
        fake_user = f"user{random.randint(1000, 9999)}"
        self.device_mgr._adb("shell", "input", "text", fake_user)
        sleep(random.gauss(1.5, 0.5))
        self.device_mgr._adb("shell", "input", "keyevent", "111")
        sleep(0.5)
        self.device_mgr._adb("shell", "am", "force-stop", INSTAGRAM_PACKAGE)
        sleep(random.gauss(3.0, 1.0))
        self.device_mgr._adb("shell", "monkey", "-p", INSTAGRAM_PACKAGE,
                              "-c", "android.intent.category.LAUNCHER", "1")
        sleep(random.gauss(4.0, 1.0))
        self.device_mgr._adb("shell", "input", "tap", "540", "1200")
        sleep(random.gauss(3.0, 1.0))
        self.device_mgr._adb("shell", "input", "keyevent", "3")
        sleep(random.gauss(1.8, 0.4))
        self.device_mgr._adb("shell", "am", "force-stop", INSTAGRAM_PACKAGE)
        sleep(random.gauss(2.0, 0.7))

    def _warmup_personalize_device(self):
        logger.info("  🎨 Personalizing device...")
        self.device_mgr._adb("shell", "settings", "put", "system", "screen_brightness",
                              str(random.randint(80, 200)))
        sleep(0.5)
        self.device_mgr._adb("shell", "settings", "put", "system", "font_scale",
                              str(random.choice(["1.0", "1.05", "0.95", "1.1"])))
        sleep(0.5)

    def _adb_warmup(self):
        behaviors = [
            (0.85, self._warmup_instagram_read_only),
            (0.70, self._warmup_instagram_hesitation_typing),
            (0.60, self._warmup_instagram_task_switch),
            (0.55, self._warmup_instagram_random_touch_noise),
            (0.65, self._warmup_instagram_probe),
            (0.50, self._warmup_notifications),
            (0.35, self._warmup_system_settings),
            (0.40, self._warmup_personalize_device),]
        if not self._is_package_installed(INSTAGRAM_PACKAGE):
            raise RuntimeError(f"Instagram package '{INSTAGRAM_PACKAGE}' is not installed.")
        random.shuffle(behaviors)
        executed = 0
        for probability, func in behaviors:
            if random.random() < probability:
                try:
                    func()
                    executed += 1
                except Exception as e:
                    logger.warning(f"  ⚠️  Warmup {func.__name__} failed: {e}")
        if executed == 0:
            logger.info("  ℹ️  Warmup randomization skipped all actions; running fallback probe...")
            try:
                self._warmup_instagram_probe()
            except Exception as e:
                logger.warning(f"  ⚠️  Fallback warmup probe failed: {e}")
        logger.info("  📱 Final Instagram launch before Appium...")
        if not self._launch_instagram_preappium():
            logger.warning("  ⚠️  Final pre-Appium Instagram launch failed; Appium will restore the app.")
        sleep(4.0)

    def _connect_appium(self):
        from appium import webdriver as appium_webdriver
        for attempt in range(1, 4):
            try:
                self.driver = self.device_mgr.connect_appium(APPIUM_SERVER_URL)
                if not isinstance(self.driver, appium_webdriver.Remote):
                    raise RuntimeError("Driver is not Remote.")
                try:
                    self.driver.activate_app(INSTAGRAM_PACKAGE)
                    sleep(2.0)
                except Exception:
                    pass
                logger.info("  ✅ Appium driver ready.")
                return
            except Exception as e:
                logger.warning(f"  ⚠️  Appium attempt {attempt}/3 failed: {e}")
                sleep(5)
        raise RuntimeError("Appium connection failed after 3 attempts.")

    def _w(self, timeout=10):
        return WebDriverWait(self.driver, timeout)

    def _find(self, xpath, timeout=10):
        return self._w(timeout).until(EC.presence_of_element_located((By.XPATH, xpath)))

    def _find_clickable(self, xpath, timeout=10):
        return self._w(timeout).until(EC.element_to_be_clickable((By.XPATH, xpath)))

    def _tap_text(self, text, timeout=10):
        xpath = (
            f'//*['
            f'contains(translate(@text,"ABCDEFGHIJKLMNOPQRSTUVWXYZ","abcdefghijklmnopqrstuvwxyz"),"{text.lower()}") '
            f'or contains(translate(@content-desc,"ABCDEFGHIJKLMNOPQRSTUVWXYZ","abcdefghijklmnopqrstuvwxyz"),"{text.lower()}")'
            f']')
        self._find_clickable(xpath, timeout).click()
        logger.info(f"  ✓ Tapped '{text}'")

    def _tap_first(self, candidates, timeout_lead=20, timeout_rest=4, fatal=None):
        for scan_round, direction in enumerate([None, "down", "up"]):
            self._prepare_for_critical_tap()
            for i, text in enumerate(candidates):
                try:
                    t = timeout_lead if (scan_round == 0 and i == 0) else timeout_rest
                    self._tap_text(text, timeout=t)
                    return
                except Exception:
                    continue
            if direction:
                self._nudge_scroll_for_visibility(direction)
        msg = fatal or f"None of {candidates} found."
        logger.error(f"❌ {msg}")
        self._dump_xml()
        raise RuntimeError(msg)

    def _type_into_field(self, field_xpath, text, field_type="default", timeout=10):
        el = self._find_clickable(field_xpath, timeout)
        el.click()
        sleep(random.gauss(0.7, 0.2))
        original_text = (el.text or el.get_attribute("text") or "").strip()
        try:
            el.clear()
        except Exception:
            pass
        if original_text and original_text not in field_xpath:
            delete_count = min(max(len(original_text) + 2, 4), 24)
            for _ in range(delete_count):
                self.device_mgr._adb("shell", "input", "keyevent", "67")
                sleep(0.03)
        sleep(0.4)
        neighbor_keys = {
            'a': 's', 'b': 'v', 'c': 'x', 'd': 'f', 'e': 'r', 'f': 'd',
            'g': 'h', 'h': 'g', 'i': 'o', 'j': 'k', 'k': 'j', 'l': 'k',
            'm': 'n', 'n': 'm', 'o': 'i', 'p': 'o', 'q': 'w', 'r': 'e',
            's': 'a', 't': 'r', 'u': 'i', 'v': 'b', 'w': 'q', 'x': 'c',
            'y': 'u', 'z': 'x',}
        delays = {
            "password": (0.18, 0.06),
            "email":    (0.10, 0.04),
            "code":     (0.30, 0.08),
            "name":     (0.09, 0.03),}
        base, jitter = delays.get(field_type, (0.12, 0.05))
        error_rate = 0.08 if field_type in ("name", "email") else 0.0
        for char in text:
            if random.random() < 0.05:
                sleep(random.gauss(1.5, 0.5))
            if random.random() < error_rate and char.lower() in neighbor_keys:
                wrong = neighbor_keys[char.lower()]
                el.send_keys(wrong)
                sleep(random.gauss(0.4, 0.1))
                self.device_mgr._adb("shell", "input", "keyevent", "67")  # BACKSPACE
                sleep(random.gauss(0.3, 0.1))
            el.send_keys(char)
            sleep(max(0.04, random.gauss(base, jitter)))
        sleep(0.3)
        logger.info(f"  ✓ Typed into field ({field_type}, {len(text)} chars)")

    def _is_keyboard_visible(self):
        try:
            out = self.device_mgr._adb("shell", "dumpsys", "input_method", timeout=8)
            blob = ((out.stdout or "") + "\n" + (out.stderr or "")).lower()
            markers = ("minputshown=true", "isinputviewshown=true", "inputshown=true")
            return any(marker in blob for marker in markers)
        except Exception:
            return None

    def _dismiss_keyboard(self, attempts=3):
        attempts = max(1, int(attempts))
        for _ in range(attempts):
            visible = self._is_keyboard_visible()
            if visible is False:
                return
            self.device_mgr._adb("shell", "input", "keyevent", "111") 
            sleep(0.25)
        sleep(0.2)

    def _prepare_for_critical_tap(self):
        for _ in range(2):
            self._dismiss_keyboard(attempts=2)
            sleep(0.15)
        try:
            self.device_mgr._adb("shell", "cmd", "statusbar", "collapse")
        except Exception:
            pass

    def _nudge_scroll_for_visibility(self, direction):
        if direction == "down":
            self._adb_swipe(540, 1650, 540, 980, 320)
        else:
            self._adb_swipe(540, 980, 540, 1650, 320)
        sleep(0.4)

    def _get_current_package(self):
        probes = [
            ("shell", "dumpsys", "window", "windows"),
            ("shell", "dumpsys", "activity", "activities"),]
        for probe in probes:
            try:
                result = self.device_mgr._adb(*probe, timeout=10)
                blob = ((result.stdout or "") + "\n" + (result.stderr or "")).lower()
                if INSTAGRAM_PACKAGE.lower() in blob:
                    return INSTAGRAM_PACKAGE
                if "com.android.launcher3" in blob:
                    return "com.android.launcher3"
            except Exception:
                continue
        return None

    def _ensure_instagram_foreground(self, reason="resume Instagram", settle_time=2.5):
        for attempt in range(1, 4):
            current_pkg = self._get_current_package()
            if current_pkg == INSTAGRAM_PACKAGE:
                self._prepare_for_critical_tap()
                return True
            logger.info(f"  📱 Restoring Instagram ({reason}, attempt {attempt}/3)...")
            try:
                if self.driver:
                    self.driver.activate_app(INSTAGRAM_PACKAGE)
                    sleep(settle_time)
            except Exception:
                pass
            current_pkg = self._get_current_package()
            if current_pkg == INSTAGRAM_PACKAGE:
                self._prepare_for_critical_tap()
                return True
            self.device_mgr._adb("shell", "monkey", "-p", INSTAGRAM_PACKAGE,
                                  "-c", "android.intent.category.LAUNCHER", "1")
            sleep(settle_time)
        self._dump_xml()
        raise RuntimeError(f"Could not restore Instagram to foreground after: {reason}")

    def _dump_xml(self):
        try:
            with open("error_ui_dump.xml", "w", encoding="utf-8") as f:
                f.write(self.driver.page_source)
            logger.info("  📄 UI dumped → error_ui_dump.xml")
        except Exception:
            pass

    def _nav_up(self):
        try:
            el = self.driver.find_element(By.XPATH,'//*[@content-desc="Navigate up" or @content-desc="Back"]')
            el.click()
            sleep(0.5)
            return True
        except Exception:
            return False

    def _adb_tap(self, x, y):
        self.device_mgr._adb("shell", "input", "tap", str(x), str(y))
        sleep(0.4)

    def _adb_swipe(self, x1, y1, x2, y2, duration_ms=300):
        self.device_mgr._adb(
            "shell", "input", "swipe",
            str(x1), str(y1), str(x2), str(y2), str(duration_ms))
        sleep(0.35)

    def _read_screen(self, screen_name):
        base_time = random.gauss(3.5, 1.5)
        actual = max(1.0, min(8.0, base_time))
        logger.info(f"  📖 Reading '{screen_name}' ({actual:.1f}s)...")
        sleep(actual)

    def _check_notifications_midflow(self):
        if random.random() < 0.3:
            logger.info("  🔔 Checking notifications mid-signup...")
            self.device_mgr._adb("shell", "cmd", "statusbar", "expand-notifications")
            sleep(random.gauss(2.0, 0.7))
            self.device_mgr._adb("shell", "cmd", "statusbar", "collapse")
            sleep(0.5)

    def _double_check_typed_field(self, field_xpath):
        if random.random() < 0.4:
            try:
                el = self.driver.find_element(By.XPATH, field_xpath)
                el.click()
                sleep(random.gauss(2.0, 0.7))
                self._dismiss_keyboard()
                sleep(0.3)
            except Exception:
                pass

    def _mid_signup_app_restart(self):
        if random.random() < 0.25:
            logger.info("  🔄 App restart mid-signup (distracted user)...")
            self.device_mgr._adb("shell", "input", "keyevent", "3")
            sleep(random.gauss(4.0, 1.5))
            if random.random() < 0.5:
                self.device_mgr._adb("shell", "cmd", "statusbar", "expand-notifications")
                sleep(random.gauss(2.0, 0.7))
                self.device_mgr._adb("shell", "cmd", "statusbar", "collapse")
                sleep(1.0)
            self._ensure_instagram_foreground(reason="mid-signup restart", settle_time=3.0)

    def _onboarding_phase(self):
        logger.info("\n[PHASE 1] ONBOARDING — navigating to email signup")
        sleep(3)
        self._read_screen("Login/Profile screen")
        if random.random() < 0.6:
            logger.info("  📜 Scrolling around...")
            for _ in range(random.randint(1, 2)):
                self.device_mgr._adb("shell", "input", "swipe", "500", "1200", "500", "800", "400")
                sleep(random.gauss(1.5, 0.5))
                self.device_mgr._adb("shell", "input", "swipe", "500", "800", "500", "1200", "400")
                sleep(random.gauss(1.0, 0.4))
        if random.random() < 0.8:
            logger.info("  🤦‍♂️ Executing 'Failed Login' stumble...")
            try:
                try:
                    login_banner = self.driver.find_element(By.XPATH, '//*[@text="Log In" or @content-desc="Log In"]')
                    login_banner.click()
                    sleep(2.0)
                except:
                    pass
                fields = self.driver.find_elements(By.CLASS_NAME, "android.widget.EditText")
                if len(fields) >= 2:
                    fields[0].click()
                    sleep(0.5)
                    fields[0].send_keys(f"user{random.randint(1000, 9999)}")
                    sleep(1.0)
                    fields[1].click()
                    sleep(0.5)
                    fields[1].send_keys("WrongPass123!")
                    self._dismiss_keyboard()
                    sleep(1.0)
                    login_btn = self.driver.find_element(By.XPATH, '//*[@text="Log in" or @text="Log In" or @content-desc="Log in"]')
                    login_btn.click()
                    logger.info("  ✓ Tapped Log in with fake credentials.")
                    sleep(random.gauss(4.0, 1.0))
                    try:
                        ok_btn = self.driver.find_element(By.XPATH, '//*[@text="OK" or @text="Dismiss"]')
                        ok_btn.click()
                        sleep(1.0)
                    except:
                        pass
                    logger.info("  ✓ Stumble complete. User is now 'resorting' to signing up.")
            except Exception as e:
                logger.info("  ⚠️ Skipped stumble (UI didn't match login fields).")
        for _ in range(3):
            self._dismiss_keyboard()
            sleep(0.3)
        self._tap_first(
            ["Create new account", "Sign up", "Don't have an account", "Create new or log into existing account"],
            timeout_lead=30, timeout_rest=5,
            fatal="Could not find 'Create Account'. Is Instagram on the login screen?")
        self._tap_first(
            ["Sign up with email", "Use email or phone number", "Use email", "Email"],
            timeout_lead=20, timeout_rest=4,
            fatal="Could not find 'Sign up with email'.")

    def _email_phase(self):
        logger.info("\n[PHASE 2] EMAIL INPUT")
        self._read_screen("Email address form")
        choice = input("\nEnter email on device, then tap Next. Type 'auto' here only if you want generated email: ").strip().lower()
        self.manual_email_mode = choice != "auto"
        if self.manual_email_mode:
            return
        self._email_auto()

    def _email_auto(self):
        self.email_address = self.email_client.generate_email()
        logger.info(f"  📧 Email: {self.email_address}")
        email_xpath = (
            '//*[@hint="Email address" or @text="Email address" '
            'or contains(@resource-id,"email") '
            'or @hint="Mobile number or email"]')
        self._type_into_field(email_xpath, self.email_address, field_type="email", timeout=15)
        self._double_check_typed_field(email_xpath)
        self._dismiss_keyboard()
        sleep(0.5)
        self._check_notifications_midflow()
        self.human.deliberate_next_click(self.device_mgr, self.driver)
        self._tap_first(["Next"], timeout_lead=10, timeout_rest=3,
                        fatal="Next not found after email.")
        self.manual_email_mode = False

    def _verification_phase(self):
        logger.info("\n[PHASE 3] VERIFICATION CODE")
        self._read_screen("Confirmation code page")
        if self.manual_email_mode:
            input("Enter the OTP on the device, tap Next, then press Enter here...")
            return
        logger.info(f"  ⏳ Polling inbox for OTP ({self.email_address})...")
        code = self.email_client.poll_for_code(self.email_address, timeout=90, interval=5.0)
        logger.info(f"  🔐 Code: {code}")
        otp_xpath = (
            '//*[@hint="Confirmation code" or @hint="Enter code" '
            'or contains(@resource-id,"confirmation_code") '
            'or @hint="6-digit code"]')
        self._type_into_field(otp_xpath, code, field_type="code", timeout=15)
        self._dismiss_keyboard()
        sleep(0.4)
        self.human.deliberate_next_click(self.device_mgr, self.driver)
        self._tap_first(["Next"], timeout_lead=10, timeout_rest=3,
                        fatal="Next not found after OTP.")

    def _password_phase(self):
        logger.info("\n[PHASE 4] PASSWORD")
        self._read_screen("Create a password")
        pass_xpath = (
            '//*[@hint="Password" or @hint="Create a password" '
            'or contains(@resource-id,"password") '
            'or @password="true"]')
        self._type_into_field(pass_xpath, self.password, field_type="password", timeout=15)
        self._double_check_typed_field(pass_xpath)
        self._dismiss_keyboard()
        sleep(0.5)
        self._check_notifications_midflow()
        self.human.deliberate_next_click(self.device_mgr, self.driver)
        self._tap_first(["Next"], timeout_lead=10, timeout_rest=3,
                        fatal="Next not found after password.")

    def _dob_phase(self):
        logger.info("\n[PHASE 5] DATE OF BIRTH")
        self._read_screen("Birthday picker")
        target_year  = random.randint(1990, 2005)
        target_month = random.randint(1, 12)    
        target_day   = random.randint(1, 28)   
        logger.info(f"  🎂 Target DOB: {MONTH_NAMES[target_month-1]} {target_day}, {target_year}")
        sleep(1.5)
        try:
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located(
                    (By.XPATH, '//*[@text="Birthday (0 years old)" or contains(@text,"Birthday")]')))
        except Exception:
            pass
        sleep(0.8)
        try:
            bd_el = self.driver.find_element(
                By.XPATH,'//*[@text="Birthday (0 years old)" or contains(@text,"Birthday")]')
            bd_el.click()
            sleep(1.2)
        except Exception:
            pass
        self._set_date_picker(target_month, target_day, target_year)
        sleep(0.8)
        self._mid_signup_app_restart()
        self.human.deliberate_next_click(self.device_mgr, self.driver)
        self._tap_first(["Next"], timeout_lead=15, timeout_rest=5,
                        fatal="Next not found after DOB.")

    def _picker_swipe(self, picker_el, steps, direction="up"):
        bounds   = picker_el.rect
        x        = int(bounds['x'] + bounds['width'] / 2)
        cy       = int(bounds['y'] + bounds['height'] / 2)
        item_h   = int(bounds['height'] / 3)       
        half = item_h // 2
        if direction == "down":   
            y_from, y_to = cy - half, cy + half
        else:
            y_from, y_to = cy + half, cy - half
        for _ in range(steps):
            self._adb_swipe(x, y_from, x, y_to, duration_ms=280)

    def _set_date_picker(self, target_month, target_day, target_year):
        try:
            pickers = WebDriverWait(self.driver, 10).until(
                lambda d: d.find_elements(By.CLASS_NAME, "android.widget.NumberPicker")
                if len(d.find_elements(By.CLASS_NAME, "android.widget.NumberPicker")) >= 3
                else False)
        except Exception:
            pickers = self.driver.find_elements(By.CLASS_NAME, "android.widget.NumberPicker")
        if not pickers or len(pickers) < 3:
            logger.warning(f"  ⚠️  Only {len(pickers)} NumberPicker(s) found — attempting fallback")
            self._dob_fallback_adb(target_month, target_day, target_year)
            return
        month_picker, day_picker, year_picker = pickers[0], pickers[1], pickers[2]
        logger.info(f"  ✓ Found 3 NumberPickers")
        import datetime
        now = datetime.datetime.now()
        month_diff = target_month - now.month
        if month_diff != 0:
            direction = "up" if month_diff > 0 else "down"
            self._picker_swipe(month_picker, abs(month_diff), direction)
            sleep(0.5)
        day_diff = target_day - now.day
        if day_diff != 0:
            direction = "up" if day_diff > 0 else "down"
            self._picker_swipe(day_picker, abs(day_diff), direction)
            sleep(0.5)
        year_diff = target_year - now.year  
        if year_diff != 0:
            direction = "up" if year_diff > 0 else "down"
            self._picker_swipe(year_picker, abs(year_diff), direction)
            sleep(0.5)
        sleep(0.6)
        logger.info(f"  ✓ Pickers scrolled: month={target_month}, day={target_day}, year={target_year}")
        self._tap_set_button()

    def _tap_set_button(self):
        try:
            el = WebDriverWait(self.driver, 8).until(
                EC.element_to_be_clickable((By.ID, "android:id/button1")))
            el.click()
            logger.info("  ✓ Tapped SET (by resource-id)")
            sleep(0.6)
            return
        except Exception:
            pass
        try:
            el = self.driver.find_element(By.XPATH, '//android.widget.Button[@text="SET"]')
            el.click()
            logger.info("  ✓ Tapped SET (by exact text)")
            sleep(0.6)
            return
        except Exception:
            pass
        logger.warning("  ⚠️  SET: Appium failed — ADB tapping at (700, 1193)")
        self._adb_tap(700, 1193)

    def _dob_fallback_adb(self, target_month, target_day, target_year):
        """Last resort: use pure ADB taps in the approximate picker region."""
        logger.warning("  ⚠️  Using ADB-only DOB fallback")
        try:
            size = self.driver.get_window_size()
            w, h = size['width'], size['height']
            year_x = int(w * 0.78)
            cy     = int(h * 0.52)
            item_h = int(h * 0.067) 
            import datetime
            year_diff = datetime.datetime.now().year - target_year 
            for _ in range(year_diff):
                self._adb_swipe(year_x, cy - item_h, year_x, cy + item_h, 280)
            self._tap_set_button()
        except Exception as e:
            logger.error(f"  ❌ DOB fallback failed: {e}")

    def _fullname_phase(self):
        logger.info("\n[PHASE 6] FULL NAME")
        name = names.get_full_name()
        self.full_name = name
        logger.info(f"  👤 Name: {name}")
        self._read_screen("Full name entry")
        sleep(2.0)  
        name_xpaths = [
            '//*[@text="Full name"]',
            '//*[@hint="Full name"]',
            '//*[contains(@resource-id,"full_name")]',
            '//*[@hint="Name"]',
            '//*[@text="Name"]',
            '//android.widget.EditText[@password="false"]',]
        for xpath in name_xpaths:
            try:
                el = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, xpath)))
                self._type_into_field(xpath, name, field_type="name", timeout=5)
                logger.info(f"  ✓ Typed name with selector: {xpath}")
                self._double_check_typed_field(xpath)
                break
            except Exception:
                continue
        else:
            self._dump_xml()
            raise RuntimeError("Could not find Full Name field with any selector.")
        self._dismiss_keyboard()
        sleep(0.5)
        self._check_notifications_midflow()
        self.human.deliberate_next_click(self.device_mgr, self.driver)
        self._tap_first(["Next"], timeout_lead=10, timeout_rest=3,
                        fatal="Next not found after name.")

    def _username_phase(self):
        logger.info("\n[PHASE 7] USERNAME")
        self._read_screen("Username selection")
        username_xpaths = [
            '//*[@text="Username"]',
            '//*[@hint="Username"]',
            '//*[contains(@resource-id,"username")]',
            '//android.widget.EditText[@password="false"]',]

        def build_candidate(attempt):
            base_name = getattr(self, "full_name", names.get_first_name())
            stem = "".join(ch.lower() for ch in base_name if ch.isalnum())
            stem = stem[:12] or f"user{random.randint(100, 999)}"
            if attempt == 0:
                return f"{stem}{random.randint(100, 999)}"
            return f"{stem}{random.randint(1000, 99999)}"

        def username_status():
            try:
                page = self.driver.page_source.lower()
            except Exception:
                return None
            if any(token in page for token in ["username isn't available", "not available", "unavailable", "try another username", "username not available"]):
                return "invalid"
            if any(token in page for token in ["username available", "is available", "available username"]):
                return "valid"
            return None

        for xpath in username_xpaths:
            try:
                el = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, xpath))
                )
                current = el.text or el.get_attribute("text") or ""
                logger.info(f"  Suggested username: '{current}'")

                for attempt in range(4):
                    candidate = build_candidate(attempt)
                    self._type_into_field(xpath, candidate, field_type="name", timeout=5)
                    logger.info(f"  Trying username: {candidate}")
                    sleep(5.0)
                    status = username_status()
                    if status != "invalid":
                        logger.info(f"  ✓ Username accepted or no rejection detected: {candidate}")
                        break
                    logger.info(f"  ↻ Username rejected, retrying: {candidate}")
                self._dismiss_keyboard()
                break
            except Exception:
                continue
        else:
            logger.warning(f"  ⚠️  Username field interaction failed")
            
        sleep(random.gauss(1.0, 0.3))
        self._tap_first(["Next"], timeout_lead=10, timeout_rest=3,
                        fatal="Next not found after username.")

    def _terms_phase(self):
        logger.info("\n[PHASE 8] TERMS & CONDITIONS")
        self._read_screen("Terms and conditions")
        self._prepare_for_critical_tap()
        self.human.scroll_through_terms(self.device_mgr, self.driver)
        self._tap_first(
            ["I agree", "Agree", "Accept"],
            timeout_lead=30, timeout_rest=5,
            fatal="Could not find 'I agree' button.")

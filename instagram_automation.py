import hashlib
import json
import random
import logging
import re
from time import sleep, monotonic
import xml.etree.ElementTree as ET
from pathlib import Path
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
        self.entry_ui_mode = None
        self.current_stage = "unknown"
        self.stage_history = []

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
        launch_strategies = [
            ("shell", "am", "start", "-W", "-n",
             f"{INSTAGRAM_PACKAGE}/com.instagram.mainactivity.LauncherActivity"),
            ("shell", "am", "start", "-W", "-a", "android.intent.action.MAIN",
             "-c", "android.intent.category.LAUNCHER", "-n",
             f"{INSTAGRAM_PACKAGE}/com.instagram.mainactivity.LauncherActivity"),
            ("shell", "monkey", "-p", INSTAGRAM_PACKAGE,
             "-c", "android.intent.category.LAUNCHER", "1"),
        ]
        for attempt in range(3):
            strategy = launch_strategies[attempt % len(launch_strategies)]
            logger.info(f"  📱 Launching Instagram (strategy {attempt + 1}/3)...")
            self.device_mgr._adb(*strategy, timeout=20)
            sleep(max(2.0, random.gauss(2.8, 0.45)))
            if self._get_foreground_package_preappium() == INSTAGRAM_PACKAGE:
                self._resolve_language_gate_preappium()
                return True
            self.device_mgr._adb("shell", "am", "force-stop", INSTAGRAM_PACKAGE, check=False, timeout=10)
            sleep(0.6)
            self.device_mgr._adb("shell", "monkey", "-p", INSTAGRAM_PACKAGE,
                                 "-c", "android.intent.category.LAUNCHER", "1")
            sleep(1.5)
            if self._get_foreground_package_preappium() == INSTAGRAM_PACKAGE:
                self._resolve_language_gate_preappium()
                return True
        logger.warning("  ⚠️  Instagram did not reach foreground during pre-Appium launch")
        return False

    def _dump_uia_preappium(self, remote_path="/sdcard/preappium_uia.xml"):
        try:
            self.device_mgr._adb("shell", "uiautomator", "dump", remote_path, check=False, timeout=12)
            out = self.device_mgr._adb("shell", "cat", remote_path, check=False, timeout=10)
            return out.stdout or ""
        except Exception:
            return ""

    @staticmethod
    def _bounds_center(bounds):
        match = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds or "")
        if not match:
            return None
        x1, y1, x2, y2 = map(int, match.groups())
        return ((x1 + x2) // 2, (y1 + y2) // 2)

    def _screen_size_preappium(self):
        try:
            out = self.device_mgr._adb("shell", "wm", "size", check=False, timeout=8)
            text = (out.stdout or "") + (out.stderr or "")
            m = re.search(r"(\d+)x(\d+)", text)
            if m:
                return int(m.group(1)), int(m.group(2))
        except Exception:
            pass
        return 720, 1280

    def _find_language_gate_button_center(self, xml_text):
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError:
            return None
        primary_tokens = [
            "english", "(usa)", "angielskim", "kontynuuj",
            "continue", "use instagram in english",
        ]
        secondary_tokens = ["retry", "try again", "ponownie", "spróbuj"]
        primary_center = None
        secondary_center = None
        for node in root.iter("node"):
            text = (node.attrib.get("text") or "").strip().lower()
            content = (node.attrib.get("content-desc") or "").strip().lower()
            hay = f"{text} {content}".strip()
            if not hay:
                continue
            center = self._bounds_center(node.attrib.get("bounds"))
            if not center:
                continue
            if primary_center is None and any(token in hay for token in primary_tokens):
                primary_center = center
            if secondary_center is None and any(token in hay for token in secondary_tokens):
                secondary_center = center
        return primary_center or secondary_center

    def _looks_like_language_gate(self, xml_text):
        page = (xml_text or "").lower()
        gate_markers = [
            "english (usa)",
            "(usa)",
            "języku angielskim",
            "use instagram in english",
            "language",
        ]
        issue_markers = [
            "wystąpił błąd",
            "error",
            "problem",
            "retry",
            "try again",
            "spróbuj",
            "ponownie",
            "kontynuuj",
            "continue",
        ]
        return any(g in page for g in gate_markers) and any(i in page for i in issue_markers)

    def _resolve_language_gate_preappium(self):
        # Some boots land on a language/error interstitial; clear it before Appium.
        for attempt in range(1, 4):
            xml_text = self._dump_uia_preappium()
            if not xml_text or not self._looks_like_language_gate(xml_text):
                return
            center = self._find_language_gate_button_center(xml_text)
            if center is None:
                w, h = self._screen_size_preappium()
                center = (w // 2, int(h * 0.90))
            logger.info(f"  🌐 Language prompt detected, confirming ({attempt}/3)...")
            self.device_mgr._adb(
                "shell", "input", "tap", str(center[0]), str(center[1]),
                check=False, timeout=8)
            sleep(0.9)

    def _find_preappium_node_center_by_tokens(self, tokens, xml_text=None):
        xml_text = xml_text or self._dump_uia_preappium()
        if not xml_text:
            return None
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError:
            return None
        lowered = [t.lower() for t in tokens]
        for node in root.iter("node"):
            text = (node.attrib.get("text") or "").strip().lower()
            content = (node.attrib.get("content-desc") or "").strip().lower()
            hay = f"{text} {content}".strip()
            if not hay:
                continue
            if not any(token in hay for token in lowered):
                continue
            center = self._bounds_center(node.attrib.get("bounds"))
            if center:
                return center
        return None

    def _ensure_preappium_login_surface(self):
        xml_text = self._dump_uia_preappium()
        if not xml_text:
            return
        page = xml_text.lower()
        if "get started" in page and ("already have" in page or "already have an account" in page):
            center = self._find_preappium_node_center_by_tokens(
                ["i already have", "already have an account", "already have account"],
                xml_text=xml_text,
            )
            if center:
                logger.info("  🧭 Pre-Appium new entry UI detected → tapping 'I already have account'")
                self.device_mgr._adb(
                    "shell", "input", "tap", str(center[0]), str(center[1]),
                    check=False, timeout=8)
                sleep(1.2)

    def _preappium_entry_state(self):
        xml_text = self._dump_uia_preappium()
        if not xml_text:
            return "unknown", ""
        page = xml_text.lower()
        if "get started" in page and ("already have" in page or "already have an account" in page):
            self.entry_ui_mode = "new_landing"
            return "new_landing", xml_text
        if any(token in page for token in [
            "create new account",
            "sign up",
            "don't have an account",
            "use email or phone number",
        ]):
            self.entry_ui_mode = "old_entry"
            return "old_entry", xml_text
        if any(token in page for token in [
            "phone number, username, or email",
            "password",
            "log in",
            "login",
        ]):
            return "login", xml_text
        return "unknown", xml_text

    def _preappium_tap_text(self, candidates, timeout=8):
        deadline = monotonic() + timeout
        lowered = [c.lower() for c in candidates]
        while monotonic() < deadline:
            xml_text = self._dump_uia_preappium()
            if not xml_text:
                sleep(0.3)
                continue
            center = self._find_preappium_node_center_by_tokens(lowered, xml_text=xml_text)
            if center:
                self.device_mgr._adb(
                    "shell", "input", "tap", str(center[0]), str(center[1]),
                    check=False, timeout=8)
                sleep(0.45)
                return True
            sleep(0.25)
        return False

    def _quick_random_touch_noise(self, taps=2):
        width, height = self._screen_size_preappium()
        points = [
            (int(width * 0.22), int(height * 0.28)),
            (int(width * 0.78), int(height * 0.28)),
            (int(width * 0.50), int(height * 0.42)),
            (int(width * 0.35), int(height * 0.62)),
            (int(width * 0.66), int(height * 0.62)),
        ]
        for _ in range(max(1, taps)):
            x, y = random.choice(points)
            self.device_mgr._adb("shell", "input", "tap", str(x), str(y), check=False, timeout=8)
            sleep(0.18)
        if random.random() < 0.7:
            x = width // 2
            y1 = int(height * 0.70)
            y2 = int(height * 0.48)
            self.device_mgr._adb(
                "shell", "input", "swipe",
                str(x), str(y1), str(x), str(y2), "180",
                check=False, timeout=8)
            sleep(0.2)

    def _preappium_type_fake_login_fields(self):
        self._ensure_preappium_login_surface()
        sleep(0.4)
        self._adb_tap(540, 760)
        sleep(0.25)
        fake_user = f"user{random.randint(1000, 9999)}"
        self.device_mgr._adb("shell", "input", "text", fake_user, check=False, timeout=8)
        sleep(0.3)
        self._adb_tap(540, 910)
        sleep(0.25)
        fake_pass = f"Wrongpass{random.randint(100, 999)}"
        self.device_mgr._adb("shell", "input", "text", fake_pass, check=False, timeout=8)
        sleep(0.25)
        self.device_mgr._adb("shell", "input", "keyevent", "111", check=False, timeout=8)

    def _fast_preappium_instagram_journey(self):
        logger.info("  ⚡ Warmup: fast Instagram-only journey...")
        if not self._launch_instagram_preappium():
            raise RuntimeError("Instagram not foreground for fast warmup journey")
        sleep(1.0)
        state, _ = self._preappium_entry_state()
        self._quick_random_touch_noise(taps=2)
        if state == "new_landing":
            if self._preappium_tap_text(["Get started", "Get Started"], timeout=4):
                sleep(1.0)
                self.device_mgr._adb("shell", "input", "keyevent", "4", check=False, timeout=8)
                sleep(0.5)
            if self._preappium_tap_text(["I already have an account", "I already have account"], timeout=4):
                sleep(0.8)
        else:
            if self._preappium_tap_text(
                ["Create new account", "Sign up", "Don't have an account", "Create new or log into existing account"],
                timeout=4,
            ):
                sleep(0.9)
                self.device_mgr._adb("shell", "input", "keyevent", "4", check=False, timeout=8)
                sleep(0.5)
        self._preappium_type_fake_login_fields()
        self.device_mgr._adb("shell", "input", "keyevent", "3", check=False, timeout=8)
        sleep(0.7)
        self.device_mgr._adb(
            "shell", "monkey", "-p", INSTAGRAM_PACKAGE,
            "-c", "android.intent.category.LAUNCHER", "1",
            check=False, timeout=10)
        sleep(1.3)
        self._quick_random_touch_noise(taps=1)
        self.device_mgr._adb("shell", "am", "force-stop", INSTAGRAM_PACKAGE, check=False, timeout=10)
        sleep(0.5)
        self.device_mgr._adb(
            "shell", "monkey", "-p", INSTAGRAM_PACKAGE,
            "-c", "android.intent.category.LAUNCHER", "1",
            check=False, timeout=10)
        sleep(1.4)
        if state == "new_landing":
            self._preappium_tap_text(["Get started", "Get Started"], timeout=2)
            sleep(0.5)
            self.device_mgr._adb("shell", "input", "keyevent", "4", check=False, timeout=8)
        else:
            self._preappium_tap_text(
                ["Create new account", "Sign up", "Don't have an account", "Create new or log into existing account"],
                timeout=2,
            )
            sleep(0.5)
            self.device_mgr._adb("shell", "input", "keyevent", "4", check=False, timeout=8)
        self.device_mgr._adb("shell", "input", "keyevent", "3", check=False, timeout=8)

    def _warmup_instagram_read_only(self):
        logger.info("  📱 Warmup: Instagram read-only session...")
        if not self._launch_instagram_preappium():
            raise RuntimeError("Instagram not foreground for read-only warmup")
        for _ in range(random.randint(1, 3)):
            self._safe_vertical_swipe(direction="down", duration_ms=random.randint(300, 550))
            sleep(random.gauss(1.6, 0.5))
            if random.random() < 0.55:
                self._safe_vertical_swipe(direction="up", duration_ms=random.randint(260, 430))
                sleep(random.gauss(1.1, 0.3))

    def _warmup_instagram_hesitation_typing(self):
        logger.info("  ✍️  Warmup: hesitant typing on Instagram login...")
        if not self._launch_instagram_preappium():
            raise RuntimeError("Instagram not foreground for hesitant typing warmup")
        self._ensure_preappium_login_surface()
        self._adb_tap(540, 820)
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
        self._adb_tap(540, 360)
        sleep(random.gauss(1.5, 0.4))
        if not self._launch_instagram_preappium():
            raise RuntimeError("Instagram failed to restore after task switch")

    def _warmup_instagram_random_touch_noise(self):
        logger.info("  👆 Warmup: random touch noise inside Instagram...")
        if not self._launch_instagram_preappium():
            raise RuntimeError("Instagram not foreground for random-touch warmup")
        width, height = self._current_screen_size()
        touch_points = [
            (int(width * 0.15), int(height * 0.22)),
            (int(width * 0.85), int(height * 0.22)),
            (int(width * 0.50), int(height * 0.40)),
            (int(width * 0.50), int(height * 0.62)),
            (int(width * 0.25), int(height * 0.76)),
            (int(width * 0.75), int(height * 0.76)),
        ]
        for _ in range(random.randint(2, 5)):
            x, y = random.choice(touch_points)
            self._adb_tap(x, y)
            sleep(random.gauss(0.9, 0.25))
            if random.random() < 0.45:
                self._safe_vertical_swipe(direction="down", duration_ms=random.randint(180, 320))
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
        self._ensure_preappium_login_surface()
        self._adb_tap(540, 800)
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
        self._adb_tap(540, 1200)
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
        if not self._is_package_installed(INSTAGRAM_PACKAGE):
            raise RuntimeError(f"Instagram package '{INSTAGRAM_PACKAGE}' is not installed.")
        try:
            self._fast_preappium_instagram_journey()
        except Exception as e:
            logger.warning(f"  ⚠️  Fast warmup journey failed: {e}")
        logger.info("  📱 Final Instagram launch before Appium...")
        if not self._launch_instagram_preappium():
            logger.warning("  ⚠️  Final pre-Appium Instagram launch failed; Appium will restore the app.")
        # Always end warmup from a clean app process for deterministic Appium start.
        self.device_mgr._adb("shell", "am", "force-stop", INSTAGRAM_PACKAGE, check=False, timeout=10)
        sleep(1.5)

    def _connect_appium(self, reset_flow=True):
        from appium import webdriver as appium_webdriver
        for attempt in range(1, 4):
            try:
                self.driver = self.device_mgr.connect_appium(APPIUM_SERVER_URL)
                if not isinstance(self.driver, appium_webdriver.Remote):
                    raise RuntimeError("Driver is not Remote.")
                try:
                    self.driver.activate_app(INSTAGRAM_PACKAGE)
                    sleep(0.8 if reset_flow else 0.4)
                except Exception:
                    pass
                if reset_flow:
                    self._hard_close_and_reopen_instagram("post-Appium clean launch")
                    self._ensure_signup_entry_state("post-Appium startup gate")
                else:
                    logger.info("  🔁 Appium reconnected in place (no Instagram reset).")
                logger.info("  ✅ Appium driver ready.")
                return
            except Exception as e:
                logger.warning(f"  ⚠️  Appium attempt {attempt}/3 failed: {e}")
                sleep(5)
        raise RuntimeError("Appium connection failed after 3 attempts.")

    def _driver_session_alive(self):
        if not self.driver:
            return False
        try:
            _ = self.driver.session_id
            self.driver.get_window_size()
            return True
        except Exception as exc:
            msg = str(exc).lower()
            if any(token in msg for token in [
                "invalid session",
                "session is either terminated or not started",
                "nosuchdriver",
                "no such driver",
                "could not proxy command to the remote server",
                "econnrefused 127.0.0.1:8200",
                "uia2proxy",
                "unknown server-side error occurred while processing the command",
            ]):
                return False
            # Treat unexpected transient driver errors as alive; callers can fail normally.
            return True

    def _ensure_active_driver(self, reason="mid-flow check"):
        if self._driver_session_alive():
            return
        logger.warning(f"  ⚠️ Appium session lost ({reason}) — reconnecting...")
        self._connect_appium(reset_flow=False)
        self._ensure_instagram_foreground(reason=f"{reason} reconnect", settle_time=0.8)

    def _w(self, timeout=10):
        self._ensure_active_driver("webdriver wait")
        return WebDriverWait(self.driver, timeout)

    def _find(self, xpath, timeout=10):
        self._ensure_active_driver(f"find {xpath[:40]}")
        return self._w(timeout).until(EC.presence_of_element_located((By.XPATH, xpath)))

    def _find_clickable(self, xpath, timeout=10):
        self._ensure_active_driver(f"find clickable {xpath[:40]}")
        return self._w(timeout).until(EC.element_to_be_clickable((By.XPATH, xpath)))

    def _tap_text(self, text, timeout=10):
        xpath = (
            f'//*['
            f'contains(translate(@text,"ABCDEFGHIJKLMNOPQRSTUVWXYZ","abcdefghijklmnopqrstuvwxyz"),"{text.lower()}") '
            f'or contains(translate(@content-desc,"ABCDEFGHIJKLMNOPQRSTUVWXYZ","abcdefghijklmnopqrstuvwxyz"),"{text.lower()}")'
            f']')
        self._find_clickable(xpath, timeout).click()
        logger.info(f"  ✓ Tapped '{text}'")

    def _tap_first(self, candidates, timeout_lead=10, timeout_rest=2, fatal=None):
        for scan_round, direction in enumerate([None, "down", "up"]):
            self._ensure_instagram_foreground(
                reason=f"searching '{candidates[0]}'",
                settle_time=1.4)
            self._prepare_for_critical_tap(aggressive=False)
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

    def _focus_xpath_field(self, field_xpath, timeout=10, retries=3):
        last_error = None
        for _ in range(max(1, retries)):
            try:
                el = self._find_clickable(field_xpath, timeout)
                el.click()
                sleep(random.gauss(0.4, 0.12))
                return el
            except Exception as exc:
                last_error = exc
                sleep(0.25)
        if last_error:
            raise last_error
        raise RuntimeError(f"Could not focus field: {field_xpath}")

    def _clear_focused_field(self, max_backspaces=32):
        for _ in range(max_backspaces):
            self.device_mgr._adb("shell", "input", "keyevent", "67", check=False, timeout=6)
            sleep(0.02)

    def _type_into_field(self, field_xpath, text, field_type="default", timeout=10):
        el = self._focus_xpath_field(field_xpath, timeout=timeout, retries=3)
        original_text = ""
        try:
            original_text = (el.text or el.get_attribute("text") or "").strip()
        except Exception:
            original_text = ""
        try:
            el.clear()
        except Exception:
            pass
        if original_text and original_text not in field_xpath:
            delete_count = min(max(len(original_text) + 2, 4), 24)
            self._clear_focused_field(max_backspaces=delete_count)
        sleep(0.25)
        if field_type in {"password", "code"}:
            self._type_focused_via_adb(text, clear_first=False)
            logger.info(f"  ✓ Typed into field ({field_type}, {len(text)} chars) via focused ADB")
            return
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
            "name":     (0.045, 0.015),}
        base, jitter = delays.get(field_type, (0.12, 0.05))
        error_rate = 0.08 if field_type in ("name", "email") else 0.0
        for char in text:
            if random.random() < 0.05:
                sleep(random.gauss(1.5, 0.5))
            if random.random() < error_rate and char.lower() in neighbor_keys:
                wrong = neighbor_keys[char.lower()]
                try:
                    el = self._focus_xpath_field(field_xpath, timeout=4, retries=2)
                    el.send_keys(wrong)
                except Exception:
                    self.device_mgr._adb("shell", "input", "text", wrong, check=False, timeout=8)
                sleep(random.gauss(0.4, 0.1))
                self.device_mgr._adb("shell", "input", "keyevent", "67")  # BACKSPACE
                sleep(random.gauss(0.3, 0.1))
            try:
                el = self._focus_xpath_field(field_xpath, timeout=4, retries=2)
                el.send_keys(char)
            except Exception:
                safe = "%s" if char == " " else char
                self.device_mgr._adb("shell", "input", "text", safe, check=False, timeout=8)
            sleep(max(0.04, random.gauss(base, jitter)))
        sleep(0.3)
        logger.info(f"  ✓ Typed into field ({field_type}, {len(text)} chars)")

    def _visible_edittext_fields(self):
        fields = []
        try:
            candidates = self.driver.find_elements(By.CLASS_NAME, "android.widget.EditText")
        except Exception:
            return fields
        for el in candidates:
            try:
                enabled = str(el.get_attribute("enabled")).lower() != "false"
                focusable = str(el.get_attribute("focusable")).lower() != "false"
                displayed = el.is_displayed()
                if enabled and focusable and displayed:
                    fields.append(el)
            except Exception:
                continue
        return fields

    def _type_into_element(self, el, text, field_type="default"):
        el.click()
        sleep(random.gauss(0.5, 0.15))
        try:
            el.clear()
        except Exception:
            pass
        delays = {
            "password": (0.16, 0.05),
            "email": (0.10, 0.04),
            "default": (0.12, 0.05),
        }
        base, jitter = delays.get(field_type, delays["default"])
        for ch in text:
            try:
                el.send_keys(ch)
            except Exception:
                safe = "%s" if ch == " " else ch
                self.device_mgr._adb("shell", "input", "text", safe, check=False, timeout=8)
            sleep(max(0.04, random.gauss(base, jitter)))

    def _detect_login_field_indexes(self):
        fields = self._visible_edittext_fields()
        if len(fields) < 2:
            return None
        password_idx = None
        for i, el in enumerate(fields):
            try:
                if str(el.get_attribute("password")).lower() == "true":
                    password_idx = i
                    break
            except Exception:
                continue
        if password_idx is None:
            password_idx = 1 if len(fields) > 1 else 0
        username_idx = 0 if password_idx != 0 else 1
        return username_idx, password_idx

    def _focus_edittext_by_index(self, idx, retries=5):
        for _ in range(max(1, retries)):
            fields = self._visible_edittext_fields()
            if len(fields) <= idx:
                sleep(0.35)
                continue
            try:
                fields[idx].click()
                sleep(0.35)
                return True
            except Exception:
                sleep(0.35)
                continue
        return False

    def _type_focused_via_adb(self, text, clear_first=True, clear_count=12):
        if clear_first:
            for _ in range(max(0, int(clear_count))):
                self.device_mgr._adb("shell", "input", "keyevent", "67", check=False, timeout=6)
        safe = str(text).replace(" ", "%s")
        self.device_mgr._adb("shell", "input", "text", safe, check=False, timeout=10)
        sleep(0.35)

    def _is_keyboard_visible(self):
        try:
            out = self.device_mgr._adb("shell", "dumpsys", "input_method", timeout=8)
            blob = ((out.stdout or "") + "\n" + (out.stderr or "")).lower()
            markers = ("minputshown=true", "isinputviewshown=true", "inputshown=true")
            return any(marker in blob for marker in markers)
        except Exception:
            return None

    def _dismiss_keyboard(self, attempts=3, aggressive=False):
        attempts = max(1, int(attempts))
        for _ in range(attempts):
            visible = self._is_keyboard_visible()
            if visible is False:
                return
            self.device_mgr._adb("shell", "input", "keyevent", "111", check=False, timeout=8)
            if aggressive and visible is True:
                sleep(0.12)
                still_visible = self._is_keyboard_visible()
                if still_visible is True:
                    self.device_mgr._adb("shell", "input", "keyevent", "4", check=False, timeout=8)
            sleep(0.25)
        if aggressive:
            try:
                width, height = self._current_screen_size()
                self._adb_tap(width // 2, int(height * 0.16))
                self.device_mgr._adb("shell", "input", "keyevent", "111", check=False, timeout=8)
            except Exception:
                pass
        sleep(0.2)

    def _prepare_for_critical_tap(self, aggressive=False):
        for _ in range(2):
            self._dismiss_keyboard(attempts=3, aggressive=aggressive)
            sleep(0.15)
        try:
            self.device_mgr._adb("shell", "cmd", "statusbar", "collapse")
        except Exception:
            pass

    def _nudge_scroll_for_visibility(self, direction):
        self._safe_vertical_swipe(direction=direction, duration_ms=320)
        sleep(0.4)

    def _get_current_package(self):
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
                    if any(marker in line for marker in ("mCurrentFocus", "mFocusedApp", "topResumedActivity", "ResumedActivity"))
                ]
                for line in focus_lines:
                    lowered = line.lower()
                    if INSTAGRAM_PACKAGE.lower() in lowered:
                        return INSTAGRAM_PACKAGE
                    if "com.android.launcher3" in lowered:
                        return "com.android.launcher3"
                    match = re.search(r"([a-z0-9._]+)/[a-z0-9._$]+", lowered)
                    if match:
                        return match.group(1)
                if not focus_lines:
                    joined = "\n".join(lines[:40]).lower()
                    if INSTAGRAM_PACKAGE.lower() in joined:
                        return INSTAGRAM_PACKAGE
                    if "com.android.launcher3" in joined:
                        return "com.android.launcher3"
            except Exception:
                continue
        return None

    def _instagram_in_foreground(self):
        return self._get_current_package() == INSTAGRAM_PACKAGE

    def _ensure_instagram_foreground(self, reason="resume Instagram", settle_time=1.2):
        for attempt in range(1, 4):
            current_pkg = self._get_current_package()
            if current_pkg == INSTAGRAM_PACKAGE:
                self._prepare_for_critical_tap()
                if self._get_current_package() == INSTAGRAM_PACKAGE:
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
                if self._get_current_package() == INSTAGRAM_PACKAGE:
                    return True
            self.device_mgr._adb(
                "shell", "am", "start", "-W", "-n",
                f"{INSTAGRAM_PACKAGE}/com.instagram.mainactivity.LauncherActivity",
                check=False, timeout=12)
            sleep(settle_time)
            current_pkg = self._get_current_package()
            if current_pkg == INSTAGRAM_PACKAGE:
                self._prepare_for_critical_tap()
                if self._get_current_package() == INSTAGRAM_PACKAGE:
                    return True
            self.device_mgr._adb("shell", "monkey", "-p", INSTAGRAM_PACKAGE,
                                  "-c", "android.intent.category.LAUNCHER", "1")
            sleep(settle_time)
            current_pkg = self._get_current_package()
            if current_pkg == INSTAGRAM_PACKAGE:
                self._prepare_for_critical_tap()
                if self._get_current_package() == INSTAGRAM_PACKAGE:
                    return True
        self._dump_xml()
        raise RuntimeError(f"Could not restore Instagram to foreground after: {reason}")

    def _entry_surface_state(self):
        if not self._instagram_in_foreground():
            return "unknown"
        try:
            page = (self.driver.page_source or "").lower()
        except Exception:
            return "unknown"
        if any(token in page for token in [
            "get started",
            "get started.",
        ]) and any(token in page for token in [
            "already have",
            "already have an account",
            "already have account",
        ]):
            self.entry_ui_mode = "new_landing"
            return "new_landing"
        if any(token in page for token in [
            "phone number, username, or email",
            "password",
            "log in",
            "login",
        ]):
            return "login"
        if any(token in page for token in [
            "create new account",
            "sign up",
            "don't have an account",
            "use email or phone number",
        ]):
            self.entry_ui_mode = "old_entry"
            return "signup_entry"
        return "unknown"

    def _wait_for_signup_option_surface(self, timeout=6):
        deadline = monotonic() + timeout
        required_tokens = [
            "sign up with email",
            "use email or phone number",
            "use email",
            "mobile number or email",
            "phone number or email",
        ]
        while monotonic() < deadline:
            if not self._instagram_in_foreground():
                try:
                    self._ensure_instagram_foreground(reason="wait for signup choice", settle_time=0.8)
                except Exception:
                    sleep(0.35)
                    continue
            try:
                page = (self.driver.page_source or "").lower()
            except Exception:
                page = ""
            if any(token in page for token in required_tokens):
                return True
            sleep(0.35)
        return False

    def _tap_any_text(self, candidates, timeout=6, ensure_foreground=False):
        if ensure_foreground:
            self._ensure_instagram_foreground(reason=f"tap {'/'.join(candidates[:1])}", settle_time=0.8)
        for text in candidates:
            try:
                self._tap_text(text, timeout=timeout)
                return True
            except Exception:
                continue
        return False

    def _required_fake_login_probe(self):
        logger.info("  🧪 Required login probe behavior (deterministic)...")
        self._ensure_instagram_foreground(reason="required fake-login probe", settle_time=1.0)
        for _ in range(3):
            state = self._entry_surface_state()
            if state == "new_landing":
                if not self._tap_any_text(["I already have an account", "I already have account"], timeout=4):
                    raise RuntimeError("New entry UI detected, but 'I already have account' was not found.")
                sleep(0.6)
            elif state != "login":
                self._tap_any_text(["Log in", "Log In", "I already have an account"], timeout=3)
                sleep(0.5)
            fields = self._visible_edittext_fields()
            if len(fields) >= 2:
                break
        else:
            self._dump_xml()
            raise RuntimeError("Fake-login probe could not find editable login fields.")

        fake_user = f"user{random.randint(10000, 99999)}"
        fake_pass = f"Wrongpass{random.randint(1000, 9999)}"
        typed = False
        for _ in range(4):
            idxs = self._detect_login_field_indexes()
            if not idxs:
                sleep(0.25)
                continue
            username_idx, password_idx = idxs
            if not self._focus_edittext_by_index(username_idx, retries=3):
                continue
            self._type_focused_via_adb(fake_user, clear_first=False)
            if not self._focus_edittext_by_index(password_idx, retries=3):
                continue
            self._type_focused_via_adb(fake_pass, clear_first=False)
            typed = True
            break
        if not typed:
            self._dump_xml()
            raise RuntimeError("Fake-login probe failed to type credentials on stable editable fields.")

        self._dismiss_keyboard(attempts=2, aggressive=False)
        self._quick_random_touch_noise(taps=1)
        logger.info("  ✓ Fake-login probe completed (no submit).")

        # Requirement: close fully and relaunch before moving to signup.
        self._hard_close_and_reopen_instagram("after required fake-login probe")
        self._ensure_instagram_foreground(reason="post fake-login relaunch", settle_time=1.0)

    def _route_into_signup(self):
        self._ensure_instagram_foreground(reason="route to signup", settle_time=0.8)
        self._dismiss_keyboard(attempts=3, aggressive=True)
        state = self._entry_surface_state()
        ui_mode = self.entry_ui_mode or state
        if ui_mode == "new_landing":
            logger.info("  🧭 Routing signup via new entry UI flag")
            for _ in range(2):
                before = self._refresh_stage()
                if self._tap_any_text(
                    ["Get started", "Get Started", "Start", "Continue"],
                    timeout=2,
                    ensure_foreground=True,
                ):
                    sleep(0.5)
                    if self._wait_for_signup_option_surface(timeout=4):
                        self._refresh_stage()
                        self._record_action("tap:get_started", stage_before=before, stage_after=self.current_stage)
                        return
                sleep(0.4)
            raise RuntimeError("Tapped 'Get started' but did not reach the signup choice screen.")
        logger.info("  🧭 Routing signup via old entry UI flag")
        for _ in range(2):
            before = self._refresh_stage()
            self._tap_first(
                ["Create new account", "Sign up", "Don't have an account", "Create new or log into existing account"],
                timeout_lead=4, timeout_rest=1,
                fatal="Could not find 'Create Account'. Is Instagram on the login screen?")
            sleep(0.5)
            if self._wait_for_signup_option_surface(timeout=4):
                self._refresh_stage()
                self._record_action("tap:create_account", stage_before=before, stage_after=self.current_stage)
                return
            logger.info("  ↻ Create-account tap did not advance yet, retrying...")
        raise RuntimeError("Tapped 'Create new account' but did not reach the signup choice screen.")

    def _is_login_or_signup_surface(self):
        try:
            page = (self.driver.page_source or "").lower()
        except Exception:
            return False
        indicators = [
            "create new account",
            "sign up",
            "use email or phone number",
            "mobile number or email",
            "phone number, username, or email",
            "get started",
            "i already have an account",
            "log in",
            "login",
            "password",
        ]
        if any(token in page for token in indicators):
            return True
        try:
            return len(self.driver.find_elements(By.CLASS_NAME, "android.widget.EditText")) > 0
        except Exception:
            return False

    def _wait_for_login_or_signup_surface(self, timeout=10):
        deadline = monotonic() + timeout
        while monotonic() < deadline:
            if self._is_login_or_signup_surface():
                return True
            sleep(1.0)
        return False

    def _hard_close_and_reopen_instagram(self, reason="state reset"):
        logger.info(f"  ♻️ Hard reset Instagram ({reason})...")
        try:
            if self.driver:
                self.driver.terminate_app(INSTAGRAM_PACKAGE)
        except Exception:
            pass
        self.device_mgr._adb("shell", "am", "force-stop", INSTAGRAM_PACKAGE, check=False, timeout=12)
        sleep(random.uniform(0.6, 1.0))
        self.device_mgr._adb(
            "shell", "am", "start", "-W", "-n",
            f"{INSTAGRAM_PACKAGE}/com.instagram.mainactivity.LauncherActivity",
            check=False, timeout=20)
        sleep(1.6)
        self._ensure_instagram_foreground(reason=reason, settle_time=1.4)
        self._dismiss_keyboard()

    def _ensure_signup_entry_state(self, reason="startup"):
        logger.info(f"  🧭 Verifying signup entry state ({reason})...")
        self._ensure_instagram_foreground(reason=reason, settle_time=1.4)
        self._dismiss_keyboard(attempts=4, aggressive=True)
        if self._wait_for_login_or_signup_surface(timeout=8):
            logger.info("  ✅ Signup/login surface detected.")
            return

        logger.warning("  ⚠️ Unexpected screen state, attempting in-app recovery...")
        for _ in range(2):
            try:
                self.driver.back()
            except Exception:
                self.device_mgr._adb("shell", "input", "keyevent", "4", check=False, timeout=8)
            sleep(0.8)
            self._dismiss_keyboard(attempts=3, aggressive=True)
            if self._wait_for_login_or_signup_surface(timeout=4):
                logger.info("  ✅ Signup/login surface recovered via back navigation.")
                return

        self._hard_close_and_reopen_instagram(f"{reason} recovery")
        if not self._wait_for_login_or_signup_surface(timeout=8):
            self._dump_xml()
            raise RuntimeError("Instagram not on login/signup screen after recovery.")
        logger.info("  ✅ Signup/login surface recovered after hard reset.")

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
        tx, ty = self._clamp_to_safe_touch_area(x, y)
        self.device_mgr._adb("shell", "input", "tap", str(tx), str(ty))
        sleep(0.4)

    def _adb_swipe(self, x1, y1, x2, y2, duration_ms=300):
        sx1, sy1 = self._clamp_to_safe_touch_area(x1, y1)
        sx2, sy2 = self._clamp_to_safe_touch_area(x2, y2)
        self.device_mgr._adb(
            "shell", "input", "swipe",
            str(sx1), str(sy1), str(sx2), str(sy2), str(duration_ms))
        sleep(0.11)

    def _current_screen_size(self):
        if self.driver:
            try:
                size = self.driver.get_window_size()
                width = int(size.get("width", 0))
                height = int(size.get("height", 0))
                if width > 0 and height > 0:
                    return width, height
            except Exception:
                pass
        return self._screen_size_preappium()

    def _clamp_to_safe_touch_area(self, x, y):
        width, height = self._current_screen_size()
        x_margin = max(12, int(width * 0.03))
        # Avoid top status area and bottom gesture area.
        y_top = max(24, int(height * 0.08))
        y_bottom = min(height - 24, int(height * 0.88))
        safe_x = max(x_margin, min(width - x_margin, int(x)))
        safe_y = max(y_top, min(y_bottom, int(y)))
        return safe_x, safe_y

    def _safe_vertical_swipe(self, direction="down", duration_ms=320):
        width, height = self._current_screen_size()
        x = width // 2
        y_upper = int(height * 0.35)
        y_lower = int(height * 0.70)
        if direction == "down":
            self._adb_swipe(x, y_lower, x, y_upper, duration_ms)
            return
        self._adb_swipe(x, y_upper, x, y_lower, duration_ms)

    def _read_screen(self, screen_name, min_s=1.0, max_s=8.0, mean=3.5, std=1.5):
        base_time = random.gauss(mean, std)
        actual = max(min_s, min(max_s, base_time))
        logger.info(f"  📖 Reading '{screen_name}' ({actual:.1f}s)...")
        sleep(actual)

    def _runtime_trace_path(self):
        runtime_dir = getattr(self.device_mgr, "current_runtime_dir", None)
        if not runtime_dir:
            return None
        return Path(runtime_dir) / "flow_trace.jsonl"

    def _page_source_snapshot(self):
        if not self.driver:
            return ""
        try:
            return self.driver.page_source or ""
        except Exception:
            return ""

    def _page_signature(self, page=None):
        payload = (page if page is not None else self._page_source_snapshot()) or ""
        if not payload:
            return "none"
        return hashlib.md5(payload.encode("utf-8", errors="ignore")).hexdigest()[:12]

    def _record_action(self, action, stage_before=None, stage_after=None, outcome="ok", extra=None):
        entry = {
            "t": round(monotonic(), 3),
            "action": action,
            "stage_before": stage_before or self.current_stage,
            "stage_after": stage_after or self.current_stage,
            "outcome": outcome,
            "foreground": self._get_current_package(),
            "keyboard": self._is_keyboard_visible(),
            "page_hash": self._page_signature(),
        }
        if extra:
            entry["extra"] = extra
        self.stage_history.append(entry)
        trace_path = self._runtime_trace_path()
        if trace_path:
            try:
                trace_path.parent.mkdir(parents=True, exist_ok=True)
                with trace_path.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(entry, ensure_ascii=True) + "\n")
            except Exception:
                pass

    def _refresh_stage(self):
        self.current_stage = self._signup_stage()
        return self.current_stage

    def _wait_for_expected_stage(self, expected_stages, timeout=12, reason="transition"):
        expected = set(expected_stages)
        start_stage = self._refresh_stage()
        start_hash = self._page_signature()
        deadline = monotonic() + timeout
        while monotonic() < deadline:
            stage = self._refresh_stage()
            if stage in expected:
                self._record_action(
                    f"stage:{reason}",
                    stage_before=start_stage,
                    stage_after=stage,
                    outcome="matched",
                    extra={"expected": sorted(expected)},
                )
                return stage
            if stage in {"challenge", "success"}:
                self._record_action(
                    f"stage:{reason}",
                    stage_before=start_stage,
                    stage_after=stage,
                    outcome="terminal",
                    extra={"expected": sorted(expected)},
                )
                return stage
            if stage in {"email", "otp", "password", "dob", "fullname", "username", "terms"} and stage != start_stage and stage not in expected:
                self._record_action(
                    f"stage:{reason}",
                    stage_before=start_stage,
                    stage_after=stage,
                    outcome="unexpected",
                    extra={"expected": sorted(expected)},
                )
                raise RuntimeError(
                    f"Expected {sorted(expected)} after {reason}, but reached '{stage}' instead.")
            if self._page_signature() != start_hash and stage == "unknown":
                start_hash = self._page_signature()
            sleep(0.45)
        current = self._refresh_stage()
        self._record_action(
            f"stage:{reason}",
            stage_before=start_stage,
            stage_after=current,
            outcome="timeout",
            extra={"expected": sorted(expected)},
        )
        self._dump_xml()
        raise RuntimeError(
            f"Timed out waiting for {sorted(expected)} after {reason}; current stage is '{current}'.")

    def _stage_rank(self, stage):
        order = [
            "entry_new",
            "login",
            "signup_choice",
            "email",
            "otp",
            "password",
            "dob",
            "fullname",
            "username",
            "terms",
            "success",
            "challenge",
        ]
        try:
            return order.index(stage)
        except ValueError:
            return -1

    def _skip_phase_if_advanced(self, phase_name, target_stage, current_stage):
        if self._stage_rank(current_stage) > self._stage_rank(target_stage):
            logger.info(f"  ↪ Skipping {phase_name}; flow already advanced to {current_stage}.")
            self._record_action(
                f"skip:{phase_name}",
                stage_before=current_stage,
                stage_after=current_stage,
                outcome="already_advanced",
                extra={"target_stage": target_stage},
            )
            return True
        return False

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
        self._ensure_signup_entry_state("onboarding start")
        self._refresh_stage()
        sleep(0.9)
        self._read_screen("Login/Profile screen", min_s=0.8, max_s=2.0, mean=1.2, std=0.35)
        self._required_fake_login_probe()
        self._ensure_instagram_foreground(reason="before signup routing", settle_time=0.8)
        self._dismiss_keyboard(attempts=2, aggressive=False)
        self._route_into_signup()
        before = self._refresh_stage()
        self._tap_first(
            ["Sign up with email", "Use email or phone number", "Use email"],
            timeout_lead=6, timeout_rest=2,
            fatal="Could not find 'Sign up with email'.")
        self._wait_for_expected_stage(["email", "otp"], timeout=12, reason="signup email entry")
        self._record_action("tap:signup_email", stage_before=before, stage_after=self.current_stage)

    def _email_phase(self):
        logger.info("\n[PHASE 2] EMAIL INPUT")
        self._ensure_active_driver("email phase start")
        stage = self._wait_for_expected_stage(["email", "otp", "password"], timeout=10, reason="email phase start")
        if self._skip_phase_if_advanced("email", "email", stage):
            return
        self._read_screen("Email address form")
        choice = input("\nEnter email on device, then tap Next. Type 'auto' here only if you want generated email: ").strip().lower()
        self.manual_email_mode = choice != "auto"
        if self.manual_email_mode:
            self._wait_for_expected_stage(["otp", "password"], timeout=30, reason="manual email continue")
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
        before = self._refresh_stage()
        self._tap_first(["Next"], timeout_lead=10, timeout_rest=3,
                        fatal="Next not found after email.")
        self._wait_for_expected_stage(["otp", "password"], timeout=18, reason="email next")
        self._record_action("tap:next_email", stage_before=before, stage_after=self.current_stage)
        self.manual_email_mode = False

    def _verification_phase(self):
        logger.info("\n[PHASE 3] VERIFICATION CODE")
        self._ensure_active_driver("verification phase start")
        stage = self._wait_for_expected_stage(["otp", "password", "dob"], timeout=12, reason="verification phase start")
        if self._skip_phase_if_advanced("verification", "otp", stage):
            return
        self._read_screen("Confirmation code page")
        if self.manual_email_mode:
            input("Enter the OTP on the device, tap Next, then press Enter here...")
            self._wait_for_expected_stage(["password", "dob"], timeout=35, reason="manual otp continue")
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
        before = self._refresh_stage()
        self._tap_first(["Next"], timeout_lead=10, timeout_rest=3,
                        fatal="Next not found after OTP.")
        self._wait_for_expected_stage(["password", "dob"], timeout=18, reason="otp next")
        self._record_action("tap:next_otp", stage_before=before, stage_after=self.current_stage)

    def _password_phase(self):
        logger.info("\n[PHASE 4] PASSWORD")
        self._ensure_active_driver("password phase start")
        stage = self._wait_for_expected_stage(["password", "dob", "fullname"], timeout=12, reason="password phase start")
        if self._skip_phase_if_advanced("password", "password", stage):
            return
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
        before = self._refresh_stage()
        self._tap_first(["Next"], timeout_lead=10, timeout_rest=3,
                        fatal="Next not found after password.")
        self._wait_for_expected_stage(["dob", "fullname"], timeout=18, reason="password next")
        self._record_action("tap:next_password", stage_before=before, stage_after=self.current_stage)

    def _dob_phase(self):
        logger.info("\n[PHASE 5] DATE OF BIRTH")
        self._ensure_active_driver("dob phase start")
        stage = self._wait_for_expected_stage(["dob", "fullname", "username"], timeout=12, reason="dob phase start")
        if self._skip_phase_if_advanced("dob", "dob", stage):
            return
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
        before = self._refresh_stage()
        self._tap_first(["Next"], timeout_lead=15, timeout_rest=5,
                        fatal="Next not found after DOB.")
        self._wait_for_expected_stage(["fullname", "username"], timeout=18, reason="dob next")
        self._record_action("tap:next_dob", stage_before=before, stage_after=self.current_stage)

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
        self._ensure_active_driver("full name phase start")
        stage = self._wait_for_expected_stage(["fullname", "username", "terms"], timeout=12, reason="full name phase start")
        if self._skip_phase_if_advanced("full name", "fullname", stage):
            return
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
        before = self._refresh_stage()
        self._tap_first(["Next"], timeout_lead=10, timeout_rest=3,
                        fatal="Next not found after name.")
        self._wait_for_expected_stage(["username", "terms"], timeout=18, reason="name next")
        self._record_action("tap:next_name", stage_before=before, stage_after=self.current_stage)

    def _username_phase(self):
        logger.info("\n[PHASE 7] USERNAME")
        self._ensure_active_driver("username phase start")
        stage = self._wait_for_expected_stage(["username", "terms", "success", "challenge"], timeout=12, reason="username phase start")
        if self._skip_phase_if_advanced("username", "username", stage):
            return
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
                    sleep(2.0)
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
        before = self._refresh_stage()
        self._tap_first(["Next"], timeout_lead=10, timeout_rest=3,
                        fatal="Next not found after username.")
        self._wait_for_expected_stage(["terms", "success", "challenge"], timeout=18, reason="username next")
        self._record_action("tap:next_username", stage_before=before, stage_after=self.current_stage)

    def _terms_state(self):
        try:
            page = (self.driver.page_source or "").lower()
        except Exception:
            return "unknown"
        challenge_tokens = [
            "prove you're human",
            "verify",
            "confirm it's you",
            "phone number",
            "suspended",
            "security check",
        ]
        success_tokens = [
            "welcome",
            "find friends",
            "sync contacts",
            "add profile photo",
            "follow",
            "your story",
            "home",
            "search",
            "reels",
            "profile",
            "edit profile",
            "share your first photo",
        ]
        terms_tokens = [
            "terms",
            "privacy policy",
            "cookie policy",
            "i agree",
            "agree",
            "accept",
        ]
        if any(token in page for token in challenge_tokens):
            return "challenge"
        if any(token in page for token in success_tokens):
            return "advanced"
        if any(token in page for token in terms_tokens):
            return "terms"
        return "unknown"

    def _signup_stage(self):
        try:
            page = (self.driver.page_source or "").lower()
        except Exception:
            return "unknown"
        if self._post_agree_success_visible():
            return "success"
        if any(token in page for token in [
            "prove you're human",
            "verify",
            "confirm it's you",
            "phone number",
            "suspended",
            "security check",
        ]):
            return "challenge"
        if any(token in page for token in [
            "get started",
        ]) and any(token in page for token in [
            "already have",
            "already have an account",
            "already have account",
        ]):
            return "entry_new"
        if any(token in page for token in [
            "sign up with email",
            "use email or phone number",
            "use email",
            "mobile number or email",
            "phone number or email",
        ]):
            return "signup_choice"
        if any(token in page for token in [
            "phone number, username, or email",
            "log in",
            "login",
        ]) and "confirmation code" not in page:
            return "login"
        stages = {
            "email": ["email address", "mobile number or email"],
            "otp": ["confirmation code", "enter code", "6-digit code"],
            "password": ["create a password", "password"],
            "dob": ["birthday", "date of birth"],
            "fullname": ["full name", "name"],
            "username": ["username"],
            "terms": ["i agree", "privacy policy", "cookie policy", "accept"],
        }
        for stage, tokens in stages.items():
            if any(token in page for token in tokens):
                return stage
        return "unknown"

    def _agree_button_visible(self):
        strict_xpaths = [
            '//*[@text="I agree" or @content-desc="I agree"]',
            '//*[@text="Agree" or @content-desc="Agree"]',
            '//*[@text="Accept" or @content-desc="Accept"]',
            '//android.widget.Button[@text="I agree" or @text="Agree" or @text="Accept"]',
        ]
        for xp in strict_xpaths:
            try:
                self.driver.find_element(By.XPATH, xp)
                return True
            except Exception:
                continue
        return False

    def _agreement_page_visible(self):
        try:
            page = (self.driver.page_source or "").lower()
        except Exception:
            return False
        return self._agree_button_visible() or any(token in page for token in [
            "privacy policy",
            "cookie policy",
            "data policy",
            "terms of use",
            "i agree",
        ])

    def _tap_exact_candidates(self, exact_texts, timeout=4):
        for text in exact_texts:
            xpaths = [
                f'//*[@text="{text}"]',
                f'//*[@content-desc="{text}"]',
                f'//android.widget.TextView[@text="{text}"]',
                f'//android.widget.Button[@text="{text}"]',
            ]
            for xp in xpaths:
                try:
                    self._find_clickable(xp, timeout=timeout).click()
                    logger.info(f"  ✓ Tapped exact '{text}'")
                    return True
                except Exception:
                    continue
        return False

    def _post_agree_success_visible(self):
        try:
            page = (self.driver.page_source or "").lower()
        except Exception:
            return False
        success_tokens = [
            "add profile photo",
            "add profile picture",
            "add photo",
            "add picture",
            "choose profile picture",
            "share your first photo",
        ]
        return any(token in page for token in success_tokens)

    def _recover_terms_surface(self):
        if self._agreement_page_visible():
            logger.info("  ℹ️ Still on agreement page; skipping recovery back action.")
            return
        state = self._terms_state()
        if state == "terms":
            return
        stage = self._signup_stage()
        if stage in {"dob", "fullname", "username", "password", "email", "otp"}:
            raise RuntimeError(f"Terms recovery aborted: flow regressed to {stage} page.")
        logger.info("  ↩️ Recovering terms surface (single-step back)...")
        if not self._nav_up():
            self.device_mgr._adb("shell", "input", "keyevent", "4", check=False, timeout=8)
        sleep(1.0)
        self._ensure_instagram_foreground(reason="terms recovery", settle_time=1.8)
        self._dismiss_keyboard(attempts=2, aggressive=False)

    def _visit_terms_link(self, link_candidates, label):
        if not self._tap_exact_candidates(link_candidates, timeout=2):
            logger.info(f"  ℹ️ {label} link not found on this UI.")
            return False
        sleep(0.6)
        if self._agreement_page_visible():
            logger.info(f"  ℹ️ {label} exact tap did not leave the agreement page; skipping back.")
            return False
        dwell = max(2.0, random.gauss(3.3, 0.7))
        logger.info(f"  🔎 Opened {label}; reading ({dwell:.1f}s)...")
        sleep(dwell)
        self._recover_terms_surface()
        return True

    def _tap_agree_strict(self):
        strict_xpaths = [
            '//*[@text="I agree" or @content-desc="I agree"]',
            '//*[@text="Agree" or @content-desc="Agree"]',
            '//*[@text="Accept" or @content-desc="Accept"]',
            '//android.widget.Button[@text="I agree" or @text="Agree" or @text="Accept"]',
        ]
        for xp in strict_xpaths:
            try:
                self._find_clickable(xp, timeout=6).click()
                logger.info("  ✓ Tapped agree button (strict selector)")
                return True
            except Exception:
                continue
        return self._tap_any_text(["I agree", "Agree", "Accept", "Accept all"], timeout=6)

    def _wait_post_agree_outcome(self, timeout=25):
        deadline = monotonic() + timeout
        while monotonic() < deadline:
            if self._post_agree_success_visible():
                return "advanced"
            if self._agreement_page_visible():
                return "terms"
            state = self._terms_state()
            if state in ("advanced", "challenge"):
                return state
            stage = self._signup_stage()
            if stage in {"dob", "fullname", "username", "password", "email", "otp"}:
                return "regressed"
            if not self._agree_button_visible() and stage == "unknown":
                return "advanced"
            sleep(1.2)
        return "unknown"

    def _terms_phase(self):
        logger.info("\n[PHASE 8] TERMS & CONDITIONS")
        self._ensure_active_driver("terms phase start")
        self._ensure_instagram_foreground(reason="terms phase start", settle_time=1.8)
        stage = self._wait_for_expected_stage(["terms", "success", "challenge"], timeout=12, reason="terms phase start")
        if self._skip_phase_if_advanced("terms", "terms", stage):
            return
        self._dismiss_keyboard(attempts=3, aggressive=True)
        self._read_screen("Terms and conditions", min_s=0.8, max_s=2.0, mean=1.2, std=0.3)
        self._visit_terms_link(
            ["Privacy Policy", "Data Policy", "Terms of Use"],
            label="Privacy/Terms",
        )
        self._visit_terms_link(
            ["Cookie Policy", "Cookies Policy", "Cookie Use"],
            label="Cookies",
        )
        for attempt in range(1, 4):
            self._ensure_instagram_foreground(reason=f"terms attempt {attempt}", settle_time=1.6)
            self._prepare_for_critical_tap(aggressive=False)
            try:
                before = self._refresh_stage()
                if not self._tap_agree_strict():
                    raise RuntimeError("Could not find agree button.")
            except Exception:
                self._recover_terms_surface()
                continue
            outcome = self._wait_post_agree_outcome(timeout=12)
            if outcome == "advanced":
                self._refresh_stage()
                self._record_action("tap:agree", stage_before=before, stage_after=self.current_stage, outcome="advanced")
                logger.info("  ✅ Terms accepted and flow advanced.")
                return
            if outcome == "challenge":
                self._refresh_stage()
                self._record_action("tap:agree", stage_before=before, stage_after=self.current_stage, outcome="challenge")
                raise RuntimeError("Post-agree challenge detected (verification/human check required).")
            if outcome == "regressed":
                self._refresh_stage()
                self._record_action("tap:agree", stage_before=before, stage_after=self.current_stage, outcome="regressed")
                self._dump_xml()
                raise RuntimeError("Terms phase regressed to an earlier signup page after Agree.")
            if outcome == "terms":
                self._refresh_stage()
                self._record_action("tap:agree", stage_before=before, stage_after=self.current_stage, outcome="no_transition")
                logger.info("  ℹ️ Still on agreement page after Agree; retrying without back navigation.")
                continue
            logger.warning("  ⚠️ No clear transition after Agree; retrying terms flow...")
            self._refresh_stage()
            self._record_action("tap:agree", stage_before=before, stage_after=self.current_stage, outcome="unknown")
            self._recover_terms_surface()
        self._dump_xml()
        raise RuntimeError("Terms phase did not reach the profile-photo/success screen after Agree.")

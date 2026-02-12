import time
import random
import logging
import subprocess
import os
from config import ADB_BIN, UI_ELEMENT_TIMEOUT
from human_behavior import HumanBehavior
from network_behavior import NetworkBehavior

logger = logging.getLogger("InstagramAutomation")

class InstagramSignUpFlow: 

    def __init__(self, device_mgr, driver):
        self.device_mgr = device_mgr
        self.driver = driver
        self.human = HumanBehavior()
        self.network = NetworkBehavior(device_mgr)
        self.password = "Pp66778899"

    def run(self):
        logger.info(">>> 🤖 STARTING INSTAGRAM AUTOMATION WITH HUMAN BEHAVIOR <<<")
        try:
            logger.info("🌍 Sending Pre-Start Network Traffic...")
            self.network.send_pigeon_log("app_start") 
            self.network.send_launcher_sync()
            time.sleep(1.0)
            self._onboarding_phase()
            self._email_phase()
            logger.info("🌍 Sending Background Checks...")
            self.network.send_prefill_check()
            self.network.send_pigeon_log("verification_attempt")
            time.sleep(0.5)
            self._verification_code_phase()
            self._password_phase()
            self._dob_phase()
            self._fullname_phase()
            self._username_phase()
            logger.info("🌍 Sending Final Config Sync...")
            self.network.send_qe_sync()
            self.network.send_mock_browser_request()
            time.sleep(1.0)
            self._terms_phase()
            logger.info("✅ ABSOLUTE VICTORY: Account Successfully Created!")
            return True
        except Exception as e:
            logger.error(f"❌ Automation Failed: {e}")
            raise

    def _onboarding_phase(self):
        logger.info("\n[PHASE 1] ONBOARDING & MENU NAVIGATION")
        self._click_human("Stories", exact=True, timeout=15)
        self.human.attention_lapse()
        self._click_human("Just once", exact=True, timeout=10)
        self.human.read_time_behavior(1.0)
        self.device_mgr.minimize_and_restore_app()
        self.human.read_time_behavior(1.0)
        self._click_human("create new account", timeout=15)
        self._click_human("Sign up with email", timeout=15)

    def _email_phase(self):
        logger.info("\n[PHASE 2] EMAIL INPUT")
        email = input("  📧 Enter email address: ")
        self.device_mgr.minimize_and_restore_app()
        self.human.read_time_behavior(0.8)
        self._click_human("Email", exact=True, timeout=10)
        self.human.type_with_typos(ADB_BIN, email, field_type="email")
        self.human.double_check_field(ADB_BIN)
        self.human.deliberate_next_click(self.device_mgr, self.driver)
        self._click_human("Next", exact=True, timeout=10)

    def _verification_code_phase(self):
        logger.info("\n[PHASE 3] VERIFICATION CODE")
        self.human.minimize_check_notifications(self.device_mgr, ADB_BIN)
        code = input("  🔐 Enter verification code: ")
        self.device_mgr.click_text(self.driver, "Confirmation code", exact=True, timeout=10)
        self.human.read_time_behavior(0.5)
        self.human.type_with_typos(ADB_BIN, code, field_type="code")
        self.human.deliberate_next_click(self.device_mgr, self.driver)
        self._click_human("Next", exact=True, timeout=10)

    def _password_phase(self):
        logger.info("\n[PHASE 4] PASSWORD CREATION")
        self.human.back_button_panic(ADB_BIN)
        password = self.password
        self._click_human("Password", exact=True, timeout=10)
        self.human.type_with_typos(ADB_BIN, password, field_type="password")
        self.human.verify_password_eye(self.device_mgr, self.driver)
        self.human.deliberate_next_click(self.device_mgr, self.driver)
        self._click_human("Next", exact=True, timeout=10)

    def _dob_phase(self):
        logger.info("\n[PHASE 5] DATE OF BIRTH")
        self.human.read_time_behavior(1.5) 
        target_year = random.randint(1990, 2005)
        logger.info(f"  Target Year: {target_year}")
        self.human.indecisive_date_swipes(self.device_mgr, self.driver, target_year)
        self.human.deliberate_next_click(self.device_mgr, self.driver)
        self._click_human("Next", timeout=10)

    def _fullname_phase(self):
        logger.info("\n[PHASE 6] FULL NAME")
        import names
        full_name = names.get_full_name()
        logger.info(f"  Chosen Name: {full_name}")
        self._click_human("Full name", exact=True, timeout=10)
        self.human.type_with_typos(ADB_BIN, full_name, field_type="name")
        self.human.double_check_field(ADB_BIN)
        self.human.deliberate_next_click(self.device_mgr, self.driver)
        self._click_human("Next", exact=True, timeout=10)

    def _username_phase(self):
        logger.info("\n[PHASE 7] USERNAME CUSTOMIZATION")
        self.human.attention_lapse()
        self.human.edit_username(self.device_mgr, self.driver, ADB_BIN)
        self.human.deliberate_next_click(self.device_mgr, self.driver)
        self._click_human("Next", exact=True, timeout=10)

    def _terms_phase(self):
        logger.info("\n[PHASE 8] LEGAL & TERMS")
        self.human.scroll_through_terms(self.device_mgr, self.driver)
        try:
            links = ["Learn more", "Terms", "Privacy Policy", "Cookies Policy"]
            if random.random() < 0.35:
                link = random.choice(links)
                logger.info(f"  📖 Reading '{link}' (simulated interest)...")
                if self.device_mgr.click_text(self.driver, link, exact=True, timeout=5):
                    self.human.read_time_behavior(random.gauss(6, 2))
                    logger.info("  Returning to terms...")
                    subprocess.run([str(ADB_BIN), "shell", "input", "keyevent", "4"], check=False)
                    self.human.read_time_behavior(2.0)
        except Exception as e:
            logger.warning(f"  Failed to read policy link: {e}")

        logger.info("  Agreeing to terms...")
        self._click_human("I agree", exact=True, timeout=30)

    def _click_human(self, text, exact=False, timeout=15):
        for i in range(3):
            if self.device_mgr.click_text(self.driver, text, exact=exact, timeout=timeout):
                logger.info(f"  ✓ Clicked '{text}'")
                return True
            logger.warning(f"  ⚠️ Couldn't find '{text}', retrying ({i+1}/3)...")
            time.sleep(2)
        raise Exception(f"Failed to click '{text}' after 3 attempts")
import sys
import time
import random
import logging
import subprocess
import names
from device_manager import DeviceManager
from proxy_runner import VPNProxyClient
from appium import webdriver

from config import APPIUM_SERVER_URL, MAX_ERRORS 

# Configure logging to both file and console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("automation.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("MainController")
count = 0 

class MainController:
    def __init__(self):
        self.device_mgr = DeviceManager()
        self.vpn_client = VPNProxyClient()
        self.driver = None

    def main_loop(self):
        errors = 0
        while errors < MAX_ERRORS:
            try:
                logger.info("Initializing")
                logger.info("[1/5] Spoofing Device Identity...")
                self.device_mgr.spoof_config()
                self.device_mgr.wipe_data()
                logger.info("[2/5] Rotating IP Address...")
                try:
                    self.vpn_client.rotate_ip()
                except Exception as e:
                    logger.error(f"Failed to rotate IP: {e}")
                    errors += 1
                    continue
                logger.info("[3/5] Booting Emulator (Cold Boot)...")
                self.device_mgr.start_emulator()
                logger.info("[4/5] Setup & Warmup...")
                try:
                    self.device_mgr.apply_proxy()
                    apks = self.device_mgr.get_all_apks()
                    if not apks:
                        logger.error("No APKs found in bin folder!")
                        return
                    else:
                        if not self.device_mgr.install_split_apks(apks):
                            logger.error("Failed to install APKs!")
                            return
                    if not self.device_mgr.seed_gallery():
                        logger.error("Failed to seed gallery!")
                        return
                    self.device_mgr.warmup_actions()
                except Exception as e:
                    logger.error(f"Setup failed: {e}")
                logger.info("[5/5] Starting Automation...")
                self.driver = self.device_mgr.connect_appium(APPIUM_SERVER_URL)
                if not isinstance(self.driver, webdriver.Remote):
                    raise Exception("Appium driver not initialized")
                self.run_appium_automation()
                logger.info("ENDING MAINLOOP (for this iteration)")
                input("Press Enter to continue...")
                if self.driver:
                    try:
                        self.driver.quit()
                    except:
                        pass
                    self.driver = None
                self.device_mgr.kill_emulator()
            except KeyboardInterrupt:
                logger.info("Interrupted by user.")
                if self.driver:
                    try:
                        self.driver.quit()
                    except:
                        pass
                self.device_mgr.kill_emulator()
                self.vpn_client.stop_proxy()
                print("\nStopped.")
                break
            except Exception as e:
                logger.error(f"Main loop error: {e}")
                if self.driver:
                    try:
                        self.driver.quit()
                    except:
                        pass
                self.device_mgr.kill_emulator()
                input("\n\nPress Enter to continue...\n\n")


    def run_appium_automation(self):
        logger.info(">>> APPIUM AUTOMATION STARTED <<<")
        if not self.driver:
            raise Exception("Appium driver not initialized")
        logger.info("Step: Click 'Stories'")
        if not self.device_mgr.click_text(self.driver, "Stories", exact=True, timeout=15):
            raise Exception("could not click stories")
        logger.info("Step: Click 'Just once'")
        if not self.device_mgr.click_text(self.driver, "Just once", exact=True, timeout=5):
            raise Exception("could not click 'Just once'")
        logger.info("Minimizing and restoring app for human behavior...")
        self.device_mgr.minimize_and_restore_app()
        logger.info("Step: Click 'create new account'")
        if not self.device_mgr.click_text(self.driver, "create new account", timeout=15):
            raise Exception("could not click 'create new account'")
        logger.info("Step: Click 'sign up with email'")
        if not self.device_mgr.click_text(self.driver, "Sign up with email", timeout=15):
            raise Exception("could not click 'sign up with email'")
        logger.info("Minimizing and restoring app...")
        self.device_mgr.minimize_and_restore_app()
        logger.info("Step: Type Email Address")
        # sample_email = f"user{self.account_count}@iraqimail.org"
        email = input("Enter email: ")
        if not self.device_mgr.type_text(self.driver, "Email", email, exact=True, timeout=15):
            raise Exception("could not type email")
        logger.info("Step: Click 'Next'")
        if not self.device_mgr.click_text(self.driver, "Next", exact=True, timeout=15):
            raise Exception("could not click 'Next' after typing the email")
        code_ = input("enter code from email: ")
        logger.info("Step: Type Code")
        if not self.device_mgr.type_text(self.driver, "Confirmation code", code_, exact=True, timeout=15):
            raise Exception("Could not type the code")
        logger.info("Step: Click 'Next'")
        if not self.device_mgr.click_text(self.driver, "Next", exact=True, timeout=15):
            raise Exception("Could not click 'Next' after typing the code")
        logger.info("Step: Enter Password")
        if not self.device_mgr.type_text(self.driver, "Password", "Pp66778899", exact=True, timeout=15):
            raise Exception("Could not type the password")
        logger.info("Step: Click 'Next'")
        if not self.device_mgr.click_text(self.driver, "Next", exact=True, timeout=15):
            raise Exception("Could not click 'Next' after typing the password")
        logger.info("Step: Handle Date of Birth")
        year_swipes = random.randint(15, 30) 
        for _ in range(year_swipes):
            # Swipe down on the right side using Appium Actions (X=950, Y=1300->1600)
            self.device_mgr.swipe(self.driver, 950, 1300, 950, 1600, 300)
            logger.info("Swiped down for year (Appium)...")
            time.sleep(0.5)
        logger.info("Step: Click 'Next' (after DOB) in age page")
        if not self.device_mgr.click_text(self.driver, "Next", exact=True, timeout=15):
            raise Exception("could not click next after DOB")
        logger.info("Step: Enter Full Name")
        full_name = names.get_full_name()
        logger.info(f"Generated Name: {full_name}")
        if not self.device_mgr.type_text(self.driver, "Full name", full_name, exact=True, timeout=15):
            raise Exception("could not type the full name")
        logger.info("Step: Click 'Next' (after Name)")
        if not self.device_mgr.click_text(self.driver, "Next", exact=True, timeout=15):
            raise Exception("could not click next after typing the full name")
        logger.info("Step: Accept Username (Click Next)")
        if not self.device_mgr.click_text(self.driver, "Next", exact=True, timeout=15):
            raise Exception("could not click next after accepting username")
        logger.info("Step: Agree to Terms")
        if not self.device_mgr.click_text(self.driver, "I agree", exact=True, timeout=25):
            raise Exception("could not click i agree")

if __name__ == "__main__":
    controller = MainController()
    try:
        controller.main_loop()
    except KeyboardInterrupt:
        print("\nStopped.")
import sys
import os
import subprocess
import time
import logging
from device_manager import DeviceManager
from proxy_runner import VPNProxyClient, logger as proxy_logger
from appium import webdriver
from appium.options.android import UiAutomator2Options
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import urllib.request
APPIUM_SERVER_URL = 'http://127.0.0.1:4723' 
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("MainController")
class MainController:
    def __init__(self):
        self.device_mgr = DeviceManager()
        self.vpn_client = VPNProxyClient()
        self.account_count = 0
    def main_loop(self):
        logger.info("Initializing")
        logger.info("[1/5] Spoofing Device Identity...")
        self.device_mgr.spoof_config()
        self.device_mgr.wipe_data()
        logger.info("[2/5] Rotating IP Address...")
        try:
            self.vpn_client.rotate_ip()
            time.sleep(3) 
        except Exception as e:
            logger.error(f"Failed to rotate IP: {e}")
            cmd = input("Continue anyway? (y/n): ")
            if cmd.lower() != 'y':
                return
        logger.info("[3/5] Booting Emulator (Cold Boot)...")
        self.device_mgr.start_emulator()
        logger.info("[4/5] Setup & Warmup...")
        try:
            self.device_mgr.apply_proxy()
            apks = self.device_mgr.get_all_apks()
            if not apks:
                logger.error("No APKs found in bin folder!")
            else:
                self.device_mgr.install_split_apks(apks)
            self.device_mgr.seed_gallery()
            self.device_mgr.warmup_actions()
        except Exception as e:
            logger.error(f"Setup failed: {e}")
        logger.info("[5/5] Starting Automation...")
        self.connect_appium() 
        self.run_appium_automation()
        cmd = input("Press ENTER to end mainloop (or 'q' to quit): ")
        if cmd.lower() == 'q':
            sys.exit(0)
        logger.info("ENDING MAINLOOP")
        self.device_mgr.kill_emulator()
        time.sleep(2)
    def connect_appium(self):
        self.driver = self.device_mgr.connect_appium(APPIUM_SERVER_URL)
        if self.driver:
            logger.info("Waiting 5 seconds for UI to stabilize...")
            time.sleep(5)
        else:
            logger.error("Proceeding without Appium driver (Fallback Mode).")
    def run_appium_automation(self):
        logger.info(">>> APPIUM AUTOMATION STARTED <<<")
        try:
            if not self.driver:
                raise Exception("Appium driver not initialized")

            # 1. Handle "Stories" Selection
            logger.info("Step: Click 'Stories'")
            self.device_mgr.click_text(self.driver, "Stories", timeout=15)
            
            # 2. Handle 'Just once'
            logger.info("Step: Click 'Just once'")
            self.device_mgr.click_text(self.driver, "Just once", timeout=5)
            
            # 3. Wait 5 seconds as requested in audio
            logger.info("Waiting 5 seconds before clicking Get Started...")
            time.sleep(5)

            # 4. Handle "Get started" (Regex for variants like 'Get started' or 'Getting started')
            logger.info("Step: Click 'create new account'")
            self.device_mgr.click_text(self.driver, "create new account", timeout=15)

            logger.info("Step: Click 'sign up with email'")
            self.device_mgr.click_text(self.driver, "email", timeout=15)

            # 5. Type Email (character by character)
            logger.info("Step: Type Email Address")
            sample_email = f"user{self.account_count}@iraqimail.org"
            # Assuming the field hint is "Email", we search for and type into it
            self.device_mgr.type_text(self.driver, "Email", sample_email, timeout=10)
            
            # self.account_count += 1

        except Exception as e:
            logger.error(f"Appium failed during interaction: {e}")
            logger.info("--- CRITICAL ADB FALLBACK ---")
        finally:
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass    
        logger.info(">>> APPIUM AUTOMATION FINISHED <<<")

if __name__ == "__main__":
    controller = MainController()
    try:
        controller.main_loop()
    except KeyboardInterrupt:
        print("\nStopped.")
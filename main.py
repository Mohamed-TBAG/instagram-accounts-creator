import sys
from time import sleep
from device_manager import DeviceManager
from proxy_runner import VPNProxyClient
from instagram_automation import InstagramSignUpFlow
from appium import webdriver
from config import APPIUM_SERVER_URL, MAX_ERRORS, RETRY_DELAY, LOG_DIR
from logger_config import setup_logging, get_logger
setup_logging(log_dir=LOG_DIR, app_name="InstagramCreation")
logger = get_logger("MainController") 

class MainController:
    
    def __init__(self):
        logger.info("Initializing MainController...")
        self.device_mgr = DeviceManager()
        self.vpn_client = VPNProxyClient()
        self.driver = None
    
    def run(self):
        error_count = 0
        loop_counter = 0
        while loop_counter < 1000: 
            port = 5555
            name = "redroid_0"
            logger.info(f"\n{'='*80}")
            logger.info(f"ITERATION {loop_counter} (Errors: {error_count}/{MAX_ERRORS})")
            logger.info("=" * 80)
            try:
                self._setup_phase()
                self._boot_phase(name=name, port=port)
                self._automation_phase()
                self._cleanup_iteration(name=name)
            except KeyboardInterrupt:
                logger.info("\n⛔ Interrupted by user")
                self._cleanup_iteration(name=name, raise_on_error=False)
                print("\nStopped.")
                break
            except Exception as e:
                error_count += 1
                logger.error(f"❌ Iteration failed: {e}", exc_info=True)
                self._cleanup_iteration(name=name, raise_on_error=False)
                if error_count >= MAX_ERRORS:
                    logger.error("Too many consecutive errors. Stopping.")
                    break               
                logger.info(f"🔄 Retrying ({error_count}/{MAX_ERRORS}) in {RETRY_DELAY}s...") 
                sleep(RETRY_DELAY)
                input("\n👉 Press Enter to retry...\n") 
            else:
                error_count = 0
                logger.info(f"✅ Iteration {loop_counter} completed successfully")
                loop_counter += 1
        self._final_cleanup()
        logger.info("=" * 80)
        logger.info(f"FINISHED - Total iterations: {loop_counter}, Errors: {error_count}")
        logger.info("=" * 80)   

    def _setup_phase(self):
        logger.info("\n[PHASE 1/4] NETWORK SETUP")
        logger.info("  [1.1] Rotating IP address...")
        self.vpn_client.rotate_ip()
    
    def _boot_phase(self, name="redroid_0", port=5555):
        logger.info("\n[PHASE 2/4] REDROID CONTAINER BOOT")
        logger.info(f"  [2.1] Starting container {name} on port {port}...")
        self.device_mgr.start_emulator(name=name, port=port)
        logger.info("  [2.2] Applying proxy settings...")
        self.device_mgr.apply_proxy()
        logger.info("  [2.3] Installing Instagram APK...")
        apks = self.device_mgr.get_all_apks()
        if not apks:
            raise Exception("No APK files found in bin folder!")
        self.device_mgr.install_split_apks(apks)
        logger.info("  [2.4] Seeding gallery...")
        self.device_mgr.seed_gallery()
        print(f"\n[PAUSED] Boot phase completed! Container '{name}' is running on port {port}.")
        print("Device Identity (MAC, UUIDs, Model) has been injected cleanly.")
        input("👉 Press Enter to connect Appium and begin automation (or Ctrl+C to abort)...\n")
        logger.info("  [2.5] Performing warmup...")
        self.device_mgr.warmup_actions()
        logger.info(f"  [2.6] Connecting Appium to 127.0.0.1:{port}...")
        self.driver = self.device_mgr.connect_appium(APPIUM_SERVER_URL)
        if not isinstance(self.driver, webdriver.Remote):
            raise Exception("Failed to initialize Appium driver")

    def _automation_phase(self):
        logger.info("\n[PHASE 3/4] EXECUTING SIGN-UP FLOW")
        flow = InstagramSignUpFlow(self.device_mgr, self.driver)
        flow.run()
        logger.info("  ✅ Account creation cycle complete")
    
    def _cleanup_iteration(self, name="redroid_0", raise_on_error=True):
        logger.info("\n[PHASE 4/4] CLEANUP & TEARDOWN")
        errors = []
        logger.info("  [4.1] Disconnecting Appium driver...")
        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                errors.append(f"Failed to quit driver: {e}")
            finally:
                self.driver = None
        logger.info(f"  [4.2] Killing container {name}...")
        try:
            self.device_mgr.kill_emulator(name=name)
        except Exception as e:
            errors.append(f"Failed to kill container '{name}': {e}")
        if errors and raise_on_error:
            raise Exception(" | ".join(errors))
        for err in errors:
            logger.warning(err)
        logger.info("  ✅ Cleanup complete")
    
    def _final_cleanup(self):
        logger.info("Performing final cleanup...")
        try:
            if self.driver:
                self.driver.quit()
                self.driver = None
            self.device_mgr.kill_emulator()
            self.vpn_client.stop_proxy()
        except Exception as e:
            logger.warning(f"Error during final cleanup: {e}")

def main():
    try:
        controller = MainController()
        controller.run()
        return 0
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())

import sys
from time import sleep
from pathlib import Path
from config import HTTP_PROXY_PORT, LOG_DIR, MAX_ERRORS, PROXY_PORT
from config import APPIUM_SERVER_URL
from device_manager import DeviceManager
from logger_config import get_logger, setup_logging
from proxy_runner import VPNProxyClient
from instagram_automation import InstagramSignUpFlow
from session import build_session_context
from appium import webdriver

setup_logging(log_dir=LOG_DIR, app_name="InstagramCreation")
logger = get_logger("MainController")

class MainController:

    def __init__(self):
        logger.info("Initializing MainController...")
        self.device_mgr = DeviceManager()
        self.proxy_client = None
        self.session = None
        self.driver = None

    def _fix_binder(self):
        try:
            logger.info("🔧 Running binder fix script...")
            script_path = next(Path.cwd().glob("**/fix_binder_nodes.sh"), None)
            if script_path and script_path.exists():
                import subprocess
                subprocess.run(["bash", str(script_path)], check=False)
        except Exception as e:
            logger.warning(f"⚠️ Binder fix failed: {e}")

    def run(self):
        error_count = 0
        iteration = 0
        max_errors_allowed = 10 
        
        self._fix_binder()
        
        while iteration < 1000:
            if error_count >= max_errors_allowed:
                logger.error(f"🛑 Reached maximum allowed errors ({max_errors_allowed}). Stopping.")
                break

            self.session = build_session_context(
                iteration=iteration,
                runtime_root=LOG_DIR / "sessions",
                adb_port_base=5555,
                socks_port_base=PROXY_PORT,
                http_proxy_port_base=HTTP_PROXY_PORT,
            )
            logger.info(f"\n{'=' * 80}\nITERATION {iteration} | {self.session.session_id}\n{'=' * 80}")
            
            try:
                self._setup_phase()
                sleep(2)
                
                self._boot_phase()
                sleep(3)
                
                
                self._automation_phase()
                
                error_count = 0
                logger.info(f"✅ Iteration {iteration} completed successfully")
                iteration += 1
                logger.info("⏳ Waiting 15s before next session...")
                sleep(15)
                
            except KeyboardInterrupt:
                logger.info("\n⛔ Interrupted by user")
                break
            except Exception as e:
                error_count += 1
                logger.error(f"❌ Iteration failed: {e}")
                if "binderfs" in str(e).lower():
                    self._fix_binder()
                logger.info(f"🔄 Waiting 10s before retry ({error_count}/{max_errors_allowed})...")
                sleep(10)
            finally:
                self._cleanup_iteration()
                
        self._final_cleanup()
        logger.info("=" * 80)
        logger.info(f"FINISHED — Total iterations: {iteration}, Errors: {error_count}")
        logger.info("=" * 80)

    def _setup_phase(self):
        logger.info("\n[PHASE 1] NETWORK SETUP")
        self.proxy_client = VPNProxyClient(self.session)
        self.proxy_client.rotate_ip()

    def _boot_phase(self):
        logger.info("\n[PHASE 2] CONTAINER BOOT")
        meta = self.device_mgr.start_emulator(self.session)
        # self.device_mgr.apply_proxy(proxy_address=self.proxy_client.session_http_proxy)
        
        apks = self.device_mgr.get_all_apks()
        if not apks:
            raise Exception("No APK files found in bin/instagram/")
        self.device_mgr.install_split_apks(apks)
        
        self.device_mgr.seed_gallery()
        self.device_mgr.warmup_actions()
        
        self.driver = self.device_mgr.connect_appium(APPIUM_SERVER_URL)
        if not isinstance(self.driver, webdriver.Remote):
            raise Exception("Failed to initialize Appium driver")

    def _automation_phase(self):
        logger.info("\n[PHASE 3] EXECUTING SIGN-UP FLOW")
        flow = InstagramSignUpFlow(self.device_mgr, self.driver)
        flow.run()

    def _cleanup_iteration(self):
        logger.info("\n[PHASE 4] CLEANUP & TEARDOWN")
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            finally:
                self.driver = None
                
        if self.session:
            try:
                self.device_mgr.kill_emulator(
                    name=self.session.container_name,
                    port=self.session.adb_port)
            except Exception:
                pass
                
        if self.proxy_client:
            try:
                self.proxy_client.stop_proxy()
            except Exception:
                pass
            finally:
                self.proxy_client = None
                
        self.session = None

    def _final_cleanup(self):
        try:
            self._cleanup_iteration()
        except Exception:
            pass

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

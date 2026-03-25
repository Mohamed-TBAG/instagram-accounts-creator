import subprocess
import sys
from time import sleep
from pathlib import Path
from config import HTTP_PROXY_PORT, LOG_DIR, MAX_ERRORS, PROXY_PORT, ADB_BIN
from device_manager import DeviceManager
from logger_config import get_logger, setup_logging
from proxy_runner import VPNProxyClient
from instagram_automation import InstagramSignUpFlow
from session import build_session_context
setup_logging(log_dir=LOG_DIR, app_name="InstagramCreation")
logger = get_logger("MainController")
BINDER_SUDO_PASSWORD = "0101"

def _adb_kill_server():
    logger.info("🔧 Restarting ADB server (healing unauthorized/stale state)...")
    subprocess.run([str(ADB_BIN), "kill-server"],
                   capture_output=True, timeout=10)
    sleep(1)
    subprocess.run([str(ADB_BIN), "start-server"],
                   capture_output=True, timeout=10)
    sleep(1)
    logger.info("  ✅ ADB server restarted")

def _fix_binder():
    try:
        script = next(Path.cwd().glob("**/fix_binder_nodes.sh"), None)
        if script and script.exists():
            sudo_run = subprocess.run(
                ["sudo", "-S", "-p", "", "bash", str(script)],
                input=f"{BINDER_SUDO_PASSWORD}\n",
                text=True,
                capture_output=True,
                timeout=30,)
            if sudo_run.returncode != 0:
                logger.warning(f"⚠️ Binder fix via sudo password failed: {(sudo_run.stderr or sudo_run.stdout).strip()[:200]}")
                return
            logger.info("🔧 Binder fix script executed (auto sudo password mode)")
    except Exception as e:
        logger.warning(f"⚠️ Binder fix failed (non-critical): {e}")

class MainController:
    MAX_ITERATIONS   = 1_000
    MAX_ERRORS       = MAX_ERRORS
    BETWEEN_SLEEP    = 15            
    RETRY_SLEEP      = 12           

    def __init__(self):
        logger.info("Initializing MainController...")
        self.device_mgr    = DeviceManager()
        self.proxy_client  = None
        self.session       = None
        self.driver        = None

    def run(self):
        _fix_binder()
        error_count = 0
        iteration   = 0
        while iteration < self.MAX_ITERATIONS:
            if error_count >= self.MAX_ERRORS:
                logger.error(f"🛑 Reached max errors ({self.MAX_ERRORS}). Stopping.")
                break
            self.session = build_session_context(
                iteration         = iteration,
                runtime_root      = LOG_DIR / "sessions",
                adb_port_base     = 5555,
                socks_port_base   = PROXY_PORT,
                http_proxy_port_base = HTTP_PROXY_PORT,)
            logger.info(
                f"\n{'=' * 80}\n"
                f"ITERATION {iteration} | {self.session.session_id}\n"
                f"{'=' * 80}")
            try:
                self._phase_setup()
                self._phase_boot()
                self._phase_run()
                error_count = 0
                logger.info(f"✅ Iteration {iteration} completed successfully")
                iteration += 1
                logger.info(f"⏳ Waiting {self.BETWEEN_SLEEP}s before next session...")
                sleep(self.BETWEEN_SLEEP)
            except KeyboardInterrupt:
                logger.info("\n⛔ Interrupted by user.")
                break
            except Exception as exc:
                error_count += 1
                self._handle_iteration_error(exc, error_count)
            finally:
                self._phase_cleanup()
        logger.info("=" * 80)
        logger.info(f"FINISHED — Total iterations: {iteration}, Errors: {error_count}")
        logger.info("=" * 80)

    def _phase_setup(self):
        logger.info("\n[PHASE 1] NETWORK / PROXY SETUP")
        self.proxy_client = VPNProxyClient(self.session)
        self.proxy_client.rotate_ip()

    def _phase_boot(self):
        logger.info("\n[PHASE 2] CONTAINER BOOT")
        self.device_mgr.start_emulator(self.session)
        self.device_mgr.apply_proxy(
            proxy_address=self.proxy_client.session_http_proxy)
        sleep(2)  
        self.device_mgr.verify_network_connectivity(
            proxy_address=self.proxy_client.session_http_proxy)
        apks = self.device_mgr.get_all_apks()
        if not apks:
            raise RuntimeError("No APK files found in bin/. Cannot install Instagram.")
        self.device_mgr.install_split_apks(apks)
        self.device_mgr.seed_gallery()

    def _phase_run(self):
        logger.info("\n[PHASE 3] EXECUTING SIGN-UP FLOW")
        flow = InstagramSignUpFlow(self.device_mgr)
        flow.run()
        self.driver = flow.driver

    def _phase_cleanup(self):
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
        logger.info("  ✅ Cleanup done")

    def _handle_iteration_error(self, exc: Exception, error_count: int):
        msg = str(exc)
        logger.error(f"❌ Iteration failed [{error_count}/{self.MAX_ERRORS}]: {msg}")
        if "unauthorized" in msg or "adb" in msg.lower() and "error" in msg.lower():
            logger.warning("🩺 Detected ADB authorized error — restarting ADB server...")
            _adb_kill_server()
        elif "binderfs" in msg.lower():
            logger.warning("🩺 Detected binderfs issue — running fix script...")
            _fix_binder()
        elif "appium" in msg.lower() or "webdriver" in msg.lower() or "session" in msg.lower():
            logger.warning("🩺 Detected Appium/WebDriver error. Will restart fresh.")
        elif any(k in msg.lower() for k in ["connection", "proxy", "timeout", "network"]):
            logger.warning("🩺 Detected network error. Will rotate IP on next attempt.")
        logger.info(f"🔄 Retrying in {self.RETRY_SLEEP}s...")
        sleep(self.RETRY_SLEEP)

def main() -> int:
    try:
        controller = MainController()
        controller.run()
        return 0
    except KeyboardInterrupt:
        logger.info("\n⛔ Aborted by user at startup.")
        return 0
    except Exception as e:
        logger.critical(f"💥 Fatal unrecoverable error: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())
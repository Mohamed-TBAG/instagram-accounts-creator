import sys
import subprocess
import requests
import signal
from time import sleep
from logger_config import setup_logging, get_logger
from config import (
    API_URL, PROXY_PORT, PROJECT_ROOT, WIREPROXY_BIN, WG_KEY_BIN,
    WIREPROXY_CONF, PROXY_HOST, HTTP_PROXY_PORT, LOG_DIR)

logger = get_logger("ProxyClient")
class VPNProxyClient:

    def __init__(self):
        self.proxy_process = None
        self.conf_path = WIREPROXY_CONF
        self.proxy_log_file = None
        self.session = requests.Session()
        if not WIREPROXY_BIN.exists():
            raise FileNotFoundError(f"wireproxy binary not found at {WIREPROXY_BIN}")
        if not WG_KEY_BIN.exists():
             logger.warning(f"wg.exe not found at {WG_KEY_BIN}. Trying 'wg' from PATH...")

    def generate_keys(self):
        try:
            exe = str(WG_KEY_BIN) if WG_KEY_BIN.exists() else "wg"
            privkey = subprocess.check_output([exe, "genkey"]).decode().strip()
            pubkey = subprocess.check_output([exe, "pubkey"], input=privkey.encode()).decode().strip()
            return privkey, pubkey
        except Exception as e:
            raise Exception(f"Failed to generate keys: {e}. Is WireGuard installed?") from e

    def get_lease(self, pubkey):
        try:
            resp = self.session.post(API_URL, json={"pubkey": pubkey}, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            raise Exception(f"Failed to get lease: {e}") from e

    def create_config(self, lease, privkey):
        config = f"""[Interface]
                PrivateKey = {privkey}
                Address = {lease['address']}
                DNS = 8.8.8.8, 2606:4700:4700::1111
                MTU = {lease['mtu']}
                [Peer]
                PublicKey = {lease['peer_pubkey']}
                Endpoint = {lease['endpoint']}
                AllowedIPs = ::/0
                PersistentKeepalive = 25
                [Socks5]
                BindAddress = {PROXY_HOST}:{PROXY_PORT}
                [Http]
                BindAddress = {PROXY_HOST}:{HTTP_PROXY_PORT}
                """
        self.conf_path.write_text(config, encoding="utf-8")
        return self.conf_path
    
    def start_proxy(self):
        logger.info(f"Starting WireProxy on 127.0.0.1:{PROXY_PORT}...")
        if self.proxy_log_file:
            try:
                self.proxy_log_file.close()
            except Exception:
                pass
        self.proxy_log_file = open(PROJECT_ROOT / "wireproxy.log", "w")
        cmd = [str(WIREPROXY_BIN), "--config", str(self.conf_path)]
        self.proxy_process = subprocess.Popen(cmd, stdout=self.proxy_log_file, stderr=self.proxy_log_file)
        sleep(1)
        if self.proxy_process.poll() is not None:
            raise Exception(f"WireProxy failed to start. Exit code={self.proxy_process.returncode}")
        else:
             logger.info("Proxy is running.")

    def stop_proxy(self):
        try:
            subprocess.run(["pkill", "-9", "wireproxy"], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        except Exception:
            pass
        if self.proxy_process:
            logger.info("Stopping proxy...")
            self.proxy_process.terminate()
            try:
                self.proxy_process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.proxy_process.kill()
            self.proxy_process = None
        if self.proxy_log_file:
            try:
                self.proxy_log_file.close()
            except Exception:
                pass
            self.proxy_log_file = None

    def rotate_ip(self):
        self.stop_proxy()
        priv, pub = self.generate_keys()
        lease = self.get_lease(pub)
        self.create_config(lease, priv)
        self.start_proxy()
        logger.info(f"ROTATION COMPLETE. New IP: {lease['address']}")

_client = None

def signal_handler(sig, frame):
    global _client
    if _client:
        _client.stop_proxy()
    sys.exit(0)

if __name__ == "__main__":
    setup_logging(log_dir=LOG_DIR, app_name="WireProxy")
    signal.signal(signal.SIGINT, signal_handler)
    try:
        _client = VPNProxyClient()
        _client.rotate_ip()
        logger.info("Press Enter to rotate IP, or Ctrl+C to exit.")
        while True:
            input()
            _client.rotate_ip()
    except Exception as e:
        logger.error(f"Error: {e}")
        if _client:
            _client.stop_proxy()

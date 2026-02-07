import os
import sys
import time
import subprocess
import requests
import signal
import logging
from pathlib import Path
API_URL = "http://65.108.211.167:8000/connect"
PROXY_PORT = 1080
PROJECT_ROOT = Path("/home/tbag/Desktop/Workspace/instagram-masscreation")
WIREPROXY_BIN = PROJECT_ROOT / "bin" / "wireproxy"
WG_KEY_BIN = Path("/usr/bin/wg")
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ProxyClient")
class VPNProxyClient:
    def __init__(self):
        self.proxy_process = None
        self.conf_path = Path("wireproxy.conf")
        if not WIREPROXY_BIN.exists():
            logger.error(f"wireproxy binary not found at {WIREPROXY_BIN}")
            sys.exit(1)
        if not WG_KEY_BIN.exists():
             logger.warning(f"wg.exe not found at {WG_KEY_BIN}. Trying 'wg' from PATH...")
    def generate_keys(self):
        """Generate a fresh Curve25519 keypair using wg.exe."""
        try:
            exe = str(WG_KEY_BIN) if WG_KEY_BIN.exists() else "wg"
            privkey = subprocess.check_output([exe, "genkey"]).decode().strip()
            pubkey = subprocess.check_output([exe, "pubkey"], input=privkey.encode()).decode().strip()
            return privkey, pubkey
        except Exception as e:
            logger.error(f"Failed to generate keys: {e}. Is WireGuard installed?")
            sys.exit(1)
    def get_lease(self, pubkey):
        """Request a new IP lease from the server."""
        try:
            resp = requests.post(API_URL, json={"pubkey": pubkey}, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"Failed to get lease: {e}")
            raise
    def create_config(self, lease, privkey):
        """Create a WireProxy config file."""
        config = f"""
            [Interface]
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
            BindAddress = 127.0.0.1:{PROXY_PORT}
            [Http]
            BindAddress = 127.0.0.1:1081
            """
        with open(self.conf_path, "w") as f:
            f.write(config)
        return self.conf_path
    def start_proxy(self):
        """Start wireproxy."""
        logger.info(f"Starting WireProxy on 127.0.0.1:{PROXY_PORT}...")
        cmd = [str(WIREPROXY_BIN), "--config", str(self.conf_path)]
        self.proxy_process = subprocess.Popen(cmd)
        time.sleep(1)
        if self.proxy_process.poll() is not None:
             logger.error("WireProxy failed to start.")
        else:
             logger.info("Proxy is running.")
    def stop_proxy(self):
        # Aggressively kill any existing wireproxy processes to free up ports
        try:
            subprocess.run(["pkill", "-9", "wireproxy"], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        except:
            pass
        if self.proxy_process:
            logger.info("Stopping proxy...")
            self.proxy_process.terminate()
            try:
                self.proxy_process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.proxy_process.kill()
            self.proxy_process = None
    def rotate_ip(self):
        self.stop_proxy()
        priv, pub = self.generate_keys()
        lease = self.get_lease(pub)
        self.create_config(lease, priv)
        self.start_proxy()
        logger.info(f"ROTATION COMPLETE. New IP: {lease['address']}")
client = VPNProxyClient()
def signal_handler(sig, frame):
    client.stop_proxy()
    sys.exit(0)
if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    try:
        client.rotate_ip()
        logger.info("Press Enter to rotate IP, or Ctrl+C to exit.")
        while True:
            input()
            client.rotate_ip()
    except Exception as e:
        logger.error(f"Error: {e}")
        client.stop_proxy()

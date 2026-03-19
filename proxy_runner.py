from pathlib import Path
from subprocess import DEVNULL, Popen, TimeoutExpired, check_output, run
from time import sleep
import requests

from config import API_URL, PROXY_HOST, WIREPROXY_BIN, WG_KEY_BIN
from logger_config import get_logger
from session import SessionContext

logger = get_logger("ProxyClient")

class VPNProxyClient:

    def __init__(self, session: SessionContext):
        self.ctx = session
        self.proxy_process = None
        self.proxy_log_file = None
        self.session_dir = session.runtime_dir
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.conf_path = self.session_dir / "wireproxy.conf"
        self.log_path = self.session_dir / "wireproxy.log"
        # Android's Bionic DNS resolver ignores /etc/hosts, so host.docker.internal fails.
        # We must use the direct Docker bridge gateway IP (usually 172.17.0.1).
        self.session_http_proxy = f"172.17.0.1:{self.ctx.http_proxy_port}"
        self.session_socks_proxy = f"172.17.0.1:{self.ctx.socks_port}"
        self.http = requests.Session()
        if not WIREPROXY_BIN.exists():
            raise FileNotFoundError(f"wireproxy binary not found at {WIREPROXY_BIN}")

    def generate_keys(self):
        exe = str(WG_KEY_BIN) if WG_KEY_BIN.exists() else "wg"
        privkey = check_output([exe, "genkey"], text=True).strip()
        pubkey = check_output([exe, "pubkey"], input=privkey, text=True).strip()
        return privkey, pubkey

    def get_lease(self, pubkey):
        resp = self.http.post(API_URL, json={"pubkey": pubkey}, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def create_config(self, lease, privkey):
        # We must bind to 0.0.0.0 so the docker container (on a bridge network)
        # can reach the host-gateway IP that wireproxy is listening on.
        #
        # IPv6 ROUTING FIX:
        # The lease gives us a unique IPv6 from the Finland server.
        # By routing ALL traffic through the tunnel (::/0 and 0.0.0.0/0),
        # outbound connections use the assigned IPv6 as source.
        # DNS must list IPv6 resolver FIRST so DNS lookups go IPv6 and
        # reveal the Finland IPv6, not the Ukraine IPv4.
        config = (
            "[Interface]\n"
            f"PrivateKey = {privkey}\n"
            f"Address = {lease['address']}\n"
            # IPv6-first DNS: Cloudflare IPv6 first, then fallback to IPv4
            "DNS = 2606:4700:4700::1111, 2606:4700:4700::1001, 1.1.1.1\n"
            f"MTU = {lease['mtu']}\n"
            "[Peer]\n"
            f"PublicKey = {lease['peer_pubkey']}\n"
            f"Endpoint = {lease['endpoint']}\n"
            # Route ALL traffic through VPN (both IPv4 and IPv6)
            "AllowedIPs = 0.0.0.0/0, ::/0\n"
            "PersistentKeepalive = 25\n"
            "[Socks5]\n"
            f"BindAddress = 0.0.0.0:{self.ctx.socks_port}\n"
            "[Http]\n"
            f"BindAddress = 0.0.0.0:{self.ctx.http_proxy_port}\n"
        )
        self.conf_path.write_text(config, encoding="utf-8")
        return self.conf_path

    def start_proxy(self):
        logger.info(
            f"[{self.ctx.session_id}] Starting WireProxy "
            f"socks={PROXY_HOST}:{self.ctx.socks_port} "
            f"http={PROXY_HOST}:{self.ctx.http_proxy_port}")
        self.stop_proxy()
        self.proxy_log_file = open(self.log_path, "w", encoding="utf-8")
        cmd = [str(WIREPROXY_BIN), "--config", str(self.conf_path)]
        self.proxy_process = Popen(cmd, stdout=self.proxy_log_file,
                                    stderr=self.proxy_log_file)
        sleep(1.0)
        if self.proxy_process.poll() is not None:
            raise Exception(
                f"WireProxy failed to start for session {self.ctx.session_id}. "
                f"exit_code={self.proxy_process.returncode}")
        logger.info(f"[{self.ctx.session_id}] Proxy is running (pid={self.proxy_process.pid})")

    def stop_proxy(self):
        if self.proxy_process:
            logger.info(f"[{self.ctx.session_id}] Stopping WireProxy (pid={self.proxy_process.pid})")
            try:
                self.proxy_process.terminate()
                try:
                    self.proxy_process.wait(timeout=3)
                except TimeoutExpired:
                    self.proxy_process.kill()
                    self.proxy_process.wait(timeout=4)
            except Exception:
                pass
            finally:
                self.proxy_process = None
        if self.proxy_log_file:
            try:
                self.proxy_log_file.close()
            except Exception:
                pass
            finally:
                self.proxy_log_file = None

    def rotate_ip(self):
        self.stop_proxy()
        priv, pub = self.generate_keys()
        lease = self.get_lease(pub)
        self.create_config(lease, priv)
        self.start_proxy()
        logger.info(f"[{self.ctx.session_id}] IP rotated. New lease: {lease['address']}")

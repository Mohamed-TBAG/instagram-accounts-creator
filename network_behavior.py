import requests
import logging
import uuid
import time
import random
import hmac
import hashlib
import base64
import json
from config import PROXY_HOST, PROXY_PORT
logger = logging.getLogger("NetworkBehavior")

class NetworkBehavior:
    def __init__(self, device_manager):
        self.dm = device_manager
        self.fingerprint = self.dm.get_device_fingerprint()
        self.session = requests.Session()
        proxy_url = f"socks5://{PROXY_HOST}:{PROXY_PORT}"
        self.session.proxies = {
            "http": proxy_url,
            "https": proxy_url}
        self.base_headers = {
            "Accept-Language": "en-US",
            "X-Fb-Client-Ip": "True",
            "X-Fb-Server-Cluster": "True",
            "X-Ig-App-Id": "567067343352427",
            "X-Ig-Connection-Type": "WIFI",
            "X-Ig-Capabilities": "3brTv10=",
            "User-Agent": self._construct_user_agent(),
            "X-Fb-Http-Engine": "Tigon/MNS/TCP",
            "X-Fb-Rmd": "state=URL_ELIGIBLE"}

    def _construct_user_agent(self):
        model = self.fingerprint["ro.product.model"] 
        return f"Instagram 415.0.0.36.76 Android (30/11; 440dpi; 1080x2340; Google/exclude; {model}; generic_x86_64_arm64; ranchu; en_US; 874816550)"

    def _get_common_headers(self):
        headers = self.base_headers.copy()
        headers["X-Meta-Usdid"] = str(uuid.uuid4())
        headers["X-Fb-Conn-Uuid-Client"] = uuid.uuid4().hex
        headers["X-Pigeon-Rawclienttime"] = str(time.time())
        headers["X-Pigeon-Session-Id"] = f"UFS-{uuid.uuid4()}-1"
        return headers

    def send_pigeon_log(self, event_name="app_start"):
        url = "https://graph.instagram.com/pigeon_nest"
        headers = self._get_common_headers()
        headers["Content-Type"] = "multipart/form-data; boundary=boundary123"
        headers["X-Fb-Friendly-Name"] = "undefined:analytics"
        body = (
            "--boundary123\r\n"
            "Content-Disposition: form-data; name=\"access_token\"\r\n\r\n"
            "567067343352427|f249176f09e26ce54212b472dbab8fa8\r\n"
            "--boundary123\r\n"
            "Content-Disposition: form-data; name=\"cmsg\"; filename=\"cmsg\"\r\n"
            "Content-Type: application/octet-stream\r\n\r\n"
            "\x1f\x8b\x08\x00\x00\x00\x00\x00\x00\x00\x03\xcb\x4b\xcd\x2b\x29\x67\x60\x60\x60\x00\x00\x2d\x3a\x07\x3a\x09\x00\x00\x00" 
            "\r\n--boundary123--\r\n")
        try:
            logger.info(f"📡 Sending Pigeon Log ({event_name})...")
            resp = self.session.post(url, headers=headers, data=body, timeout=10, verify=False) # verify=False for Charles/Burp if needed, else True
            logger.info(f"  ✓ Pigeon Response: {resp.status_code}")
            return True
        except Exception as e:
            logger.warning(f"  ⚠️ Pigeon Log Failed: {e}")
            return False

    def send_launcher_sync(self):
        url = "https://i.instagram.com/api/v1/launcher/sync/"
        headers = self._get_common_headers()
        headers["X-Ig-Device-Id"] = self.fingerprint["guid"]
        headers["X-Ig-Android-Id"] = self.fingerprint["android_id"]
        data = {
            "configs": "ig_android_launcher_sync_config",
            "id": self.fingerprint["guid"]}
        try:
            logger.info("📡 Sending Launcher Sync...")
            resp = self.session.post(url, headers=headers, data=data, timeout=10)
            logger.info(f"  ✓ Launcher Response: {resp.status_code}")
            return True
        except Exception as e:
            logger.warning(f"  ⚠️ Launcher Sync Failed: {e}")
            return False

    def send_prefill_check(self):
        url = "https://i.instagram.com/api/v1/accounts/contact_point_prefill/"
        headers = self._get_common_headers()
        headers["X-Ig-Device-Id"] = self.fingerprint["guid"]
        data = {
            "phone_id": self.fingerprint["phone_id"],
            "_uuid": self.fingerprint["guid"],
            "usage": "prefill"}
        try:
            logger.info("📡 Sending Contact Prefill Check...")
            resp = self.session.post(url, headers=headers, data=data, timeout=10)
            logger.info(f"  ✓ Prefill Response: {resp.status_code}")
            return True
        except Exception as e:
            logger.warning(f"  ⚠️ Prefill Check Failed: {e}")
            return False

    def send_qe_sync(self):
        url = "https://i.instagram.com/api/v1/qe/sync/"
        headers = self._get_common_headers()
        headers["X-Ig-Device-Id"] = self.fingerprint["guid"]
        data = {
            "id": self.fingerprint["guid"],
            "experiments": "ig_android_growth_fx_refactor"}
        try:
            logger.info("📡 Sending QE Sync...")
            resp = self.session.post(url, headers=headers, data=data, timeout=10)
            logger.info(f"  ✓ QE Sync Response: {resp.status_code}")
            return True
        except Exception as e:
            logger.warning(f"  ⚠️ QE Sync Failed: {e}")
            return False

    def send_mock_browser_request(self):
        try:
            logger.info("🌍 Sending Browser Connectivity Check...")
            headers = {
                "User-Agent": "Mozilla/5.0 (Linux; Android 11; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.104 Mobile Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
            }
            self.session.get("https://www.instagram.com/", headers=headers, timeout=10)
            logger.info("  ✓ Browser Check OK")
        except:
            pass

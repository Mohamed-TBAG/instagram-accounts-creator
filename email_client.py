import logging
import random
import re
import string
import time
import requests
logger = logging.getLogger("EmailClient")
EMAIL_API_BASE = "http://65.108.211.167"
EMAIL_API_KEY = "Pp66778899_Secure_Email_Access"
EMAIL_DOMAIN = "iraqimail.com"
CODE_PATTERN = re.compile(r'\b(\d{6})\b')

class EmailClient:

    def __init__(self, api_base=EMAIL_API_BASE, api_key=EMAIL_API_KEY, domain=EMAIL_DOMAIN):
        self.api_base = api_base.rstrip("/")
        self.api_key = api_key
        self.domain = domain
        self.session = requests.Session()
        self.session.headers["X-API-Key"] = self.api_key

    def generate_email(self) -> str:
        prefix = "user_" + "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
        email = f"{prefix}@{self.domain}"
        logger.info(f"Generated email: {email}")
        return email

    def poll_for_code(self, alias: str, timeout: int = 90, interval: float = 5.0) -> str:
        alias_name = alias.split("@")[0]
        url = f"{self.api_base}/api/emails"
        deadline = time.time() + timeout
        attempt = 0
        while time.time() < deadline:
            attempt += 1
            resp = self.session.get(url, params={"alias": alias_name, "limit": 5}, timeout=10)
            resp.raise_for_status()
            emails = resp.json()
            if emails:
                for email in emails:
                    subject = email.get("subject", "")
                    body = email.get("body", "") or email.get("snippet", "")
                    match = CODE_PATTERN.search(subject) or CODE_PATTERN.search(body)
                    if match:
                        code = match.group(1)
                        email_id = email.get("id")
                        logger.info(f"Verification code found: {code} (attempt {attempt})")
                        if email_id:
                            self._delete_email(email_id)
                        return code
            remaining = round(deadline - time.time(), 0)
            logger.debug(f"No code yet for {alias_name}, retrying in {interval}s ({remaining}s left)")
            time.sleep(interval)
        raise TimeoutError(f"No verification code received for {alias_name} within {timeout}s")

    def _delete_email(self, email_id: int):
        resp = self.session.delete(f"{self.api_base}/api/emails/{email_id}", timeout=10)
        resp.raise_for_status()
        logger.debug(f"Deleted email {email_id}")

    def get_stats(self) -> dict:
        resp = self.session.get(f"{self.api_base}/api/stats", timeout=10)
        resp.raise_for_status()
        return resp.json()

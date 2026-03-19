from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import subprocess
import os
import random
import ipaddress
import sqlite3
import logging
import base64

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("/root/backend_debug.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def _device_exists(dev: str) -> bool:
    try:
        res = subprocess.run(["ip", "link", "show", dev], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return res.returncode == 0
    except Exception:
        return False


def _ensure_wg0_up() -> bool:
    """Return True if wg0 exists (or was brought up), False otherwise."""
    if _device_exists("wg0"):
        return True
    logger.info("wg0 device not found; attempting to bring up wg0 via wg-quick")
    try:
        res = subprocess.run(["wg-quick", "up", "/etc/wireguard/wg0"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res.returncode != 0:
            logger.error(f"wg-quick up failed: {res.stderr.strip()}")
            return False
        # give kernel a moment to create interface
        import time
        time.sleep(0.5)
        return _device_exists("wg0")
    except Exception as e:
        logger.exception("Exception while trying to bring up wg0: %s", e)
        return False

app = FastAPI()

# --- Configuration ---
WG_CONF_PATH = "/etc/wireguard/wg0.conf"
SERVER_PUB_KEY = "8aZGWqJ6dOVI3JalyhpuIiwmXNJT6XhRmGsii9LU/Us="
SERVER_ENDPOINT = "195.138.76.179:51820"
BASE_IPV6 = "2a01:4f9:c010:91e9:f000::/68"
DB_PATH = "/root/backend/api/wg_users.db"

class ConnectRequest(BaseModel):
    pubkey: str

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (pubkey TEXT PRIMARY KEY, ipv4 TEXT, ipv6 TEXT)''')
    conn.commit()
    conn.close()

init_db()


def wg0_exists() -> bool:
    """Return True if interface wg0 exists."""
    try:
        res = subprocess.run(["/sbin/ip", "link", "show", "wg0"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return res.returncode == 0
    except Exception:
        return False


def ensure_wg0(timeout: int = 5) -> bool:
    """Ensure wg0 exists; try to start wg-quick@wg0 if missing. Returns True if wg0 exists.

    This is a best-effort helper to avoid crashing the API when the WireGuard
    interface is not up (for example after a reboot or when wg-quick hasn't been
    enabled)."""
    if wg0_exists():
        return True

    logger.warning("wg0 interface not found, attempting to start wg-quick@wg0")
    try:
        subprocess.run("systemctl start wg-quick@wg0", shell=True, check=False)
    except Exception as e:
        logger.exception("Failed to start wg-quick@wg0: %s", e)

    # Re-check
    return wg0_exists()

def get_next_ips():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # IPv4: Find max and increment
    c.execute("SELECT ipv4 FROM users")
    existing_v4s = {row[0] for row in c.fetchall()}
    
    next_v4 = None
    for i in range(2, 255):
        candidate = f"10.0.0.{i}"
        if candidate not in existing_v4s:
            next_v4 = candidate
            break
            
    if not next_v4:
        next_v4 = "10.0.0.254" 
    
    # IPv6: Randomize suffix
    network = ipaddress.IPv6Network(BASE_IPV6)
    c.execute("SELECT ipv6 FROM users")
    existing_v6s = {row[0] for row in c.fetchall()}
    
    while True:
        # Generate random suffix within available bits
        available_bits = 128 - network.prefixlen
        rand_suffix = random.getrandbits(available_bits)
        candidate_int = int(network.network_address) + rand_suffix
        next_v6 = str(ipaddress.IPv6Address(candidate_int))
        
        # Avoid gateway/network addresses and existing ones
        # We also want to skip the server's own IPs if possible
        if next_v6.endswith("::1"): continue
        if next_v6 == str(network.network_address): continue
        if next_v6 in existing_v6s: continue
        
        break
            
    conn.close()
    return next_v4, next_v6

def add_vpn_user(pubkey, ipv4, ipv6):
    # 1. Update WireGuard Config File (Persistence)
    # Note: This is a simple append. In production, you'd manage peers better.
    peer_block = f"\n[Peer]\n# Added via API\nPublicKey = {pubkey}\nAllowedIPs = {ipv4}/32, {ipv6}/128\n"
    with open(WG_CONF_PATH, "a") as f:
        f.write(peer_block)
    
    # 2-4. Add to live interface, route and NDP proxy if wg0 is present.
    if ensure_wg0():
        try:
            subprocess.run(f"wg set wg0 peer {pubkey} allowed-ips {ipv4}/32,{ipv6}/128", shell=True, check=False)
        except Exception:
            logger.exception("wg set failed for peer %s", pubkey)

        try:
            subprocess.run(f"ip -6 route add {ipv6}/128 dev wg0 metric 50", shell=True, check=False)
        except Exception:
            logger.exception("ip -6 route add failed for %s", ipv6)

        try:
            subprocess.run(f"ip -6 neigh add proxy {ipv6} dev enp6s18", shell=True, check=False)
        except Exception:
            # This can fail if already exists; log and continue.
            logger.exception("ip -6 neigh add proxy failed for %s", ipv6)
    else:
        logger.warning("Skipping live interface configuration for %s because wg0 is not available", pubkey)
    
    logger.info(f"Activated Peer: PubKey={pubkey} IPv4={ipv4} IPv6={ipv6}")

@app.post("/connect")
async def connect(req: ConnectRequest):
    pubkey = req.pubkey
    logger.info(f"Request from PubKey: {pubkey}")
    
    # Validate WireGuard public key: must be valid base64 and decode to 32 bytes
    if not pubkey:
        raise HTTPException(status_code=400, detail="Invalid Public Key")
    try:
        decoded = base64.b64decode(pubkey, validate=True)
        if len(decoded) != 32:
            raise ValueError("invalid length")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid Public Key format")

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT ipv4, ipv6 FROM users WHERE pubkey=?", (pubkey,))
    row = c.fetchone()
    
    if row:
        ipv4, ipv6 = row
        # Ensure it's active in the live interface even if it was in the DB
        # (Handles server restarts)
        if ensure_wg0():
            try:
                subprocess.run(f"wg set wg0 peer {pubkey} allowed-ips {ipv4}/32,{ipv6}/128", shell=True, check=False)
            except Exception:
                logger.exception("wg set failed re-activating %s", pubkey)

            try:
                subprocess.run(f"ip -6 route add {ipv6}/128 dev wg0 metric 50", shell=True, check=False)
            except Exception:
                logger.exception("ip -6 route add failed for %s", ipv6)

            try:
                subprocess.run(f"ip -6 neigh add proxy {ipv6} dev enp6s18", shell=True, check=False)
            except Exception:
                logger.exception("ip -6 neigh add proxy failed for %s", ipv6)
        else:
            logger.warning("wg0 missing; persisted peer will be activated later: %s", pubkey)
        logger.info(f"Re-activated existing user: {ipv4}, {ipv6}")
    else:
        ipv4, ipv6 = get_next_ips()
        c.execute("INSERT INTO users VALUES (?, ?, ?)", (pubkey, ipv4, ipv6))
        conn.commit()
        add_vpn_user(pubkey, ipv4, ipv6)
    
    conn.close()
    
    return {
        "address": f"{ipv4}/32, {ipv6}/128",
        "peer_pubkey": SERVER_PUB_KEY,
        "endpoint": SERVER_ENDPOINT,
        "dns": "1.1.1.1, 2606:4700:4700::1111",
        "mtu": 1360
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
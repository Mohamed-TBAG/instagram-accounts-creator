from os import environ, getenv
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.resolve()


def _load_dotenv(dotenv_path):
    if not dotenv_path.exists():
        return
    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        environ.setdefault(key, value)


_load_dotenv(PROJECT_ROOT / ".env")


def _env_path(name, default):
    raw = getenv(name, str(default)).strip()
    return Path(raw).expanduser()


def _env_str(name, default):
    raw = getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip()


def _env_int(name, default, min_value=None, max_value=None):
    raw = getenv(name)
    if raw is None or raw.strip() == "":
        value = default
    else:
        try:
            value = int(raw)
        except ValueError as e:
            raise ValueError(f"{name} must be an integer, got '{raw}'") from e
    if min_value is not None and value < min_value:
        raise ValueError(f"{name} must be >= {min_value}, got {value}")
    if max_value is not None and value > max_value:
        raise ValueError(f"{name} must be <= {max_value}, got {value}")
    return value


def _env_float(name, default, min_value=None):
    raw = getenv(name)
    if raw is None or raw.strip() == "":
        value = default
    else:
        try:
            value = float(raw)
        except ValueError as e:
            raise ValueError(f"{name} must be a float, got '{raw}'") from e
    if min_value is not None and value < min_value:
        raise ValueError(f"{name} must be >= {min_value}, got {value}")
    return value


def _env_bool(name, default=False):
    raw = getenv(name)
    if raw is None or raw.strip() == "":
        return default
    value = raw.strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be boolean-like, got '{raw}'")


PROJECT_BIN = PROJECT_ROOT / "bin"
LOG_DIR = PROJECT_ROOT / "logs"

ADB_BIN = _env_path("ADB_BIN", "/home/tbag/android-sdk/platform-tools/adb")
WG_KEY_BIN = _env_path("WG_KEY_BIN", "/usr/bin/wg")
WIREPROXY_CONF = PROJECT_ROOT / "wireproxy.conf"
WIREPROXY_BIN = _env_path("WIREPROXY_BIN", PROJECT_BIN / "wireproxy")

APPIUM_SERVER_HOST = _env_str("APPIUM_SERVER_HOST", "127.0.0.1")
APPIUM_SERVER_PORT = _env_int("APPIUM_SERVER_PORT", 4723, 1, 65535)
APPIUM_SERVER_URL = _env_str("APPIUM_SERVER_URL", f"http://{APPIUM_SERVER_HOST}:{APPIUM_SERVER_PORT}")
APPIUM_CONNECT_TIMEOUT = _env_int("APPIUM_CONNECT_TIMEOUT", 5, 1, 120)

REDROID_IMAGE    = _env_str("REDROID_IMAGE",    "redroid/redroid:11.0.0-latest")
REDROID_GPU_MODE = _env_str("REDROID_GPU_MODE", "guest").lower()
REDROID_WIDTH = _env_int("REDROID_WIDTH", 720, 320, 4096)
REDROID_HEIGHT = _env_int("REDROID_HEIGHT", 1280, 320, 4096)
REDROID_DPI = _env_int("REDROID_DPI", 320, 120, 640)
REDROID_FPS = _env_int("REDROID_FPS", 30, 10, 120)
REDROID_AUDIT_ENABLED   = _env_bool("REDROID_AUDIT_ENABLED", True)
REDROID_VERIFY_STRICT   = _env_bool("REDROID_VERIFY_STRICT", True)
GAID_DISCOVERY_ENABLED = _env_bool("GAID_DISCOVERY_ENABLED", True)
GAID_RESET_ON_BOOT = _env_bool("GAID_RESET_ON_BOOT", False)
GAID_DISCOVERY_TIMEOUT = _env_int("GAID_DISCOVERY_TIMEOUT", 20, 5, 120)
IDENTITY_GATE_MODE = _env_str("IDENTITY_GATE_MODE", "warn").lower()
if IDENTITY_GATE_MODE not in {"off", "warn", "fail"}:
    raise ValueError("IDENTITY_GATE_MODE must be one of: off, warn, fail")

API_URL = _env_str("API_URL", "http://195.138.76.179:8000/connect")
PROXY_HOST = _env_str("PROXY_HOST", "127.0.0.1")
PROXY_PORT = _env_int("PROXY_PORT", 1080, 1, 65535)
HTTP_PROXY_PORT = _env_int("HTTP_PROXY_PORT", 1081, 1, 65535)
DEVICE_PROXY_ADDRESS = _env_str("DEVICE_PROXY_ADDRESS", "10.0.2.2:1081")

INSTAGRAM_PACKAGE = _env_str("INSTAGRAM_PACKAGE", "com.instagram.android")
INSTAGRAM_LOGIN_URL = _env_str("INSTAGRAM_LOGIN_URL", "https://www.instagram.com/accounts/login/")
AUTOMATION_LOCALE = _env_str("AUTOMATION_LOCALE", "en-US")
GALLERY_PHOTO_NAME = "selfie.jpg"
GALLERY_PHOTO_DEST = "/sdcard/Pictures/selfie.jpg"

MAX_ERRORS = _env_int("MAX_ERRORS", 10, 1, 1000)
MAX_RETRIES = _env_int("MAX_RETRIES", 3, 0, 100)
RETRY_DELAY = _env_float("RETRY_DELAY", 2.0, 0.0)
ALLOW_FORCE_KILL = _env_bool("ALLOW_FORCE_KILL", False)
ADB_DEFAULT_TIMEOUT = _env_int("ADB_DEFAULT_TIMEOUT", 60, 1, 600)
BOOT_TIMEOUT = _env_int("BOOT_TIMEOUT", 60, 10, 1800)
UI_ELEMENT_TIMEOUT = _env_int("UI_ELEMENT_TIMEOUT", 15, 1, 300)

DEVICE_PROFILES = [
    {
        "manufacturer": "Google",
        "brand": "google",
        "model": "Pixel 6",
        "name": "oriole",
        "device": "oriole",
        "board": "gs101",
        "platform": "gs101",
        "hardware": "gs101",
        "density": 420,
        "resolution": "1080x1920",
        "timezones": ["America/New_York", "America/Los_Angeles", "America/Chicago", "Europe/London", "Europe/Paris"],
        "locales":   ["en-US", "en-GB", "fr-FR", "de-DE"],
    },
    {
        "manufacturer": "Samsung",
        "brand": "samsung",
        "model": "SM-S901B",
        "name": "r0qxx",
        "device": "r0q",
        "board": "exynos2200",
        "platform": "exynos2200",
        "hardware": "samsungexynos2200",
        "density": 420,
        "resolution": "1080x2340",
        "timezones": ["Europe/Berlin", "Europe/Istanbul", "Europe/Warsaw", "Asia/Riyadh", "Africa/Cairo"],
        "locales":   ["de-DE", "tr-TR", "pl-PL", "ar-SA", "ar-EG"],
    },
    {
        "manufacturer": "OnePlus",
        "brand": "OnePlus",
        "model": "LE2115",
        "name": "OnePlus9",
        "device": "OnePlus9",
        "board": "kona",
        "platform": "kona",
        "hardware": "qcom",
        "density": 402,
        "resolution": "1080x1920",
        "timezones": ["Asia/Kolkata", "Asia/Dubai", "Europe/Amsterdam", "Asia/Riyadh"],
        "locales":   ["en-IN", "ar-AE", "nl-NL", "ar-SA"],
    },
    {
        "manufacturer": "Xiaomi",
        "brand": "Xiaomi",
        "model": "M2011K2C",
        "name": "venus",
        "device": "venus",
        "board": "sm8350",
        "platform": "lahaina",
        "hardware": "qcom",
        "density": 395,
        "resolution": "1080x1920",
        "timezones": ["Asia/Shanghai", "Asia/Kolkata", "Europe/Rome", "Asia/Dubai", "Africa/Cairo"],
        "locales":   ["zh-CN", "en-IN", "it-IT", "ar-AE", "ar-EG"],
    },
    {
        "manufacturer": "OPPO",
        "brand": "OPPO",
        "model": "CPH2251",
        "name": "RENO6",
        "device": "RENO6",
        "board": "mt6877",
        "platform": "mt6877",
        "hardware": "mt6877",
        "density": 411,
        "resolution": "1080x1920",
        "timezones": ["Asia/Jakarta", "Asia/Bangkok", "Asia/Karachi", "Africa/Lagos", "Asia/Riyadh"],
        "locales":   ["id-ID", "th-TH", "ur-PK", "en-NG", "ar-SA"],
    },
]

import os
from pathlib import Path
def _env_path(name, default):
    raw = os.getenv(name, str(default))
    return Path(raw).expanduser()
AVD_NAME = os.getenv("AVD_NAME", "Pixel_6")
AVD_BASE_DIR = _env_path("AVD_BASE_DIR", "/home/tbag/.android/avd")
SDK_EMULATOR_BIN = _env_path("SDK_EMULATOR_BIN", "/home/tbag/android-sdk/emulator/emulator")
ADB_BIN = _env_path("ADB_BIN", "/home/tbag/android-sdk/platform-tools/adb")
PROJECT_ROOT = Path(__file__).parent.resolve()
PROJECT_BIN = PROJECT_ROOT / "bin"
WIREPROXY_CONF = PROJECT_ROOT / "wireproxy.conf"
WIREPROXY_BIN = _env_path("WIREPROXY_BIN", PROJECT_BIN / "wireproxy")
LOG_DIR = PROJECT_ROOT / "logs"
APPIUM_SERVER_URL = 'http://127.0.0.1:4723'
APPIUM_SERVER_HOST = '127.0.0.1'
APPIUM_SERVER_PORT = 4723
API_URL = os.getenv("API_URL", "http://65.108.211.167:8000/connect")
PROXY_PORT = int(os.getenv("PROXY_PORT", "1080"))
PROXY_HOST = os.getenv("PROXY_HOST", "127.0.0.1")
HTTP_PROXY_PORT = int(os.getenv("HTTP_PROXY_PORT", "1081"))
WG_KEY_BIN = _env_path("WG_KEY_BIN", "/usr/bin/wg")
INSTAGRAM_PACKAGE = os.getenv("INSTAGRAM_PACKAGE", "com.instagram.android")
INSTAGRAM_LOGIN_URL = os.getenv("INSTAGRAM_LOGIN_URL", "https://www.instagram.com/accounts/login/")
GALLERY_PHOTO_NAME = "selfie.jpg"
GALLERY_PHOTO_DEST = "/sdcard/Pictures/selfie.jpg"
DEVICE_PROXY_ADDRESS = os.getenv("DEVICE_PROXY_ADDRESS", "10.0.2.2:1081")  
MAX_ERRORS = int(os.getenv("MAX_ERRORS", "10"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
RETRY_DELAY = float(os.getenv("RETRY_DELAY", "2")) 
ALLOW_FORCE_KILL = os.getenv("ALLOW_FORCE_KILL", "0") == "1"
ADB_DEFAULT_TIMEOUT = int(os.getenv("ADB_DEFAULT_TIMEOUT", "60"))
BOOT_TIMEOUT = int(os.getenv("BOOT_TIMEOUT", "60"))
UI_ELEMENT_TIMEOUT = int(os.getenv("UI_ELEMENT_TIMEOUT", "15"))
APPIUM_CONNECT_TIMEOUT = int(os.getenv("APPIUM_CONNECT_TIMEOUT", "5"))
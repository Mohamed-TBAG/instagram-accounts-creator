"""
Configuration file for Instagram Mass Creation project.
Centralized configuration for paths, URLs, and settings.
"""
from pathlib import Path

# ============================================================================
# ANDROID/EMULATOR CONFIGURATION
# ============================================================================
AVD_NAME = "Pixel_6"
AVD_BASE_DIR = Path("/home/tbag/.android/avd")
SDK_EMULATOR_BIN = Path("/home/tbag/android-sdk/emulator/emulator")
ADB_BIN = Path("/home/tbag/android-sdk/platform-tools/adb")

# ============================================================================
# PROJECT CONFIGURATION
# ============================================================================
PROJECT_ROOT = Path(__file__).parent.resolve()
PROJECT_BIN = PROJECT_ROOT / "bin"
WIREPROXY_CONF = PROJECT_ROOT / "wireproxy.conf"
WIREPROXY_BIN = PROJECT_BIN / "wireproxy"

# ============================================================================
# APPIUM CONFIGURATION
# ============================================================================
APPIUM_SERVER_URL = 'http://127.0.0.1:4723'
APPIUM_SERVER_HOST = '127.0.0.1'
APPIUM_SERVER_PORT = 4723

# ============================================================================
# PROXY CONFIGURATION
# ============================================================================
API_URL = "http://65.108.211.167:8000/connect"
PROXY_PORT = 1080
PROXY_HOST = "127.0.0.1"
HTTP_PROXY_PORT = 1081
WG_KEY_BIN = Path("/usr/bin/wg")

# ============================================================================
# INSTAGRAM CONFIGURATION
# ============================================================================
INSTAGRAM_PACKAGE = "com.instagram.android"
INSTAGRAM_LOGIN_URL = "https://www.instagram.com/accounts/login/"
GALLERY_PHOTO_NAME = "selfie.jpg"
GALLERY_PHOTO_DEST = "/sdcard/Pictures/selfie.jpg"

# ============================================================================
# DEVICE/EMULATOR CONFIGURATION
# ============================================================================
DEVICE_PROXY_ADDRESS = "10.0.2.2:1081"  # Special address for emulator to reach host

# ============================================================================
# ERROR HANDLING & RETRY CONFIGURATION
# ============================================================================
MAX_ERRORS = 10
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

# ============================================================================
# TIMEOUTS (in seconds)
# ============================================================================
ADB_DEFAULT_TIMEOUT = 60
BOOT_TIMEOUT = 60
UI_ELEMENT_TIMEOUT = 15
APPIUM_CONNECT_TIMEOUT = 5

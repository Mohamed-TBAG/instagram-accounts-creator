import time
import urllib.request
from appium import webdriver
from appium.options.android import UiAutomator2Options

APPIUM_SERVER_URL = 'http://127.0.0.1:4723'

def test_generic_connect():
    print(f"Checking Appium at {APPIUM_SERVER_URL}...")
    try:
        urllib.request.urlopen(f"{APPIUM_SERVER_URL}/status", timeout=2)
    except Exception:
        print("Appium server not found. Start it first!")
        return

    options = UiAutomator2Options()
    options.platform_name = 'Android'
    options.automation_name = 'UiAutomator2'
    options.device_name = 'Pixel_6'
    options.no_reset = True
    options.set_capability('appium:autoLaunch', False)
    options.set_capability('appium:appWaitActivity', '*')

    print("Connecting for generic session...")
    try:
        driver = webdriver.Remote(APPIUM_SERVER_URL, options=options)
        print("Connected! Now activating Instagram...")
        driver.activate_app('com.instagram.android')
        print("Success! Instagram activated.")
        time.sleep(5)
        driver.quit()
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    test_generic_connect()

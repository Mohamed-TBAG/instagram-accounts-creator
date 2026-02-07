import time
from appium import webdriver
from appium.options.android import UiAutomator2Options
from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- Configuration ---
APPIUM_SERVER_URL = 'http://127.0.0.1:4723'

def test_instagram_launch():
    print(f"Connecting to Appium at {APPIUM_SERVER_URL}...")
    
    options = UiAutomator2Options()
    options.platform_name = 'Android'
    options.automation_name = 'UiAutomator2'
    options.device_name = 'Pixel_6' 
    
    options.app_package = 'com.instagram.android'
    options.set_capability('appium:appWaitActivity', '*')
    options.no_reset = True

    try:
        driver = webdriver.Remote(APPIUM_SERVER_URL, options=options)
        print("Driver connected. Forcing Instagram to front...")
        driver.activate_app('com.instagram.android')
        
        print("SUCCESS: Instagram should be open now!")
        
        # --- NEW: Find and Click 'Get started' button ---
        print("Looking for 'Get started' button...")
        wait = WebDriverWait(driver, 15) # Wait up to 15 seconds
        
        try:
            # Robust selector: Finds element with text "Get started" (case-insensitive)
            selector = 'new UiSelector().textMatches("(?i)Get started")'
            btn = wait.until(EC.presence_of_element_located((AppiumBy.ANDROID_UIAUTOMATOR, selector)))
            
            print(f"Found button: '{btn.text}'. Clicking...")
            btn.click()
            print("Successfully clicked 'Get started'!")
        except Exception as e:
            print(f"Could not find or click 'Get started' button within timeout.")

        # Stay on screen for 5 seconds to observe
        time.sleep(5)
        
        driver.quit()
        print("Closed session successfully.")
        
    except Exception as e:
        print(f"ERROR: Failed to connect or launch Instagram: {e}")

if __name__ == "__main__":
    test_instagram_launch()

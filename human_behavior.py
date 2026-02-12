import time
import random
import subprocess
import logging
from pathlib import Path
from config import ADB_BIN

logger = logging.getLogger("HumanBehavior")

class HumanBehavior:
    
    def __init__(self):
        self.neighbor_keys = {
            'a': 's', 'b': 'v', 'c': 'x', 'd': 'f', 'e': 'r', 'f': 'd', 'g': 'h',
            'h': 'g', 'i': 'o', 'j': 'k', 'k': 'j', 'l': 'k', 'm': 'n', 'n': 'm',
            'o': 'i', 'p': 'o', 'q': 'w', 'r': 'e', 's': 'a', 't': 'r', 'u': 'i',
            'v': 'b', 'w': 'q', 'x': 'c', 'y': 'u', 'z': 'x',
            '1': '2', '2': '1', '3': '4', '4': '3', '5': '6', '6': '5',
            '7': '8', '8': '7', '9': '0', '0': '9'}
    
    @staticmethod
    def gaussian_pause(mean=2.0, std=0.5, min_time=0.3, max_time=8.0):
        pause = max(min_time, min(max_time, random.gauss(mean, std)))
        return pause
    
    @staticmethod
    def attention_lapse():
        if random.random() < 0.05:
            lapse_time = random.gauss(3.5, 1.0)
            logger.info(f"🧠 Attention lapse... ({lapse_time:.1f}s)")
            time.sleep(lapse_time)
            return True
        return False
    
    def type_with_typos(self, adb_bin, text, field_type="default"):
        typing_speed = self._get_typing_speed(field_type)
        i = 0
        while i < len(text):
            char = text[i]
            if random.random() < 0.15 and char.isalnum():
                typo_char = self.neighbor_keys.get(char.lower(), char)
                if typo_char != char:
                    logger.info(f"⌨️ Typo: typed '{typo_char}' instead of '{char}'")
                    subprocess.run([str(adb_bin), "shell", "input", "text", typo_char], check=False)
                    time.sleep(random.gauss(0.7, 0.25))
                    subprocess.run([str(adb_bin), "shell", "input", "keyevent", "67"], check=False)
                    time.sleep(random.gauss(0.3, 0.1))
                    logger.info(f"✏️ Corrected: typed '{char}'")
            if char == ' ':
                subprocess.run([str(adb_bin), "shell", "input", "text", "%s"], check=False)
            elif char == "'":
                subprocess.run([str(adb_bin), "shell", "input", "text", "\\'"], check=False)
            elif char == '"':
                subprocess.run([str(adb_bin), "shell", "input", "text", '\\"'], check=False)
            else:
                subprocess.run([str(adb_bin), "shell", "input", "text", char], check=False)
            time.sleep(typing_speed)
            i += 1
    
    @staticmethod
    def _get_typing_speed(field_type):
        speeds = {
            "name": random.gauss(0.08, 0.02),
            "password": random.gauss(0.18, 0.05),
            "email": random.gauss(0.10, 0.03),
            "code": random.gauss(0.25, 0.08),
            "default": random.gauss(0.12, 0.04)}
        return max(0.05, speeds.get(field_type, speeds["default"]))
    
    @staticmethod
    def verify_password_eye(device_mgr, driver):
        if random.random() < 0.70:
            logger.info("👁️ Human behavior: Verifying password with eye icon...")
            time.sleep(random.gauss(1.2, 0.4))
            try:
                device_mgr.click_text(driver, "Show password", exact=False, timeout=3)
                logger.info("✓ Password visibility toggled")
                time.sleep(random.gauss(1.5, 0.5))  
                device_mgr.click_text(driver, "Show password", exact=False, timeout=3)
                logger.info("✓ Password hidden again")
                time.sleep(random.gauss(0.8, 0.3))
            except:
                logger.info("⚠️ Eye icon not found, skipping")
    
    @staticmethod
    def scroll_through_terms(device_mgr, driver):
        logger.info("📖 Human behavior: Scrolling through terms...")
        swipe_count = random.randint(2, 5)
        for i in range(swipe_count):
            device_mgr.swipe(driver, 400, 600, 400, 300, random.randint(400, 700))
            time.sleep(random.gauss(0.8, 0.3))
            logger.info(f"  Scrolling... ({i+1}/{swipe_count})")
        if random.random() < 0.40:
            logger.info("  Scrolling back up (second thoughts)...")
            device_mgr.swipe(driver, 400, 300, 400, 600, 500)
            time.sleep(random.gauss(0.5, 0.2))
    
    @staticmethod
    def edit_username(device_mgr, driver, adb_bin):
        logger.info("✏️ Human behavior: Editing suggested username...")
        if not device_mgr.click_text(driver, "Edit", exact=True, timeout=5):
            if not device_mgr.click_text(driver, "Change", exact=False, timeout=5):
                logger.warning("Could not find edit button")
                return
        time.sleep(random.gauss(1, 0.3))
        subprocess.run([str(adb_bin), "shell", "input", "keyevent", "29"], check=False)  
        time.sleep(random.gauss(0.3, 0.1))
        subprocess.run([str(adb_bin), "shell", "input", "keyevent", "111"], check=False)  
        time.sleep(random.gauss(0.3, 0.1))
        new_suffix = str(random.randint(100, 999))
        logger.info(f"  Changed username suffix to: {new_suffix}")
        for char in new_suffix:
            subprocess.run([str(adb_bin), "shell", "input", "text", char], check=False)
            time.sleep(0.1)
        time.sleep(random.gauss(0.8, 0.3))
    
    @staticmethod
    def minimize_check_notifications(device_mgr, adb_bin):
        if random.random() < 0.25:
            logger.info("📱 Human behavior: Checking notifications...")
            device_mgr.minimize_and_restore_app()
            time.sleep(random.gauss(1.5, 0.5))
    
    @staticmethod
    def indecisive_date_swipes(device_mgr, driver, target_year, current_year=2005):
        logger.info(f"📅 Selecting birth year ({target_year})...")
        year_diff = current_year - target_year
        swipe_count = abs(year_diff) // 3 
        overshoot = random.randint(2, 5)
        total_swipes = swipe_count + overshoot
        logger.info(f"  Initial swipes (with overshoot): {total_swipes}")
        for i in range(total_swipes):
            device_mgr.swipe(driver, 820, 1150, 820, 1350, random.randint(250, 400))
            time.sleep(random.gauss(0.4, 0.15))
        time.sleep(random.gauss(1.2, 0.4))
        logger.info(f"  Correcting overshoot...")
        for _ in range(overshoot):
            device_mgr.swipe(driver, 820, 1350, 820, 1150, random.randint(250, 350))
            time.sleep(random.gauss(0.4, 0.15))
        time.sleep(random.gauss(0.8, 0.3))
    
    @staticmethod
    def back_button_panic(adb_bin):
        if random.random() < 0.04:
            logger.info("😱 Human behavior: Accidental back button press...")
            subprocess.run([str(adb_bin), "shell", "input", "keyevent", "4"], check=False)
            time.sleep(random.gauss(0.8, 0.3))
            logger.info("  Clicking NO to stay in signup...")
            return True
        return False
    
    @staticmethod
    def double_check_field(adb_bin):
        if random.random() < 0.30:
            logger.info("🔍 Human behavior: Double-checking field...")
            subprocess.run([str(adb_bin), "shell", "input", "keyevent", "29"], check=False)
            time.sleep(random.gauss(0.8, 0.3))
            subprocess.run([str(adb_bin), "shell", "input", "keyevent", "4"], check=False)
            time.sleep(random.gauss(0.4, 0.2))
            return True
        return False
    
    @staticmethod
    def deliberate_next_click(device_mgr, driver):
        if random.random() < 0.15:
            logger.info("🔍 Looking for Next button...")
            time.sleep(random.gauss(0.5, 0.2))
        time.sleep(HumanBehavior.gaussian_pause(1.5, 0.5, 0.5, 5.0))
    
    @staticmethod
    def gallery_scroll_tease(device_mgr, driver):
        logger.info("🖼️ Human behavior: Browsing gallery for profile pic...")
        scroll_count = random.randint(3, 7)
        for i in range(scroll_count):
            device_mgr.swipe(driver, 400, 700, 200, 700, random.randint(300, 500))
            time.sleep(random.gauss(0.6, 0.2))
            if random.random() < 0.3:
                logger.info(f"  Viewing image {i+1}...")
                time.sleep(random.gauss(1.5, 0.5))
        logger.info("  No good photo, skipping...")
        time.sleep(random.gauss(0.8, 0.3))
    
    @staticmethod
    def network_retry_behavior(action_func, max_attempts=3, description="Action"):
        for attempt in range(max_attempts):
            try:
                if action_func():
                    return True
            except Exception as e:
                if attempt < max_attempts - 1 and random.random() < 0.03:
                    retry_delay = random.gauss(2.5, 0.8)
                    logger.warning(f"⚠️ {description} failed, retrying in {retry_delay:.1f}s...")
                    time.sleep(retry_delay)
                    continue
                raise
        return False
    
    @staticmethod
    def read_time_behavior(seconds=2.0):
        actual_time = random.gauss(seconds, seconds * 0.3)
        actual_time = max(0.5, actual_time)
        time.sleep(actual_time)

if __name__ == "__main__":
    human = HumanBehavior()
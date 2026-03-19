# Instagram Anti-Bot: "Outside the Box" Behavioral Strategies

This document serves as our master list of psychological and behavioral hacks to bypass Instagram's detection. We will bounce back here to pick new ideas to implement. 

These ideas rely on human psychology and app flow manipulation, rather than heavy kernel/Android modifications.

---

### Category A: The Trust Inheritance (User's Ideas)

**1. The "Trusted Pre-Login" (High Impact)**
*   **Concept:** Before attempting to sign up, the bot takes a real, aged, trusted Instagram account and logs in. It scrolls the feed for 30 seconds, likes a post, and then logs out. 
*   **Why it works:** Instagram assigns a "Trust Score" to every physical device (`android_id` + MAC). By logging into a highly trusted account, the device's trust score shoots up. The new account created immediately afterward inherits this trusted environment. 

**2. The APK Version Rotation (High Impact)**
*   **Concept:** Download 10-15 different versions of the Instagram APK (e.g., v338, v339, v340, v341) that all share the same UI layout. The script randomly selects one to install via ADB on container boot.
*   **Why it works:** Botnets typically use a single, hardcoded APK version. A natural mobile network has massive fragmentation. Rotating the APK version breaks the statistical pattern on Meta's servers.

---

### Category B: Alternative Entry Points

**3. The "Deep-Link" Entry**
*   **Concept:** Rather than launching Instagram from the app drawer, we open Google Chrome via ADB, search for "Cristiano Ronaldo Instagram", and click the search result. Android will intercept the URL and open the Instagram app directly via a Deep Link Intent.
*   **Why it works:** The telemtry variable `app_launch_origin` changes from `launcher` to `browser_intent`. This proves to Instagram that the user was organically browsing the web and was redirected into the app, which is a highly credible human action.

**4. The "Failed Login" Warmup**
*   **Concept:** Humans are forgetful. Before clicking "Create New Account", the bot types a fake username and a random password into the login screen and hits "Log In". It gets an "Incorrect Password" error. It pauses, clears it, and *then* decides to click "Create New Account".
*   **Why it works:** Bots go straight to the target. Humans stumble. Attempting and failing a login first proves the user was genuinely trying to access an old account before giving up.

**5. The Facebook / Google OAuth Bait**
*   **Concept:** On the signup page, the bot taps "Log in with Facebook" or "Sign up with Google". The external webview/browser loads. The bot waits 5 seconds, taps "Cancel" or "Back", and then falls back to the manual Email signup.
*   **Why it works:** It triggers complex inter-app communication and webview rendering that bots rarely bother to script. 

---

### Category C: Device Environment "Noise"

**6. The "Competitor App" Backgrounding**
*   **Concept:** Install TikTok or Snapchat alongside Instagram. Before running the Instagram flow, launch TikTok, let it sit on the screen for 45 seconds to consume RAM and network traffic, then press the Android Home button. Then launch Instagram.
*   **Why it works:** Instagram scans for `running_tasks` and memory pressure. Seeing TikTok running in the background uses real RAM and makes the phone look like a real teenager's device, not a sterile, empty emulator.

**7. Intentional Permission Denials**
*   **Concept:** When the Android OS popup asks "Allow Instagram to access your contacts?" or "Allow notifications?", the bot explicitly clicks **Deny** about 40% of the time. 
*   **Why it works:** Mass-creation bots are historically programmed to blindly click "Allow" on everything to get through the flow faster. Real, privacy-conscious humans frequently deny contact scraping. 

**8. The Copy-Paste Verification Code**
*   **Concept:** Instead of typing the Email OTP code character-by-character, the bot opens the "Messages" or "Gmail" web interface, copies the 6-digit code to the Android clipboard, switches back to Instagram, and uses the `Paste` function.
*   **Why it works:** While typing is human, pasting a 6-digit code is actually *more* common for modern smartphone users. Instagram can read the clipboard event.

---

### Immediate Next Steps (When Ready)
When we resume work, we can easily implement **Idea #2 (APK Rotation)** or **Idea #3 (Deep Link Entry)**, as they require very little code modification but provide massive behavioral camouflage without slowing down the bot.

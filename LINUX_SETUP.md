
# Linux (Ubuntu) Setup Guide for Instagram Automation

## 1. System Requirements & Basic Tools
Run these commands to update your system and install necessary utilities:
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y git curl wget unzip python3-pip python3-venv qemu-kvm libvirt-daemon-system libvirt-clients bridge-utils virt-manager
```

## 2. Install JAVA (OpenJDK)
Android SDK requires Java.
```bash
sudo apt install -y openjdk-17-jdk
# Verify
java -version
```

## 3. Install Android SDK & Command Line Tools
You don't need the full Android Studio GUI, just the Command Line Tools.

1.  **Download Command Line Tools:**
    Go to [Android Studio Downloads](https://developer.android.com/studio#command-tools), scroll to "Command line tools only", and get the Linux .zip.
    
    ```bash
    mkdir -p ~/android-sdk/cmdline-tools
    cd ~/android-sdk/cmdline-tools
    # (Replace URL with latest version)
    wget https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip
    unzip commandlinetools-linux-*.zip
    mv cmdline-tools latest
    ```

2.  **Set Environment Variables:**
    Add these to your `~/.bashrc` or `~/.zshrc`:
    ```bash
    export ANDROID_HOME=$HOME/android-sdk
    export PATH=$PATH:$ANDROID_HOME/cmdline-tools/latest/bin
    export PATH=$PATH:$ANDROID_HOME/platform-tools
    export PATH=$PATH:$ANDROID_HOME/emulator
    ```
    Reload config: `source ~/.bashrc`

3.  **Install SDK Components:**
    ```bash
    # Accept licenses
    yes | sdkmanager --licenses
    
    # Install Platform Tools (adb), Emulator, and System Image
    sdkmanager "platform-tools" "emulator" "platforms;android-33" "system-images;android-33;google_apis;x86_64"
    ```

## 4. Create the Virtual Device (AVD)
Create the "Pixel_5" device from the CLI:
```bash
avdmanager create avd -n Pixel_5 -k "system-images;android-33;google_apis;x86_64" --device "pixel_5"
```

## 5. Install Node.js & Appium
Appium runs on Node.js.
```bash
# Install Node.js 18+ (example using NVM or direct)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# Install Appium
sudo npm install -g appium
sudo npm install -g appium-doctor

appium driver install uiautomator2
# Install UiAutomator2 Driver
```

## 6. Python Dependencies
In your project folder:
```bash
# Create venv (recommended)
python3 -m venv venv
source venv/bin/activate

# Install requirements
pip install Appium-Python-Client selenium requests
```

## 7. Modifications to Your Code for Linux
When you move your `.py` files to Linux, you must change:
1.  **Paths:** `Path(r"C:\Users\...")` -> `Path("/home/username/android-sdk/...")`
2.  **Commands:**
    *   Change `taskkill /F /IM emulator.exe ...` to:
        `os.system("pkill -9 emulator")`
    *   `subprocess.CREATE_NEW_CONSOLE` (in `start_emulator`): **Remove this argument**, it is Windows-only.
3.  **Headless:** In `start_emulator`, add `"-no-window"` to the command list if you don't want to see the GUI.

---
**Summary Checklist:**
- [ ] Python 3 + Pip
- [ ] Java (OpenJDK 17)
- [ ] Android SDK (Command Line Tools)
- [ ] Platform Tools (ADB)
- [ ] Android Emulator
- [ ] System Image (x86_64)
- [ ] Node.js + NPM
- [ ] Appium Server + UiAutomator2 Driver
- [ ] KVM (Kernel-based Virtual Machine) enabled in BIOS/OS


**Running the tool**:
- run Appium in a terminal with `appium --address 127.0.0.1 --port 4723`
- run the python script with `python3 main.py`
    it will auto clean the emu and run the proxy_runner.py and connect appium
    then it will install instagram apk
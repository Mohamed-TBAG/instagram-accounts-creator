# Redroid Instance Manager 📱🐳

Welcome to the **Redroid Instance Manager**! This is a simple, automated tool designed to help you quickly launch, control, and connect to multiple isolated Android emulators running on your computer. 

If you are reading this and have **zero experience** with Docker, ADB, or Android emulation, you are in the right place. This guide is specifically written for beginners. Follow along carefully!

---

## 🛠️ Step 1: What You Need (Prerequisites)

Before you run this tool, you must install three essential pieces of software. 

### 1. Docker (Runs the Emulators)
Docker is a program that lets you run lightweight "containers." Our Android devices (called "ReDroid") will run inside these containers.
- **Windows / Mac Users:** Download and install [Docker Desktop](https://www.docker.com/products/docker-desktop/). After installing, open it, and leave it running in the background. On Windows, ensure you update to WSL2 if Docker asks for it.
- **Linux Users (Ubuntu/Debian):**
  Open your terminal and run:
  ```bash
  sudo apt install docker.io
  sudo systemctl start docker
  sudo systemctl enable docker
  sudo usermod -aG docker $USER
  ```
  *(Log out and log back in for the user group changes to take effect).*

### 2. ADB (Android Debug Bridge, Connects to Emulators)
ADB is a command-line tool that lets your computer talk to the Android emulators.
- **Windows:** Download the [SDK Platform-Tools for Windows](https://developer.android.com/studio/releases/platform-tools). Extract the `.zip` file somewhere safe (like `C:\platform-tools`). Open your Start Menu, search for "Environment Variables", click "Edit the system environment variables", and add `C:\platform-tools` to your system `Path`.
- **Mac:** Open your Terminal and run: `brew install android-platform-tools`
- **Linux (Ubuntu/Debian):** Open your terminal and run: `sudo apt install android-tools-adb`

### 3. Scrcpy (Views the Screen)
Scrcpy (Screen Copy) is the tool that pops up the physical window of the Android device so you can click on things.
- **Windows:** Download the [scrcpy-win64.zip](https://github.com/Genymobile/scrcpy/releases) file, extract it to a known folder, and add that folder to your system `Path` (just like you did for ADB).
- **Mac:** Run: `brew install scrcpy`
- **Linux:** Run: `sudo apt install scrcpy`

### Important Note on Kernel Modules (Linux Only)
If you are running this natively on Linux, ReDroid requires specific kernel modules (`binder_linux` and `ashmem`). You likely need to mount `binderfs`. 
Run this before trying to launch devices:
```bash
sudo mkdir -p /dev/binderfs
sudo mount -t binder binder /dev/binderfs
```
*(Windows and Mac users using Docker Desktop do not need to do this step).*

---

## 🚀 Step 2: Running the Manager

Once Docker is running, you can use this simple Python script to create and manage your Android devices.

*Ensure you have Python 3 installed on your system (`python3 --version`).*

Open your terminal or command prompt, navigate to this folder, and use the commands below:

### Creating New Emulators
To create and immediately open 3 isolated Android devices, simply pass the number `3` to the script:
```bash
python3 manager.py 3
```
*The script will automatically download the Android system (if it hasn't already), boot them up concurrently, wait for them to turn on, and automatically pop open the `scrcpy` GUI screen for each one. They are completely isolated from each other!*

---

## 🎮 Step 3: Commands Reference

Here are all the ways you can control your devices.

### Listing Devices
To see what devices are currently saved on your computer:
```bash
python3 manager.py --list
```

### Starting Devices
If you turned a device off and need to turn it back on:
```bash
python3 manager.py --start 1       # Starts ONLY device number 1
python3 manager.py --start-all     # Starts ALL existing devices at the same time
```

### Viewing Devices (Opening the Screen)
If a device is already running in the background, but you accidentally closed the screen window, you can force it to open again:
```bash
python3 manager.py --open-all
```

### Stopping Devices (Turning them Off)
To save RAM/CPU, you can turn off the devices without deleting them:
```bash
python3 manager.py --stop 1       # Turns off device 1
python3 manager.py --stop-all     # Turns off ALL devices
```

### Deleting Devices (Wiping them entirely)
If you are done testing and want to completely erase the device data forever:
```bash
python3 manager.py --delete 1     # Erases device 1 entirely
python3 manager.py --delete-all   # Erases ALL devices completely
```

---

## 🔌 Manual Connection (Advanced)

The script does it automatically, but if you want to connect to a device manually via the terminal, use the port number the script assigns (starting at `5567`):

- **Device 1:** `adb connect localhost:5567`
- **Device 2:** `adb connect localhost:5568`
- **Device 3:** `adb connect localhost:5569`

Then, to manually open the screen:
```bash
scrcpy -s localhost:5567
```

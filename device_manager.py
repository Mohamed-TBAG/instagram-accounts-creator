import os
import shutil
import subprocess
import random
import re
import logging
import uuid
from time import sleep, time
from pathlib import Path
from urllib.request import urlopen
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from appium.webdriver.common.appiumby import AppiumBy
from appium import webdriver
from appium.options.android import UiAutomator2Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.actions import interaction
from selenium.webdriver.common.actions.action_builder import ActionBuilder
from selenium.webdriver.common.actions.pointer_input import PointerInput
from config import (
    PROJECT_BIN, ADB_BIN,
    APPIUM_SERVER_URL, INSTAGRAM_PACKAGE, GALLERY_PHOTO_DEST,
    DEVICE_PROXY_ADDRESS, UI_ELEMENT_TIMEOUT,
    ADB_DEFAULT_TIMEOUT, BOOT_TIMEOUT, APPIUM_CONNECT_TIMEOUT,
    REDROID_IMAGE, REDROID_GPU_MODE, REDROID_WIDTH, REDROID_HEIGHT, REDROID_FPS,
    REDROID_USE_PROP_MOUNTS,
    DEVICE_PROFILES)
logger = logging.getLogger("DeviceManager")

class DeviceManager:

    def __init__(self):
        self.adb_port = 5555
        self.fingerprint = None
        self.previous_fingerprint = None
        self.prop_mounts = []
        if not ADB_BIN.exists():
            logger.error(f"ADB binary not found at {ADB_BIN}")
            raise FileNotFoundError(f"ADB binary not found at {ADB_BIN}")
    
    def _adb(self, *args, timeout=ADB_DEFAULT_TIMEOUT, check=False, **kwargs):
        addr = f"localhost:{self.adb_port}"
        cmd = [str(ADB_BIN), "-s", addr, *args]
        return subprocess.run(cmd, timeout=timeout, check=check, **kwargs)

    def _random_serial(self, length=12):
        alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        return "".join(random.choice(alphabet) for _ in range(length))

    def _random_hex(self, length=16):
        alphabet = "0123456789abcdef"
        return "".join(random.choice(alphabet) for _ in range(length))

    def _random_incremental(self):
        return f"{random.randint(100000000, 999999999)}"

    def _random_mac(self):
        first = random.choice([0x02, 0x06, 0x0A, 0x0E])
        rest = [random.randint(0x00, 0xFF) for _ in range(5)]
        return ":".join(f"{x:02x}" for x in [first, *rest])

    def _random_imei(self):
        body = [random.randint(0, 9) for _ in range(14)]
        total = 0
        for i, digit in enumerate(body):
            if i % 2:
                doubled = digit * 2
                total += doubled if doubled < 10 else doubled - 9
            else:
                total += digit
        check = (10 - (total % 10)) % 10
        return "".join(map(str, body + [check]))

    def _validate_container_inputs(self, name, port):
        if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]*", name):
            raise ValueError(f"Invalid container name '{name}'")
        if not isinstance(port, int) or not (1 <= port <= 65535):
            raise ValueError(f"Invalid host ADB port '{port}'")

    def _to_bool(self, raw, name):
        value = (raw or "").strip().lower()
        if value in {"1", "true", "yes", "on"}:
            return True
        if value in {"0", "false", "no", "off"}:
            return False
        raise ValueError(f"{name} must be boolean-like, got '{raw}'")

    def _read_dotenv_value(self, key):
        dotenv = Path(".env")
        if not dotenv.exists():
            return None
        for raw_line in dotenv.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            env_key, env_value = line.split("=", 1)
            if env_key.strip() != key:
                continue
            value = env_value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
                value = value[1:-1]
            return value
        return None

    def _resolve_use_prop_mounts(self):
        dotenv_raw = self._read_dotenv_value("REDROID_USE_PROP_MOUNTS")
        if dotenv_raw is not None and dotenv_raw.strip() != "":
            return self._to_bool(dotenv_raw, "REDROID_USE_PROP_MOUNTS")
        env_raw = os.getenv("REDROID_USE_PROP_MOUNTS")
        if env_raw is not None and env_raw.strip() != "":
            return self._to_bool(env_raw, "REDROID_USE_PROP_MOUNTS")
        return REDROID_USE_PROP_MOUNTS

    def generate_random_identity(self):
        profile = random.choice(DEVICE_PROFILES)
        resolution = profile.get("resolution", "1080x2400")
        density = int(profile.get("density", 420))
        incremental = self._random_incremental()
        build_id = f"RQ3A.{random.randint(210000, 219999)}.00{random.randint(1, 9)}"
        security_patch = random.choice(["2024-01-05", "2024-02-05", "2024-03-05", "2024-04-05"])
        previous = self.previous_fingerprint or {}
        serial = self._random_serial(12)
        mac = self._random_mac()
        android_id = self._random_hex(16)
        guid = str(uuid.uuid4())
        while (
            serial == previous.get("ro.serialno")
            or mac == previous.get("wifi.mac.address")
            or android_id == previous.get("android_id")
            or guid == previous.get("guid")
        ):
            serial = self._random_serial(12)
            mac = self._random_mac()
            android_id = self._random_hex(16)
            guid = str(uuid.uuid4())
        build_fp = (
            f"{profile['brand']}/{profile['name']}/{profile['device']}:"
            f"11/{build_id}/{incremental}:user/release-keys"
        )
        self.fingerprint = {
            "ro.product.manufacturer": profile["manufacturer"],
            "ro.product.brand": profile["brand"],
            "ro.product.model": profile["model"],
            "ro.product.name": profile["name"],
            "ro.product.device": profile["device"],
            "ro.serialno": serial,
            "ro.boot.serialno": serial,
            "gsm.version.baseband": f"M8350-{random.randint(1000,9999)}GEN_PACK-1",
            "hw.gsmModem.imei": self._random_imei(),
            "wifi.mac.address": mac,
            "phone_id": str(uuid.uuid4()),
            "guid": guid,
            "google_ad_id": str(uuid.uuid4()),
            "android_id": android_id,
            "build_release": "11",
            "build_id": build_id,
            "build_incremental": incremental,
            "build_security_patch": security_patch,
            "build_fingerprint": build_fp,
            "display_density": density,
            "display_resolution": resolution,
        }
        self.previous_fingerprint = dict(self.fingerprint)
        return self.fingerprint

    def get_device_fingerprint(self):
        if not self.fingerprint:
            return self.generate_random_identity()
        return self.fingerprint

    def seed_gallery(self):
        dummy_photo = PROJECT_BIN / "dummy_photo.JPG"
        if not dummy_photo.exists():
            dummy_photo = PROJECT_BIN / "dummy_photo.jpg"
        if not dummy_photo.exists():
            raise FileNotFoundError(f"dummy_photo(.jpg/.JPG) not found at {PROJECT_BIN}")
        dest = "/sdcard/Pictures/selfie.jpg"
        logger.info("Seeding Gallery...")
        try:
            self._adb("shell", "mkdir", "-p", "/sdcard/Pictures", check=True, timeout=10)
            self._adb("push", str(dummy_photo), dest, check=True, timeout=30)
            self._adb("shell", "am", "broadcast", "-a", "android.intent.action.MEDIA_SCANNER_SCAN_FILE", "-d", f"file://{dest}", check=True, timeout=10)
            logger.info("Gallery Seeded.")
        except Exception as e:
            raise Exception(f"Failed to seed gallery: {e}")

    
    def warmup_actions(self):
        logger.info("Performing Warm-up Routine...")
        try:
            self._adb("shell", "am", "start", "-a", "android.intent.action.SEND", "-t", "image/*", "--eu", "android.intent.extra.STREAM", f"file://{GALLERY_PHOTO_DEST}", INSTAGRAM_PACKAGE, check=True, timeout=10)
            logger.info("Warmup: Share Intent Launched.")
        except Exception as e:
            raise Exception(f"Warmup failed: {e}") from e

    def kill_scrcpy(self):
        try:
            subprocess.run(["pkill", "-f", "scrcpy"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            logger.info("  🔪 Killed stuck scrcpy processes.")
        except Exception:
            pass

    def kill_emulator(self, name="redroid_0"):
        # logger.info(f"Stopping ReDroid container: {name}")
        try:
            subprocess.run(["docker", "stop", name], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run([str(ADB_BIN), "disconnect", f"localhost:{self.adb_port}"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            raise Exception(f"Error killing ReDroid: {e}")
        sleep(1)

    def kill_all_emulators(self):
        """Forcefully removes all stopped or running Redroid containers from the host."""
        logger.info("🔪 Wiping all background Redroid containers...")
        try:
            cmd = "docker rm -f $(docker ps -aq -f ancestor=redroid/redroid:11.0.0-latest)"
            subprocess.run(cmd, shell=True, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            logger.error(f"Error wiping orphan containers: {e}")

    def _generate_prop_files(self, name, fingerprint):
        """Generates custom build.prop files for the container."""
        template_dir = Path("templates")
        if not template_dir.exists():
            logger.warning("Templates dir not found, skipping build.prop mount.")
            return []
        out_dir = Path("temp_props") / name
        if out_dir.exists():
            shutil.rmtree(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        files = ["system_build.prop", "vendor_build.prop", "product_build.prop"]
        mounts = []
        build_fp = fingerprint["build_fingerprint"]
        desc = (
            f"{fingerprint['ro.product.name']}-user {fingerprint['build_release']} "
            f"{fingerprint['build_id']} {fingerprint['build_incremental']} release-keys"
        )
        replacements = {
            "ro.product.model": fingerprint["ro.product.model"],
            "ro.product.brand": fingerprint["ro.product.brand"],
            "ro.product.manufacturer": fingerprint["ro.product.manufacturer"],
            "ro.product.name": fingerprint["ro.product.name"],
            "ro.product.device": fingerprint["ro.product.device"],
            "ro.serialno": fingerprint["ro.serialno"],
            "ro.build.fingerprint": build_fp,
            "ro.system.build.fingerprint": build_fp,
            "ro.vendor.build.fingerprint": build_fp,
            "ro.product.build.fingerprint": build_fp,
            "ro.bootimage.build.fingerprint": build_fp,
            "ro.build.version.release": fingerprint["build_release"],
            "ro.system.build.version.release": fingerprint["build_release"],
            "ro.vendor.build.version.release": fingerprint["build_release"],
            "ro.product.build.version.release": fingerprint["build_release"],
            "ro.build.version.incremental": fingerprint["build_incremental"],
            "ro.system.build.version.incremental": fingerprint["build_incremental"],
            "ro.vendor.build.version.incremental": fingerprint["build_incremental"],
            "ro.product.build.version.incremental": fingerprint["build_incremental"],
            "ro.build.version.security_patch": fingerprint["build_security_patch"],
            "ro.system.build.version.security_patch": fingerprint["build_security_patch"],
            "ro.vendor.build.security_patch": fingerprint["build_security_patch"],
            "ro.product.build.version.security_patch": fingerprint["build_security_patch"],
            "ro.build.id": fingerprint["build_id"],
            "ro.system.build.id": fingerprint["build_id"],
            "ro.vendor.build.id": fingerprint["build_id"],
            "ro.product.build.id": fingerprint["build_id"],
            "ro.build.display.id": desc,
            "ro.build.product": fingerprint["ro.product.device"],
            "ro.build.description": desc,
            "ro.system_ext.build.fingerprint": build_fp,
            "ro.product.system.model": fingerprint["ro.product.model"],
            "ro.product.system.brand": fingerprint["ro.product.brand"],
            "ro.product.system.manufacturer": fingerprint["ro.product.manufacturer"],
            "ro.product.system.name": fingerprint["ro.product.name"],
            "ro.product.system.device": fingerprint["ro.product.device"],
            "ro.product.system_ext.model": fingerprint["ro.product.model"],
            "ro.product.system_ext.brand": fingerprint["ro.product.brand"],
            "ro.product.system_ext.manufacturer": fingerprint["ro.product.manufacturer"],
            "ro.product.system_ext.name": fingerprint["ro.product.name"],
            "ro.product.system_ext.device": fingerprint["ro.product.device"],
            "ro.product.vendor.model": fingerprint["ro.product.model"],
            "ro.product.vendor.brand": fingerprint["ro.product.brand"],
            "ro.product.vendor.manufacturer": fingerprint["ro.product.manufacturer"],
            "ro.product.vendor.name": fingerprint["ro.product.name"],
            "ro.product.vendor.device": fingerprint["ro.product.device"],
            "ro.product.product.model": fingerprint["ro.product.model"],
            "ro.product.product.brand": fingerprint["ro.product.brand"],
            "ro.product.product.manufacturer": fingerprint["ro.product.manufacturer"],
            "ro.product.product.name": fingerprint["ro.product.name"],
            "ro.product.product.device": fingerprint["ro.product.device"]}
        for fname in files:
            src = template_dir / fname
            if not src.exists():
                 continue
            dest = out_dir / fname 
            try:
                content = src.read_text(encoding="utf-8")
                new_lines = []
                for line in content.splitlines():
                    if "=" in line:
                        key_part = line.split("=")[0].strip()
                        if key_part in replacements:
                            new_lines.append(f"{key_part}={replacements[key_part]}")
                            continue
                    new_lines.append(line)
                dest.write_text("\n".join(new_lines), encoding="utf-8")
                container_path = "/" + fname.replace("_build.prop", "/build.prop")
                mounts.extend(["-v", f"{dest.absolute()}:{container_path}"])
            except Exception as e:
                logger.error(f"Failed to process template {fname}: {e}")

        return mounts

    def get_docker_cmd(self, fp, port, name, prop_mounts):
        gpu_mode = (REDROID_GPU_MODE or "guest").strip().lower()
        if gpu_mode not in {"guest", "host"}:
            gpu_mode = "guest"
        boot_args = [
            f"androidboot.redroid_width={REDROID_WIDTH}",
            f"androidboot.redroid_height={REDROID_HEIGHT}",
            f"androidboot.redroid_fps={REDROID_FPS}",
            f"androidboot.redroid_gpu_mode={gpu_mode}",
            "androidboot.use_memfd=1",
            "debug.sf.nobootanimation=1",
        ]
        return [
            "docker", "run", "-d", "--rm", "--privileged",
            "--name", name,
            "--pull", "never",
            "-v", "/dev/binderfs:/dev/binderfs", 
            "--tmpfs", "/data:rw,exec,suid",
            f"--mac-address={fp['wifi.mac.address']}",
            "-p", f"{port}:5555",
            *prop_mounts,
            REDROID_IMAGE,
            *boot_args
        ]


    def start_emulator(self, name="redroid_0", port=5555):
        self._validate_container_inputs(name, port)
        self.adb_port = port
        addr = f"localhost:{port}"
        logger.info(f"Starting Redroid Container: {name} on port {port}")
        use_prop_mounts = self._resolve_use_prop_mounts()
        logger.info(f"Effective REDROID_USE_PROP_MOUNTS={int(use_prop_mounts)}")
        self._preflight_docker()
        self._assert_binderfs()
        fp = self.generate_random_identity()
        candidate_mounts = []
        if use_prop_mounts:
            generated_mounts = self._generate_prop_files(name, fp)
            if generated_mounts:
                candidate_mounts.append(("fingerprint_mounts", generated_mounts))
            else:
                logger.warning("No build.prop mounts generated; continuing with baseline startup")
        candidate_mounts.append(("baseline", []))
        boot_errors = []
        selected_mounts = []
        long_boot_timeout = max(BOOT_TIMEOUT, 90)
        fast_boot_timeout = min(long_boot_timeout, 120)
        for mode, mounts in candidate_mounts:
            logger.info(f"Startup mode: {mode}")
            self.kill_emulator(name)
            subprocess.run([str(ADB_BIN), "disconnect", addr], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                cmd = self.get_docker_cmd(fp, port, name, mounts)
                proc = subprocess.run(cmd, check=True, capture_output=True, text=True)
                if proc.stdout.strip():
                    logger.info(f"Container started: {proc.stdout.strip()}")
                self._assert_container_running(name)
                logger.info("  ⏳ Container started. Waiting for Android boot...")
                boot_timeout = fast_boot_timeout if mode == "fingerprint_mounts" else long_boot_timeout
                self.wait_for_adb(port, timeout=boot_timeout, name=name)
                selected_mounts = mounts
                break
            except Exception as e:
                logs = self._get_container_logs(name)
                boot_errors.append(f"{mode}: {e} logs_tail='{logs}'")
                self.kill_emulator(name)
        else:
            details = " | ".join(boot_errors)
            raise Exception(f"Failed to boot ReDroid after all startup modes: {details}")
        self.prop_mounts = selected_mounts
        self._apply_post_boot_identity(fp)
        self._verify_identity(fp, strict_props=bool(selected_mounts))
        logger.info("  ✅ Redroid is Online!")

    def _preflight_docker(self):
        try:
            subprocess.run(["docker", "info"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
        except Exception as e:
            raise Exception(f"Docker preflight failed: {e}") from e

    def _assert_binderfs(self):
        if not Path("/dev/binderfs").exists():
            raise Exception("Missing /dev/binderfs on host. Binderfs must be mounted for ReDroid.")

    def _assert_container_running(self, name):
        try:
            proc = subprocess.run(
                ["docker", "inspect", "-f", "{{.State.Running}}", name],
                capture_output=True,
                text=True,
                timeout=5,
                check=True,
            )
            state = (proc.stdout or "").strip().lower()
            if state != "true":
                raise Exception(f"Container '{name}' not running after start, state='{state}'")
        except Exception as e:
            raise Exception(f"Container state verification failed for '{name}': {e}") from e

    def wait_for_adb(self, port=5555, timeout=BOOT_TIMEOUT, name="redroid_0"):
        addr = f"localhost:{port}"
        deadline = time() + timeout
        logger.info(f"Waiting for {name} to fully boot (via ADB)...")
        subprocess.run([str(ADB_BIN), "disconnect", addr], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        last_boot_value = ""
        last_state = ""
        last_connect = ""
        while time() < deadline:
            try:
                self._assert_container_running(name)
            except Exception as e:
                logs = self._get_container_logs(name)
                raise Exception(
                    f"Container not running during boot wait: {e} logs_tail='{logs}'"
                ) from e
            try:
                connect_proc = subprocess.run([str(ADB_BIN), "connect", addr], capture_output=True, text=True, timeout=8)
                last_connect = ((connect_proc.stdout or "") + (connect_proc.stderr or "")).strip()
                state_proc = subprocess.run([str(ADB_BIN), "-s", addr, "get-state"], capture_output=True, text=True, timeout=8)
                last_state = (state_proc.stdout or "").strip()
                if last_state == "device":
                    boot_proc = subprocess.run(
                        [str(ADB_BIN), "-s", addr, "shell", "getprop", "sys.boot_completed"],
                        capture_output=True, text=True, timeout=8)
                    last_boot_value = boot_proc.stdout.strip()
                    if last_boot_value == "1":
                        logger.info(f"  ✅ Redroid ADB is Online ({addr})")
                        return
            except subprocess.TimeoutExpired:
                pass
            except Exception as e:
                logger.warning(f"Error checking boot status: {e}")
            sleep(2)
        logs = self._get_container_logs(name)
        raise Exception(
            f"Timeout waiting for {name} to boot. sys.boot_completed='{last_boot_value}' "
            f"adb_state='{last_state}' adb_connect='{last_connect}' logs_tail='{logs}'"
        )

    def _get_container_logs(self, name, tail=200):
        try:
            proc = subprocess.run(
                ["docker", "logs", "--tail", str(tail), name],
                capture_output=True,
                text=True,
                timeout=5,
                check=True,
            )
            return (proc.stdout or proc.stderr or "").strip().replace("\n", "\\n")
        except Exception:
            return ""

    def _apply_post_boot_identity(self, fp):
        logger.info("  🔧 Applying runtime identity values...")
        commands = [
            ("shell", "settings", "put", "secure", "android_id", fp["android_id"]),
            ("shell", "settings", "put", "global", "device_name", fp["ro.product.model"]),
            ("shell", "settings", "put", "secure", "bluetooth_name", fp["ro.product.model"]),
        ]
        for cmd in commands:
            try:
                self._adb(*cmd, check=False, timeout=12, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception as e:
                logger.warning(f"Runtime identity apply failed for {' '.join(cmd)}: {e}")

    def _read_prop(self, key):
        try:
            proc = self._adb("shell", "getprop", key, capture_output=True, text=True, timeout=10)
            if proc.returncode == 0:
                return (proc.stdout or "").strip()
        except Exception:
            return ""
        return ""

    def _read_setting(self, namespace, key):
        try:
            proc = self._adb("shell", "settings", "get", namespace, key, capture_output=True, text=True, timeout=10)
            if proc.returncode == 0:
                return (proc.stdout or "").strip()
        except Exception:
            return ""
        return ""

    def _read_eth_mac(self):
        try:
            proc = self._adb("shell", "cat", "/sys/class/net/eth0/address", capture_output=True, text=True, timeout=10)
            if proc.returncode == 0:
                return (proc.stdout or "").strip().lower()
        except Exception:
            return ""
        return ""

    def _verify_identity(self, fp, strict_props=True):
        expected_to_actual = {
            "ro.product.manufacturer": self._read_prop("ro.product.manufacturer"),
            "ro.product.brand": self._read_prop("ro.product.brand"),
            "ro.product.model": self._read_prop("ro.product.model"),
            "ro.product.name": self._read_prop("ro.product.name"),
            "ro.product.device": self._read_prop("ro.product.device"),
            "ro.serialno": self._read_prop("ro.serialno"),
            "ro.boot.serialno": self._read_prop("ro.boot.serialno"),
            "ro.build.fingerprint": self._read_prop("ro.build.fingerprint"),
        }
        android_id_actual = self._read_setting("secure", "android_id")
        mac_actual = self._read_eth_mac()
        mismatches = []
        required_keys = [
            "ro.product.manufacturer",
            "ro.product.brand",
            "ro.product.model",
            "ro.product.name",
            "ro.product.device",
            "ro.build.fingerprint",
        ]
        for key, actual in expected_to_actual.items():
            expected = fp["build_fingerprint"] if key == "ro.build.fingerprint" else fp.get(key, "")
            if strict_props and expected and actual and expected != actual:
                mismatches.append((key, expected, actual))
        if fp.get("android_id") and android_id_actual and fp["android_id"] != android_id_actual:
            mismatches.append(("android_id", fp["android_id"], android_id_actual))
        if strict_props and fp.get("wifi.mac.address") and mac_actual and fp["wifi.mac.address"].lower() != mac_actual:
            mismatches.append(("wifi.mac.address", fp["wifi.mac.address"].lower(), mac_actual))
        critical_mismatches = [m for m in mismatches if (m[0] in required_keys and strict_props) or m[0] == "android_id"]
        if strict_props:
            for key in required_keys:
                if not expected_to_actual.get(key):
                    raise Exception(f"Identity verification failed: missing value for {key}")
        if critical_mismatches:
            text = "; ".join(f"{k}: expected '{e}' got '{a}'" for k, e, a in critical_mismatches)
            raise Exception(f"Identity verification failed: {text}")
        logger.info(
            "Identity verified: "
            f"manufacturer={expected_to_actual['ro.product.manufacturer']}, "
            f"brand={expected_to_actual['ro.product.brand']}, "
            f"model={expected_to_actual['ro.product.model']}, "
            f"device={expected_to_actual['ro.product.device']}, "
            f"serial={expected_to_actual['ro.serialno']}, "
            f"fingerprint={expected_to_actual['ro.build.fingerprint']}, "
            f"android_id={android_id_actual}, "
            f"mac={mac_actual or fp['wifi.mac.address'].lower()}"
        )
    
    def apply_proxy(self):
        self._adb("shell", "settings", "put", "global", "http_proxy", DEVICE_PROXY_ADDRESS, check=True, timeout=30)
    
    def launch_app(self, package_name):
        logger.info(f"Launching {package_name}...")
        try:
            self._adb("shell", "monkey", "-p", package_name, "-c", "android.intent.category.LAUNCHER", "1", check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
        except subprocess.CalledProcessError as e:
            raise Exception(f"Failed to launch app {package_name}: {e}") from e
    
    def install_split_apks(self, apk_paths):
        logger.info(f"Installing Split APKs: {apk_paths}...")
        valid_paths = []
        for p in apk_paths:
            p_obj = Path(p)
            if not p_obj.is_absolute():
                 p_obj = PROJECT_BIN / p_obj.name
            if p_obj.exists():
                valid_paths.append(str(p_obj))
            else:
                raise Exception(f"APK not found: {p_obj}")    
        try:
             cmd = ["install-multiple", "-r", "-g"] + valid_paths
             self._adb(*cmd, check=True, timeout=120)
             logger.info("Split APKs Installed successfully.")
        except subprocess.CalledProcessError as e:
             raise Exception(f"Failed to install Split APKs: {e}")
    
    def get_all_apks(self):
        return list(PROJECT_BIN.glob("*.apk"))

    def connect_appium(self, server_url=None):
        if server_url is None:
            server_url = APPIUM_SERVER_URL
        logger.info(f"Connecting to Appium at {server_url}...")
        try:
            urlopen(f"{server_url}/status", timeout=APPIUM_CONNECT_TIMEOUT)
        except Exception:
            raise Exception(f"Appium Server not found at {server_url}.")
        options = UiAutomator2Options()
        options.platform_name = 'Android'
        options.automation_name = 'UiAutomator2'
        options.device_name = "Android Device" 
        options.no_reset = True
        options.set_capability('appium:autoLaunch', False)
        options.set_capability('appium:appWaitActivity', '*')
        options.set_capability('appium:uiautomator2ServerLaunchTimeout', 60000)
        options.set_capability('appium:adbExecTimeout', 60000)  
        options.set_capability('appium:newCommandTimeout', 300)
        try:
            driver = webdriver.Remote(server_url, options=options)
            logger.info("Generic Driver connected. Manually activating Instagram...")
            logger.info("Appium Connected.")
            return driver
        except Exception as e:
            logger.error(f"Failed to create Appium driver: {e}")
            raise Exception(f"Failed to create Appium driver: {e}")

    def click_text(self, driver, text, exact=False, timeout=UI_ELEMENT_TIMEOUT):
        logger.info(f"Looking for text: '{text}'...")
        try:
            wait = WebDriverWait(driver, timeout)
            escaped_text = re.escape(text)
            if not exact:
                selector = f'new UiSelector().textMatches("(?i){escaped_text}")'
            else:
                selector = f'new UiSelector().text("{text}")'
            btn = wait.until(EC.presence_of_element_located((AppiumBy.ANDROID_UIAUTOMATOR, selector)))
            btn.click()
            logger.info(f"Successfully clicked '{text}'.")
        except Exception as e:
            raise Exception(f"Could not click text '{text}' within {timeout}s: {e}") from e

    def type_text(self, driver, hint_text, input_text, exact=False, timeout=UI_ELEMENT_TIMEOUT):
        logger.info(f"Looking for input field with hint: '{hint_text}'...")
        self.click_text(driver, hint_text, exact=exact, timeout=timeout)
        logger.info(f"Field '{hint_text}' clicked. Waiting for focus...")
        logger.info(f"Typing: {input_text}...")
        for char in input_text:
            if char == ' ':
                self._adb("shell", "input", "text", "%s", check=False, timeout=10)
            elif char == "'":
                self._adb("shell", "input", "text", "\\'", check=False, timeout=10)
            else:
                self._adb("shell", "input", "text", char, check=False, timeout=10)
            sleep(0.1)
        logger.info("Typing complete.")

    def swipe(self, driver, start_x, start_y, end_x, end_y, duration_ms=500):
        try:
            actions = ActionChains(driver)
            actions.w3c_actions = ActionBuilder(driver, mouse=PointerInput(interaction.POINTER_TOUCH, "touch"))
            actions.w3c_actions.pointer_action.move_to_location(start_x, start_y)
            actions.w3c_actions.pointer_action.pointer_down()
            actions.w3c_actions.pointer_action.pause(duration_ms / 1000)
            actions.w3c_actions.pointer_action.move_to_location(end_x, end_y)
            actions.w3c_actions.pointer_action.release()
            actions.perform()
        except Exception as e:
            try:
                subprocess.run([str(ADB_BIN), "shell", "input", "swipe", str(start_x), str(start_y), str(end_x), str(end_y), str(duration_ms)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception as fallback_error:
                raise Exception(f"Swipe failed via W3C and ADB fallback. w3c_error={e}; adb_error={fallback_error}") from fallback_error

    def minimize_and_restore_app(self, package_name=None):
        try:
            if package_name is None:
                package_name = INSTAGRAM_PACKAGE
            logger.info("  📱 Human behavior: Checking background apps...")
            self._adb("shell", "input", "keyevent", "KEYCODE_HOME", check=True, timeout=5)
            sleep(0.5)
            logger.info(f"Restoring app ({package_name})...")
            self.launch_app(package_name)
        except Exception as e:
            raise Exception(f"Failed to minimize and restore app: {e}")

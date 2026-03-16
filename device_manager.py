import json
import logging
import random
import subprocess
import uuid
from datetime import datetime
from pathlib import Path
from time import sleep, time
from appium import webdriver
from appium.options.android import UiAutomator2Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.actions import interaction
from selenium.webdriver.common.actions.action_builder import ActionBuilder
from selenium.webdriver.common.actions.pointer_input import PointerInput
from config import (
    PROJECT_BIN, LOG_DIR, ADB_BIN,
    APPIUM_SERVER_URL, INSTAGRAM_PACKAGE, GALLERY_PHOTO_DEST,
    DEVICE_PROXY_ADDRESS, UI_ELEMENT_TIMEOUT,
    ADB_DEFAULT_TIMEOUT, BOOT_TIMEOUT, APPIUM_CONNECT_TIMEOUT,
    REDROID_IMAGE, REDROID_GPU_MODE, REDROID_WIDTH, REDROID_HEIGHT, REDROID_FPS,
    REDROID_AUDIT_ENABLED, REDROID_VERIFY_STRICT,
    DEVICE_PROFILES,
)
from session import SessionContext

logger = logging.getLogger("DeviceManager")

class DeviceManager:

    def __init__(self):
        self.adb_port = 5555
        self.fingerprint = None
        self.previous_fingerprint = None
        self._boot_start_time = None
        if not ADB_BIN.exists():
            raise FileNotFoundError(f"adb binary not found at {ADB_BIN}")

    def _adb(self, *args, timeout=ADB_DEFAULT_TIMEOUT, check=False, **kwargs):
        addr = f"localhost:{self.adb_port}"
        return subprocess.run(
            [str(ADB_BIN), "-s", addr, *args],
            timeout=timeout, check=check, capture_output=True, text=True, **kwargs)

    def _random_serial(self, length=12):
        return "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", k=length))

    def _random_hex(self, length=16):
        return "".join(random.choices("0123456789abcdef", k=length))

    def _random_incremental(self):
        return str(random.randint(800000000, 999999999))

    def _random_mac(self):
        first_byte = (random.randint(0, 255) & 0xFE) | 0x02
        rest = [random.randint(0, 255) for _ in range(5)]
        return ":".join(f"{b:02x}" for b in [first_byte] + rest)

    def _random_imei(self):
        digits = [random.randint(0, 9) for _ in range(14)]
        total = 0
        for i, d in enumerate(digits):
            if i % 2 == 1:
                d *= 2
                if d > 9:
                    d -= 9
            total += d
        check = (10 - (total % 10)) % 10
        return "".join(str(d) for d in digits) + str(check)

    def generate_random_identity(self):
        profile = random.choice(DEVICE_PROFILES)
        incremental = self._random_incremental()
        build_id = f"RQ3A.{random.randint(210000, 219999)}.00{random.randint(1, 9)}"
        security_patch = random.choice(
            ["2024-01-05", "2024-02-05", "2024-03-05", "2024-04-05"])

        previous = self.previous_fingerprint or {}
        serial = self._random_serial(12)
        mac = self._random_mac()
        bt_mac = self._random_mac()
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
        desc = f"{profile['name']}-user 11 {build_id} {incremental} release-keys"
        timezone = random.choice(profile.get("timezones", ["America/New_York"]))
        locale = random.choice(profile.get("locales", ["en-US"]))

        self.fingerprint = {
            "ro.product.manufacturer":  profile["manufacturer"],
            "ro.product.brand":         profile["brand"],
            "ro.product.model":         profile["model"],
            "ro.product.name":          profile["name"],
            "ro.product.device":        profile["device"],
            "ro.serialno":              serial,
            "ro.boot.serialno":         serial,
            "gsm.version.baseband":     f"M8350-{random.randint(1000,9999)}GEN_PACK-1",
            "hw.gsmModem.imei":         self._random_imei(),
            "wifi.mac.address":         mac,
            "bluetooth.mac.address":    bt_mac,
            "phone_id":                 str(uuid.uuid4()),
            "guid":                     guid,
            "google_ad_id":             str(uuid.uuid4()),
            "android_id":               android_id,
            "build_release":            "11",
            "build_id":                 build_id,
            "build_incremental":        incremental,
            "build_security_patch":     security_patch,
            "build_fingerprint":        build_fp,
            "build_description":        desc,
            "display_density":          int(profile.get("density", 420)),
            "display_resolution":       profile.get("resolution", "1080x1920"),
            "timezone":                 timezone,
            "locale":                   locale,
        }
        self.previous_fingerprint = dict(self.fingerprint)
        return self.fingerprint

    def get_device_fingerprint(self):
        if self.fingerprint is None:
            raise Exception("No fingerprint generated yet. Call generate_random_identity() first.")
        return self.fingerprint

    @staticmethod
    def _prop_val(value: str) -> str:
        return str(value).replace(" ", "%20")

    def _build_identity_args(self, fp):
        pv = self._prop_val
        build_fp = fp["build_fingerprint"]
        desc = fp["build_description"]
        return [
            f"ro.product.manufacturer={pv(fp['ro.product.manufacturer'])}",
            f"ro.product.brand={pv(fp['ro.product.brand'])}",
            f"ro.product.model={pv(fp['ro.product.model'])}",
            f"ro.product.name={pv(fp['ro.product.name'])}",
            f"ro.product.device={pv(fp['ro.product.device'])}",
            f"ro.product.system.manufacturer={pv(fp['ro.product.manufacturer'])}",
            f"ro.product.system.brand={pv(fp['ro.product.brand'])}",
            f"ro.product.system.model={pv(fp['ro.product.model'])}",
            f"ro.product.system.name={pv(fp['ro.product.name'])}",
            f"ro.product.system.device={pv(fp['ro.product.device'])}",
            f"ro.product.vendor.manufacturer={pv(fp['ro.product.manufacturer'])}",
            f"ro.product.vendor.brand={pv(fp['ro.product.brand'])}",
            f"ro.product.vendor.model={pv(fp['ro.product.model'])}",
            f"ro.product.vendor.name={pv(fp['ro.product.name'])}",
            f"ro.product.vendor.device={pv(fp['ro.product.device'])}",
            f"ro.product.product.manufacturer={pv(fp['ro.product.manufacturer'])}",
            f"ro.product.product.brand={pv(fp['ro.product.brand'])}",
            f"ro.product.product.model={pv(fp['ro.product.model'])}",
            f"ro.product.product.name={pv(fp['ro.product.name'])}",
            f"ro.product.product.device={pv(fp['ro.product.device'])}",
            f"androidboot.serialno={fp['ro.serialno']}",
            f"ro.build.fingerprint={pv(build_fp)}",
            f"ro.system.build.fingerprint={pv(build_fp)}",
            f"ro.vendor.build.fingerprint={pv(build_fp)}",
            f"ro.product.build.fingerprint={pv(build_fp)}",
            f"ro.bootimage.build.fingerprint={pv(build_fp)}",
            f"ro.build.version.release={pv(fp['build_release'])}",
            f"ro.build.id={pv(fp['build_id'])}",
            f"ro.build.version.incremental={pv(fp['build_incremental'])}",
            f"ro.build.version.security_patch={pv(fp['build_security_patch'])}",
            f"ro.build.description={pv(desc)}",
            f"ro.build.display.id={pv(desc)}",
            "ro.build.type=user",
            "ro.build.tags=release-keys",
        ]

    def get_docker_cmd(self, fp, ctx: SessionContext):
        gpu_mode = (REDROID_GPU_MODE or "guest").strip().lower()
        if gpu_mode not in {"guest", "host"}:
            gpu_mode = "guest"
        res = fp.get("display_resolution", "1080x1920")
        parts = res.split("x")
        width = int(parts[0]) if len(parts) == 2 else REDROID_WIDTH
        height = int(parts[1]) if len(parts) == 2 else REDROID_HEIGHT
        boot_args = [
            f"androidboot.redroid_width={width}",
            f"androidboot.redroid_height={height}",
            f"androidboot.redroid_fps={REDROID_FPS}",
            f"androidboot.redroid_gpu_mode={gpu_mode}",
            "androidboot.use_memfd=1",
            "debug.sf.nobootanimation=1",
            *self._build_identity_args(fp),
        ]
        return [
            "docker", "run", "-d", "--rm", "--privileged",
            "--name", ctx.container_name,
            "--hostname", f"d-{ctx.session_id[:12]}",
            "--label", f"farm.session_id={ctx.session_id}",
            "--pull", "never",
            "-v", "/dev/binderfs:/dev/binderfs",
            "--tmpfs", "/data:rw,exec,suid",
            f"--mac-address={fp['wifi.mac.address']}",
            "-p", f"{ctx.adb_port}:5555",
            REDROID_IMAGE,
            *boot_args,
        ]

    def start_emulator(self, ctx: SessionContext):
        self._validate_container_inputs(ctx.container_name, ctx.adb_port)
        ctx.runtime_dir.mkdir(parents=True, exist_ok=True)
        self.adb_port = ctx.adb_port
        self._preflight_docker()
        self._assert_binderfs()
        fp = self.generate_random_identity()
        logger.info(
            f"[{ctx.session_id}] Starting {ctx.container_name}:{ctx.adb_port} | "
            f"{fp['ro.product.manufacturer']} {fp['ro.product.model']} | "
            f"serial={fp['ro.serialno']} | android_id={fp['android_id']} | "
            f"tz={fp['timezone']} | locale={fp['locale']}")
        self.kill_emulator(name=ctx.container_name, port=ctx.adb_port)
        self._boot_start_time = time()
        
        cmd = self.get_docker_cmd(fp, ctx)
        proc = subprocess.run(cmd, check=True, capture_output=True, text=True)
        container_id = (proc.stdout or "").strip()
        if container_id:
            logger.info(f"  Container started: {container_id[:12]}")
        self._assert_container_running(ctx.container_name)
        self.wait_for_adb(port=ctx.adb_port, timeout=max(BOOT_TIMEOUT, 60),
                          name=ctx.container_name)
        
        boot_elapsed = round(time() - self._boot_start_time, 1)
        logger.info(f"  🕐 Boot completed in {boot_elapsed}s")
        self._apply_post_boot_identity(fp)
        if REDROID_AUDIT_ENABLED:
            self._dump_fingerprint_audit(ctx)
        if REDROID_VERIFY_STRICT:
            self._verify_identity(fp)
        self._save_identity_report(fp, ctx, boot_elapsed)
        return {
            "session_id": ctx.session_id,
            "container_name": ctx.container_name,
            "boot_seconds": boot_elapsed,
            "adb_port": ctx.adb_port,
            "android_id": fp["android_id"],
            "serial": fp["ro.serialno"],
            "mac": fp["wifi.mac.address"],
            "model": fp["ro.product.model"],
        }

    def kill_emulator(self, name="redroid_0", port=5555):
        addr = f"localhost:{port}"
        subprocess.run([str(ADB_BIN), "disconnect", addr],
                       capture_output=True, text=True, timeout=10)
        subprocess.run(["docker", "stop", name],
                       capture_output=True, text=True, timeout=20)
        subprocess.run(["docker", "rm", "-f", name],
                       capture_output=True, text=True, timeout=10)

    def _validate_container_inputs(self, name, port):
        if not name or not isinstance(name, str):
            raise ValueError(f"Invalid container name: {name}")
        if not (1024 <= port <= 65535):
            raise ValueError(f"Invalid ADB port: {port}")

    def _preflight_docker(self):
        subprocess.run(["docker", "info"], check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)

    def _assert_binderfs(self):
        if not Path("/dev/binderfs").exists():
            raise Exception("Missing /dev/binderfs on host. Binderfs must be mounted for ReDroid.")

    def _assert_container_running(self, name):
        proc = subprocess.run(
            ["docker", "inspect", "-f", "{{.State.Running}}", name],
            capture_output=True, text=True, timeout=10)
        if proc.stdout.strip() != "true":
            logs = self._get_container_logs(name)
            raise Exception(f"Container {name} is not running. logs: {logs}")

    def wait_for_adb(self, port=5555, timeout=BOOT_TIMEOUT, name="redroid_0"):
        addr = f"localhost:{port}"
        deadline = time() + timeout
        logger.info(f"Waiting for {name} to boot (via ADB)...")
        subprocess.run([str(ADB_BIN), "connect", addr],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20)
        while time() < deadline:
            try:
                proc = subprocess.run(
                    [str(ADB_BIN), "-s", addr, "shell", "getprop", "sys.boot_completed"],
                    capture_output=True, text=True, timeout=20)
            except:
                try:
                    subprocess.run([str(ADB_BIN), "connect", addr],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20)
                except:
                    continue
                continue
            if proc.stdout.strip() == "1":
                logger.info(f"  ✅ {name} boot_completed=1")
                return
            sleep(3)
        p = subprocess.run([str(ADB_BIN), "-s", addr, "get-state"],
                           capture_output=True, text=True, timeout=5)
        state = p.stdout.strip()
        raise Exception(
            f"Timeout waiting for {name} to boot. adb_state='{state}' "
            f"logs_tail='{self._get_container_logs(name)}'")

    def _get_container_logs(self, name, tail=200):
        try:
            proc = subprocess.run(
                ["docker", "logs", "--tail", str(tail), name],
                capture_output=True, text=True, timeout=10)
            combined = (proc.stdout or "") + (proc.stderr or "")
            lines = combined.strip().splitlines()
            return "\\n".join(lines[-5:])
        except Exception:
            return "<unavailable>"

    def _apply_post_boot_identity(self, fp):
        logger.info("  🔧 Applying post-boot identity...")
        timezone = fp.get("timezone", "America/New_York")
        locale = fp.get("locale", "en-US")
        lang, _, region = locale.partition("-")
        battery_level = random.randint(15, 92)
        battery_temp = random.randint(280, 390)
        commands = [
            ("shell", "settings", "put", "secure",  "android_id",      fp["android_id"]),
            ("shell", "settings", "put", "global",  "device_name",     fp["ro.product.model"]),
            ("shell", "settings", "put", "secure",  "bluetooth_name",  fp["ro.product.model"]),
            ("shell", "settings", "put", "global",  "auto_time_zone",  "0"),
            ("shell", "setprop",  "persist.sys.timezone", timezone),
            ("shell", "settings", "put", "system",  "user_timezone",   timezone),
            ("shell", "setprop",  "persist.sys.locale",   locale),
            ("shell", "setprop",  "persist.sys.language",  lang),
            ("shell", "setprop",  "persist.sys.country",   region),
            ("shell", "dumpsys",  "battery", "unplug"),
            ("shell", "dumpsys",  "battery", "set", "level", str(battery_level)),
            ("shell", "dumpsys",  "battery", "set", "temp", str(battery_temp)),
            ("shell", "dumpsys",  "battery", "set", "status", "3"),
        ]
        for cmd in commands:
            self._adb(*cmd, check=False, timeout=12)
        logger.info(f"  🔑 android_id={fp['android_id']} | tz={timezone} | locale={locale}")

    def _read_prop(self, key):
        try:
            result = self._adb("shell", "getprop", key, timeout=10)
            return result.stdout.strip() if result.returncode == 0 else ""
        except Exception:
            return ""

    def _read_setting(self, namespace, key):
        try:
            result = self._adb("shell", "settings", "get", namespace, key, timeout=10)
            return result.stdout.strip() if result.returncode == 0 else ""
        except Exception:
            return ""

    def _read_eth_mac(self):
        try:
            result = self._adb("shell", "cat", "/sys/class/net/eth0/address", timeout=10)
            return result.stdout.strip() if result.returncode == 0 else ""
        except Exception:
            return ""

    def _verify_identity(self, fp):
        checks = {
            "ro.product.manufacturer": fp["ro.product.manufacturer"],
            "ro.product.brand": fp["ro.product.brand"],
            "ro.product.model": fp["ro.product.model"],
            "ro.product.name": fp["ro.product.name"],
            "ro.product.device": fp["ro.product.device"],
            "ro.serialno": fp["ro.serialno"],
            "ro.build.fingerprint": fp["build_fingerprint"],
        }
        mismatches = []
        actuals = {}
        for key, expected in checks.items():
            actual = self._read_prop(key).replace("%20", " ").strip()
            expected_norm = expected.replace("%20", " ").strip()
            actuals[key] = actual
            if expected_norm and actual and expected_norm != actual:
                mismatches.append((key, expected_norm, actual))

        android_id_actual = self._read_setting("secure", "android_id")
        if fp["android_id"] and android_id_actual and fp["android_id"] != android_id_actual:
            mismatches.append(("android_id", fp["android_id"], android_id_actual))

        if mismatches:
            text = "; ".join(f"{k}: expected '{e}' got '{a}'" for k, e, a in mismatches)
            raise Exception(f"Identity verification failed: {text}")

        logger.info(
            f"  ✅ Identity verified: "
            f"model={actuals.get('ro.product.model')} "
            f"serial={actuals.get('ro.serialno')} "
            f"android_id={android_id_actual} "
            f"mac={self._read_eth_mac()}")

    def _dump_fingerprint_audit(self, ctx: SessionContext):
        audit_dir = ctx.runtime_dir
        audit_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        audit_file = audit_dir / f"fingerprint_audit_{ts}.txt"
        try:
            result = self._adb("shell", "getprop", timeout=15)
            lines = result.stdout.strip().splitlines() if result.returncode == 0 else []
            fp_lines = [l for l in lines if any(k in l for k in
                        ["ro.product", "ro.build", "ro.serialno", "ro.boot",
                         "persist.sys", "android_id", "bluetooth", "wifi"])]
            audit_file.write_text("\n".join(sorted(fp_lines)), encoding="utf-8")
            logger.info(f"  📋 Audit dumped: {audit_file}")
        except Exception as e:
            pass

    def _save_identity_report(self, fp, ctx: SessionContext, boot_elapsed):
        report_dir = ctx.runtime_dir
        report_dir.mkdir(parents=True, exist_ok=True)
        report = {
            "session_id": ctx.session_id,
            "container_name": ctx.container_name,
            "adb_port": ctx.adb_port,
            "timestamp": datetime.now().isoformat(),
            "boot_seconds": boot_elapsed,
            "identity": {
                "manufacturer": fp["ro.product.manufacturer"],
                "brand": fp["ro.product.brand"],
                "model": fp["ro.product.model"],
                "device": fp["ro.product.device"],
                "serial": fp["ro.serialno"],
                "android_id": fp["android_id"],
                "wifi_mac": fp["wifi.mac.address"],
                "bt_mac": fp["bluetooth.mac.address"],
                "imei": fp["hw.gsmModem.imei"],
                "build_fingerprint": fp["build_fingerprint"],
                "timezone": fp.get("timezone"),
                "locale": fp.get("locale"),
                "display": fp.get("display_resolution"),
            },
        }
        report_file = report_dir / "identity_report.json"
        report_file.write_text(json.dumps(report, indent=2), encoding="utf-8")
        logger.info(f"  📄 Report saved: {report_file}")

    def apply_proxy(self, proxy_address=None):
        addr = proxy_address or DEVICE_PROXY_ADDRESS
        self._adb("shell", "settings", "put", "global", "http_proxy", addr,
                   check=False, timeout=10)

    def seed_gallery(self):
        local = PROJECT_BIN / "selfie.jpg"
        if not local.exists():
            return
        self._adb("push", str(local), GALLERY_PHOTO_DEST, check=True, timeout=30)
        self._adb("shell", "am", "broadcast", "-a",
                   "android.intent.action.MEDIA_SCANNER_SCAN_FILE",
                   "-d", f"file://{GALLERY_PHOTO_DEST}", check=False, timeout=10)
        logger.info("  📸 Gallery seeded")

    def warmup_actions(self):
        logger.info("  🔥 Performing warmup...")
        self._adb("shell", "am", "start", "-a", "android.intent.action.SEND",
                   "-t", "image/*", "--eu", "android.intent.extra.STREAM",
                   f"file://{GALLERY_PHOTO_DEST}", INSTAGRAM_PACKAGE,
                   check=True, timeout=10)
        logger.info("  Warmup: Share intent launched")

    def install_split_apks(self, apk_paths):
        logger.info(f"  📦 Installing {len(apk_paths)} APK(s)...")
        cmd = [str(ADB_BIN), "-s", f"localhost:{self.adb_port}",
               "install-multiple", "-r", "-t"]
        cmd.extend(str(p) for p in apk_paths)
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if proc.returncode != 0 or "Success" not in (proc.stdout or ""):
            raise Exception(f"APK install failed: {proc.stderr or proc.stdout}")
        logger.info("  ✅ APK installed")

    def get_all_apks(self):
        apk_dir = PROJECT_BIN
        if not apk_dir.exists():
            return []
        return sorted(apk_dir.glob("*.apk"))

    def connect_appium(self, server_url=None):
        url = server_url or APPIUM_SERVER_URL
        logger.info(f"  🔌 Connecting Appium to {url}...")
        input("connecting to appium, press enter")
        opts = UiAutomator2Options()
        opts.platform_name = "Android"
        opts.device_name = f"localhost:{self.adb_port}"
        opts.no_reset = True
        opts.full_reset = False
        opts.auto_grant_permissions = True
        opts.app_package = INSTAGRAM_PACKAGE
        opts.app_activity = "com.instagram.mainactivity.LauncherActivity"
        opts.new_command_timeout = 300
        driver = webdriver.Remote(url, options=opts)
        logger.info("  ✅ Appium connected")
        return driver

    def click_text(self, driver, text, exact=False, timeout=UI_ELEMENT_TIMEOUT):
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        if exact:
            xpath = f'//*[@text="{text}"]'
        else:
            xpath = f'//*[contains(@text, "{text}")]'
        el = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.XPATH, xpath)))
        el.click()

    def type_text(self, driver, hint_text, input_text, exact=False, timeout=UI_ELEMENT_TIMEOUT):
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        if exact:
            xpath = f'//*[@text="{hint_text}"]'
        else:
            xpath = f'//*[contains(@text, "{hint_text}")]'
        el = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.XPATH, xpath)))
        el.click()
        el.send_keys(input_text)

    def swipe(self, driver, start_x, start_y, end_x, end_y, duration_ms=500):
        pointer = PointerInput(interaction.POINTER_TOUCH, "touch")
        actions = ActionBuilder(driver, mouse=pointer)
        actions.pointer_action.move_to_location(start_x, start_y)
        actions.pointer_action.pointer_down()
        actions.pointer_action.pause(duration_ms / 1000)
        actions.pointer_action.move_to_location(end_x, end_y)
        actions.pointer_action.pointer_up()
        actions.perform()

    def minimize_and_restore_app(self, package_name=None):
        pkg = package_name or INSTAGRAM_PACKAGE
        self._adb("shell", "input", "keyevent", "3", check=False, timeout=5)
        sleep(random.uniform(1.5, 3.0))
        self._adb("shell", "monkey", "-p", pkg, "-c",
                   "android.intent.category.LAUNCHER", "1",
                   check=False, timeout=10)
        sleep(random.uniform(0.8, 1.5))

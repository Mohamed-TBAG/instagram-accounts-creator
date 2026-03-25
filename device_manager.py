import json
import logging
import random
import re
import subprocess
import uuid
import xml.etree.ElementTree as ET
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
    REDROID_AUDIT_ENABLED, REDROID_VERIFY_STRICT, GAID_DISCOVERY_ENABLED,
    GAID_RESET_ON_BOOT, GAID_DISCOVERY_TIMEOUT,
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
        self.identity_registry_path = LOG_DIR / "identity_registry.json"
        self.identity_registry = self._load_identity_registry()
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

    def _load_identity_registry(self):
        if not self.identity_registry_path.exists():
            return {
                "serials": [],
                "android_ids": [],
                "wifi_macs": [],
                "bt_macs": [],
                "imeis": [],
                "guids": [],
                "phone_ids": [],
                "gaids": [],
            }
        try:
            data = json.loads(self.identity_registry_path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("Registry payload must be an object")
            return {
                "serials": list(data.get("serials", [])),
                "android_ids": list(data.get("android_ids", [])),
                "wifi_macs": list(data.get("wifi_macs", [])),
                "bt_macs": list(data.get("bt_macs", [])),
                "imeis": list(data.get("imeis", [])),
                "guids": list(data.get("guids", [])),
                "phone_ids": list(data.get("phone_ids", [])),
                "gaids": list(data.get("gaids", [])),
            }
        except Exception:
            logger.warning("  ⚠️ Identity registry is corrupt; starting fresh.")
            return {
                "serials": [],
                "android_ids": [],
                "wifi_macs": [],
                "bt_macs": [],
                "imeis": [],
                "guids": [],
                "phone_ids": [],
                "gaids": [],
            }

    def _save_identity_registry(self):
        self.identity_registry_path.parent.mkdir(parents=True, exist_ok=True)
        self.identity_registry_path.write_text(
            json.dumps(self.identity_registry, indent=2),
            encoding="utf-8",
        )

    def _value_seen(self, bucket, value):
        if not value:
            return False
        return value in self.identity_registry.get(bucket, [])

    def _mark_value(self, bucket, value):
        if not value:
            return
        target = self.identity_registry.setdefault(bucket, [])
        if value in target:
            return
        target.append(value)
        # Keep file bounded while preserving long enough history.
        if len(target) > 5000:
            del target[:-5000]

    def _identity_candidate_reused(self, candidate):
        return any([
            self._value_seen("serials", candidate.get("ro.serialno")),
            self._value_seen("android_ids", candidate.get("android_id")),
            self._value_seen("wifi_macs", candidate.get("wifi.mac.address")),
            self._value_seen("bt_macs", candidate.get("bluetooth.mac.address")),
            self._value_seen("imeis", candidate.get("hw.gsmModem.imei")),
            self._value_seen("guids", candidate.get("guid")),
            self._value_seen("phone_ids", candidate.get("phone_id")),
        ])

    def _mark_identity_used(self, fp):
        self._mark_value("serials", fp.get("ro.serialno"))
        self._mark_value("android_ids", fp.get("android_id"))
        self._mark_value("wifi_macs", fp.get("wifi.mac.address"))
        self._mark_value("bt_macs", fp.get("bluetooth.mac.address"))
        self._mark_value("imeis", fp.get("hw.gsmModem.imei"))
        self._mark_value("guids", fp.get("guid"))
        self._mark_value("phone_ids", fp.get("phone_id"))
        self._mark_value("gaids", fp.get("google_ad_id"))
        self._save_identity_registry()

    def generate_random_identity(self):
        previous = self.previous_fingerprint or {}
        for _ in range(80):
            profile = random.choice(DEVICE_PROFILES)
            incremental = self._random_incremental()
            build_id = f"RQ3A.{random.randint(210000, 219999)}.00{random.randint(1, 9)}"
            security_patch = random.choice(
                ["2024-01-05", "2024-02-05", "2024-03-05", "2024-04-05"])
            serial = self._random_serial(12)
            mac = self._random_mac()
            bt_mac = self._random_mac()
            android_id = self._random_hex(16)
            guid = str(uuid.uuid4())
            phone_id = str(uuid.uuid4())
            imei = self._random_imei()

            if (
                serial == previous.get("ro.serialno")
                or mac == previous.get("wifi.mac.address")
                or bt_mac == previous.get("bluetooth.mac.address")
                or android_id == previous.get("android_id")
                or guid == previous.get("guid")
                or phone_id == previous.get("phone_id")
                or imei == previous.get("hw.gsmModem.imei")
            ):
                continue

            build_fp = (
                f"{profile['brand']}/{profile['name']}/{profile['device']}:"
                f"11/{build_id}/{incremental}:user/release-keys"
            )
            desc = f"{profile['name']}-user 11 {build_id} {incremental} release-keys"
            timezone = random.choice(profile.get("timezones", ["America/New_York"]))
            locale = random.choice(profile.get("locales", ["en-US"]))

            candidate = {
                "ro.product.manufacturer":  profile["manufacturer"],
                "ro.product.brand":         profile["brand"],
                "ro.product.model":         profile["model"],
                "ro.product.name":          profile["name"],
                "ro.product.device":        profile["device"],
                "ro.product.board":         profile.get("board", profile["device"]),
                "ro.board.platform":        profile.get("platform", profile["device"]),
                "ro.hardware":              profile.get("hardware", profile.get("platform", profile["device"])),
                "ro.serialno":              serial,
                "ro.boot.serialno":         serial,
                "gsm.version.baseband":     f"M8350-{random.randint(1000,9999)}GEN_PACK-1",
                "hw.gsmModem.imei":         imei,
                "wifi.mac.address":         mac,
                "bluetooth.mac.address":    bt_mac,
                "phone_id":                 phone_id,
                "guid":                     guid,
                # Filled post-boot by reading the OS ad-id provider (if available).
                "google_ad_id":             None,
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
            if self._identity_candidate_reused(candidate):
                continue
            self.fingerprint = candidate
            self.previous_fingerprint = dict(self.fingerprint)
            return self.fingerprint
        raise RuntimeError("Could not generate a unique identity after multiple attempts.")

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
            "--dns", "8.8.8.8",
            "--dns", "8.8.4.4",
            "--add-host", "host.docker.internal:host-gateway",
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
        self._mark_identity_used(fp)
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
        self._adb_connect_with_retry(addr)
        while time() < deadline:
            try:
                proc = subprocess.run(
                    [str(ADB_BIN), "-s", addr, "shell", "getprop", "sys.boot_completed"],
                    capture_output=True, text=True, timeout=20)
            except Exception:
                self._adb_connect_with_retry(addr)
                print("  ⚠️ ADB connection issue — retrying...")
                continue
            stdout = (proc.stdout or "").strip()
            stderr = (proc.stderr or "").strip()
            if "unauthorized" in stderr or "unauthorized" in stdout:
                logger.warning("  ⚠️ ADB unauthorized — restarting server...")
                self._restart_adb_server()
                self._adb_connect_with_retry(addr)
                sleep(3)
                continue
            if stdout == "1":
                logger.info(f"  ✅ {name} boot_completed=1")
                return
            sleep(3)
        p = subprocess.run([str(ADB_BIN), "-s", addr, "get-state"],
                           capture_output=True, text=True, timeout=5)
        state = p.stdout.strip()
        raise RuntimeError(
            f"Timeout waiting for {name} to boot. adb_state='{state}' "
            f"logs_tail='{self._get_container_logs(name)}'")

    def _adb_connect_with_retry(self, addr, max_attempts=3):
        for attempt in range(1, max_attempts + 1):
            proc = subprocess.run(
                [str(ADB_BIN), "connect", addr],
                capture_output=True, text=True, timeout=20)
            out = (proc.stdout or "") + (proc.stderr or "")
            if "unauthorized" in out:
                logger.warning(f"  ADB unauthorized on connect (attempt {attempt}). Restarting.")
                self._restart_adb_server()
                sleep(2)
                continue
            return 
        logger.warning("  Could not resolve ADB unauthorized after retries — proceeding.")

    def _restart_adb_server(self):
        subprocess.run([str(ADB_BIN), "kill-server"],
                       capture_output=True, timeout=10)
        sleep(1)
        subprocess.run([str(ADB_BIN), "start-server"],
                       capture_output=True, timeout=10)
        sleep(1)
        logger.info("  🔄 ADB server restarted")

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
        self._populate_google_ad_id(fp)

    @staticmethod
    def _extract_uuid(text):
        if not text:
            return None
        match = re.search(
            r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b",
            text,
        )
        if match:
            return match.group(0).lower()
        return None

    def _is_package_installed(self, package_name):
        try:
            result = self._adb("shell", "pm", "path", package_name, timeout=12)
            return "package:" in (result.stdout or "")
        except Exception:
            return False

    def _dump_uia_xml(self, remote_path="/sdcard/gaid_uia.xml"):
        try:
            self._adb("shell", "uiautomator", "dump", remote_path, check=False, timeout=15)
            result = self._adb("shell", "cat", remote_path, timeout=12)
            xml_text = result.stdout or ""
            return xml_text
        except Exception:
            return ""

    def _parse_bounds_center(self, bounds):
        m = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds or "")
        if not m:
            return None
        x1, y1, x2, y2 = map(int, m.groups())
        return ((x1 + x2) // 2, (y1 + y2) // 2)

    def _tap_node_text(self, candidates):
        xml_text = self._dump_uia_xml()
        if not xml_text:
            return False
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError:
            return False
        lowered = [c.lower() for c in candidates]
        for node in root.iter("node"):
            text = (node.attrib.get("text") or "").strip()
            content = (node.attrib.get("content-desc") or "").strip()
            hay = f"{text} {content}".lower()
            if not hay:
                continue
            if any(token in hay for token in lowered):
                center = self._parse_bounds_center(node.attrib.get("bounds"))
                if center:
                    self._adb("shell", "input", "tap", str(center[0]), str(center[1]), check=False, timeout=10)
                    sleep(0.8)
                    return True
        return False

    def _probe_gaid_from_ads_settings(self):
        # Try known entry points to Google Ads settings.
        launchers = [
            ("shell", "am", "start", "-W", "-a", "com.google.android.gms.settings.ADS_PRIVACY"),
            ("shell", "am", "start", "-W", "-n",
             "com.google.android.gms/com.google.android.gms.ads.settings.AdsSettingsActivity"),
        ]
        launched = False
        for launcher in launchers:
            res = self._adb(*launcher, check=False, timeout=GAID_DISCOVERY_TIMEOUT)
            blob = ((res.stdout or "") + "\n" + (res.stderr or "")).lower()
            if "error" not in blob and "exception" not in blob:
                launched = True
                break
        if not launched:
            return None

        sleep(2.0)
        if GAID_RESET_ON_BOOT:
            # Best-effort reset path. Text varies by Android/GMS version.
            reset_tapped = self._tap_node_text(["reset advertising id", "create new advertising id"])
            if reset_tapped:
                self._tap_node_text(["ok", "confirm"])
                sleep(1.5)

        xml_text = self._dump_uia_xml()
        gaid = self._extract_uuid(xml_text)
        # Return home regardless of success.
        self._adb("shell", "input", "keyevent", "3", check=False, timeout=8)
        return gaid

    def _populate_google_ad_id(self, fp):
        if not GAID_DISCOVERY_ENABLED:
            fp["google_ad_id"] = None
            return
        if not self._is_package_installed("com.google.android.gms"):
            logger.info("  ℹ️ Google Play services not installed; GAID unavailable on this session.")
            fp["google_ad_id"] = None
            return
        gaid = self._probe_gaid_from_ads_settings()
        if gaid and gaid != "00000000-0000-0000-0000-000000000000":
            fp["google_ad_id"] = gaid
            logger.info(f"  🆔 GAID detected: {gaid}")
            return
        if gaid == "00000000-0000-0000-0000-000000000000":
            logger.info("  ℹ️ GAID is zeroed (deleted/limited by device setting).")
        else:
            logger.warning("  ⚠️ GAID probe did not return a valid UUID.")
        fp["google_ad_id"] = gaid or None

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

        soft_checks = {
            "ro.product.board": fp.get("ro.product.board"),
            "ro.board.platform": fp.get("ro.board.platform"),
            "ro.hardware": fp.get("ro.hardware"),
            "gsm.version.baseband": fp.get("gsm.version.baseband"),
        }
        soft_gaps = []
        for key, expected in soft_checks.items():
            actual = self._read_prop(key).replace("%20", " ").strip()
            expected_norm = (expected or "").replace("%20", " ").strip()
            if expected_norm and actual and actual != expected_norm:
                soft_gaps.append(f"{key}: expected '{expected_norm}' got '{actual}'")
        if soft_gaps:
            logger.warning("  ⚠️ Soft identity gaps: " + "; ".join(soft_gaps))

        logger.info(
            f"  ✅ Identity verified: "
            f"model={actuals.get('ro.product.model')} "
            f"serial={actuals.get('ro.serialno')} "
            f"android_id={android_id_actual} "
            f"mac={self._read_eth_mac()} "
            f"gaid={fp.get('google_ad_id') or 'n/a'}")

    def _collect_runtime_identity_snapshot(self):
        props_of_interest = [
            "ro.product.manufacturer",
            "ro.product.brand",
            "ro.product.model",
            "ro.product.name",
            "ro.product.device",
            "ro.product.board",
            "ro.board.platform",
            "ro.hardware",
            "ro.serialno",
            "ro.boot.serialno",
            "ro.build.fingerprint",
            "ro.system.build.fingerprint",
            "ro.vendor.build.fingerprint",
            "ro.product.build.fingerprint",
            "ro.bootimage.build.fingerprint",
            "ro.build.tags",
            "ro.build.type",
            "ro.build.version.release",
            "ro.build.version.security_patch",
            "ro.product.cpu.abilist",
            "ro.product.cpu.abilist32",
            "ro.product.cpu.abilist64",
        ]
        snapshot = {
            "props": {key: self._read_prop(key) for key in props_of_interest},
            "settings": {
                "secure.android_id": self._read_setting("secure", "android_id"),
                "secure.bluetooth_name": self._read_setting("secure", "bluetooth_name"),
                "global.device_name": self._read_setting("global", "device_name"),
                "global.http_proxy": self._read_setting("global", "http_proxy"),
                "system.user_timezone": self._read_setting("system", "user_timezone"),
            },
            "network": {
                "eth0_mac": self._read_eth_mac(),
            },
            "kernel": {},
        }
        for label, path in [
            ("cpuinfo", "/proc/cpuinfo"),
            ("version", "/proc/version"),
            ("cmdline", "/proc/cmdline"),
        ]:
            try:
                result = self._adb("shell", "cat", path, timeout=10)
                text = (result.stdout or "").strip()
            except Exception:
                text = ""
            if len(text) > 4000:
                text = text[:4000] + "...<truncated>"
            snapshot["kernel"][label] = text
        return snapshot

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
            snapshot = self._collect_runtime_identity_snapshot()
            (audit_dir / f"runtime_identity_snapshot_{ts}.json").write_text(
                json.dumps(snapshot, indent=2), encoding="utf-8"
            )
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
                "google_ad_id": fp.get("google_ad_id"),
                "timezone": fp.get("timezone"),
                "locale": fp.get("locale"),
                "display": fp.get("display_resolution"),
            },
            "runtime_observed": self._collect_runtime_identity_snapshot(),
        }
        report_file = report_dir / "identity_report.json"
        report_file.write_text(json.dumps(report, indent=2), encoding="utf-8")
        logger.info(f"  📄 Report saved: {report_file}")

    def apply_proxy(self, proxy_address=None):
        addr = proxy_address or DEVICE_PROXY_ADDRESS
        if ":" in addr:
            host, port = addr.split(":")
        else:
            host, port = addr, "1081"
        logger.info(f"  🌐 Configuring global proxy: {host}:{port}")
        self._adb("shell", "settings", "put", "global", "http_proxy", f"{host}:{port}",
                   check=False, timeout=10)
        self._adb("shell", "settings", "put", "global", "global_http_proxy_host", host,
                   check=False, timeout=10)
        self._adb("shell", "settings", "put", "global", "global_http_proxy_port", port,
                   check=False, timeout=10)
        self._adb("shell", "settings", "put", "global", "net.dns1", "8.8.8.8",
                   check=False, timeout=10)
        self._adb("shell", "settings", "put", "global", "net.dns2", "1.1.1.1",
                   check=False, timeout=10)
        logger.info(f"  ✅ Proxy applied (Host: {host}, Port: {port})")
        logger.info(f"  🔍 DNS configured: 8.8.8.8, 1.1.1.1")

    def verify_network_connectivity(self, proxy_address=None):
        addr = proxy_address or DEVICE_PROXY_ADDRESS
        logger.info(f"  📡 Testing proxy connectivity through {addr}...")
        result = self._adb("shell", "curl", "-x", f"http://{addr}", "-s", "-I", "http://google.com", timeout=15)
        if "HTTP/" in (result.stdout or "") or "301" in (result.stdout or ""):
            logger.info("  ✅ Proxy connectivity verified")
            return True
        else:
            logger.warning("  ⚠️  Proxy connectivity test inconclusive (curl failed/timed out).")
            return True

    def seed_gallery(self):
        local = PROJECT_BIN / "dummy_photo.JPG"
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
        logger.info(f"  🔌 Connecting Appium → {url}...")
        opts = UiAutomator2Options()
        opts.platform_name          = "Android"
        opts.device_name            = f"localhost:{self.adb_port}"
        opts.no_reset               = True
        opts.full_reset             = False
        opts.auto_grant_permissions = True
        opts.app_package            = INSTAGRAM_PACKAGE
        opts.app_activity           = "com.instagram.mainactivity.LauncherActivity"
        opts.app_wait_activity      = "com.instagram.*"
        opts.new_command_timeout    = 300
        opts.uiautomator2_server_launch_timeout = 60_000   
        opts.uiautomator2_server_install_timeout = 60_000  
        opts.adb_exec_timeout       = 60_000             
        try:
            driver = webdriver.Remote(url, options=opts)
        except Exception as e:
            raise RuntimeError(f"Appium session creation failed: {e}") from e
        logger.info("  ✅ Appium connected")
        return driver

    def click_text(self, driver, text, exact=False, timeout=UI_ELEMENT_TIMEOUT):
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        if exact:
            xpath = f'//*[@text="{text}"]'
        else:
            xpath = f'//*[contains(translate(@text, "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "{text.lower()}")]'
        try:
            el = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((By.XPATH, xpath)))
            el.click()
            return True
        except Exception as e:
            raise e

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

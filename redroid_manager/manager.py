import subprocess
import concurrent.futures
import argparse
import time
import random

REDROID_IMAGE = "redroid/redroid:11.0.0-latest"
BASE_ADB_PORT = 5567
FPS = 60

def run_command(cmd, shell=False, timeout=None):
    return subprocess.run(cmd, shell=shell, capture_output=True, text=True, timeout=timeout)

def _random_serial(length=12):
    return "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", k=length))

def _random_hex(length=16):
    return "".join(random.choices("0123456789abcdef", k=length))

def _random_mac():
    first_byte = (random.randint(0, 255) & 0xFE) | 0x02
    rest = [random.randint(0, 255) for _ in range(5)]
    return ":".join(f"{b:02x}" for b in [first_byte] + rest)

def list_containers():
    print("\n\n")
    proc = run_command(["docker", "ps", "-a", "--filter", "name=redroid_instance_", "--format", "{{.Names}} ({{.Status}})"])
    if proc.stdout:
        print(proc.stdout.strip())
    else:
        print("No containers found.")
    print("\n\n")

def connect_and_open_scrcpy(port, name):
    addr = f"localhost:{port}"
    print(f"[*] {name}: Waiting for boot and connecting to ADB at {addr}...")
    
    # Wait for ADB connection to succeed
    deadline = time.time() + 60
    connected = False
    run_command(["adb", "disconnect", addr], timeout=5)
    
    while time.time() < deadline:
        try:
            run_command(["adb", "connect", addr], timeout=10)
        except subprocess.TimeoutExpired:
            pass
        # Check if boot completed
        proc = run_command(["adb", "-s", addr, "shell", "getprop", "sys.boot_completed"], timeout=5)
        if proc.stdout and proc.stdout.strip() == "1":
            print(f"[+] {name}: Boot completed.")
            connected = True
            break
        time.sleep(3)
        
    if not connected:
        print(f"[!] {name}: Failed to boot completely or connect to ADB on {addr}.")
        return

    print(f"[*] {name}: Opening scrcpy...")
    # Run scrcpy in the background
    subprocess.Popen([
        "scrcpy", "-s", addr,
        "--window-title", f"{name} (Port {port})"
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def start_container(instance_id):
    name = f"redroid_instance_{instance_id}"
    port = BASE_ADB_PORT + (instance_id - 1)
    
    # Check if container exists
    check = run_command(["docker", "ps", "-a", "--filter", f"name={name}", "--format", "{{.Names}}"])
    if name in check.stdout:
        # Check if it's already running
        running = run_command(["docker", "ps", "--filter", f"name={name}", "--format", "{{.Names}}"])
        if name in running.stdout:
            print(f"[*] {name} is already running on port {port}")
            connect_and_open_scrcpy(port, name)
            return
        else:
            print(f"[*] Starting existing container: {name} on port {port}")
            run_command(["docker", "start", name])
            connect_and_open_scrcpy(port, name)
            return

    print(f"[*] Creating and starting new container: {name} on port {port}")
    
    # Generate isolated random identity parameters
    serial = _random_serial(12)
    android_id = _random_hex(16)
    mac = _random_mac()
    
    cmd = [
        "docker", "run", "-d", "--privileged",
        "--name", name,
        "--hostname", f"d-rc-{instance_id}",
        "-v", "/dev/binderfs:/dev/binderfs",
        "--tmpfs", "/data:rw,exec,suid",
        f"--mac-address={mac}",
        "-p", f"{port}:5555",
        REDROID_IMAGE,
        f"androidboot.redroid_fps={FPS}",
        "androidboot.use_memfd=1",
        "debug.sf.nobootanimation=1",
        f"androidboot.serialno={serial}",
        f"ro.serialno={serial}",
        f"ro.boot.serialno={serial}",
        "ro.product.model=Redroid_Isolated",
    ]
    proc = run_command(cmd)
    
    if proc.returncode != 0:
        print(f"[!] Error starting {name}: {proc.stderr}")
    else:
        print(f"[+] {name} started successfully on port {port}")
        # Connect and set internal settings
        connect_and_open_scrcpy(port, name)
        # Apply secure android_id right after scrcpy connects to ensure isolation
        run_command(["adb", "-s", f"localhost:{port}", "shell", "settings", "put", "secure", "android_id", android_id])


def stop_container(instance_id):
    name = f"redroid_instance_{instance_id}"
    port = BASE_ADB_PORT + (instance_id - 1)
    addr = f"localhost:{port}"
    print(f"[*] Stopping {name}...")
    run_command(["adb", "disconnect", addr], timeout=5)
    run_command(["docker", "stop", name], timeout=15)
    print(f"[+] Stopped {name}.")

def delete_container(instance_id):
    name = f"redroid_instance_{instance_id}"
    port = BASE_ADB_PORT + (instance_id - 1)
    addr = f"localhost:{port}"
    print(f"[*] Deleting {name}...")
    run_command(["adb", "disconnect", addr], timeout=5)
    run_command(["docker", "rm", "-f", name], timeout=15)
    print(f"[+] Deleted {name}.")

def get_all_instance_ids():
    proc = run_command(["docker", "ps", "-a", "--filter", "name=redroid_instance_", "--format", "{{.Names}}"])
    ids = []
    if proc.stdout:
        for line in proc.stdout.strip().splitlines():
            if line.startswith("redroid_instance_"):
                try:
                    ids.append(int(line.split("_")[-1]))
                except ValueError:
                    pass
    return ids

def main():
    parser = argparse.ArgumentParser(description="Redroid Instance Manager")
    parser.add_argument("count", type=int, nargs='?', help="Number of windows (containers) to open")
    parser.add_argument("--list", action="store_true", help="List existing containers")
    parser.add_argument("--start", type=int, help="Start a specific existing container ID")
    parser.add_argument("--stop", type=int, help="Stop a specific existing container ID")
    parser.add_argument("--delete", type=int, help="Delete a specific existing container ID")
    parser.add_argument("--start-all", action="store_true", help="Start all existing containers")
    parser.add_argument("--stop-all", action="store_true", help="Stop all existing containers")
    parser.add_argument("--delete-all", action="store_true", help="Delete all existing containers")
    parser.add_argument("--open-all", action="store_true", help="Open SCRCPY GUI for all existing containers")
    
    args = parser.parse_args()

    if args.list:
        list_containers()
        return

    if args.stop_all:
        ids = get_all_instance_ids()
        for i in ids: stop_container(i)
        return

    if args.delete_all:
        ids = get_all_instance_ids()
        for i in ids: delete_container(i)
        return

    if args.start:
        start_container(args.start)
        return

    if args.start_all:
        ids = get_all_instance_ids()
        if not ids:
            print("[*] No existing containers to start.")
            return
        print(f"[*] Starting {len(ids)} existing Redroid instances...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(ids)) as executor:
            futures = [executor.submit(start_container, i) for i in ids]
            concurrent.futures.wait(futures)
        print("\n[*] All instances processed.")
        return

    if args.open_all:
        ids = get_all_instance_ids()
        print(f"[*] Opening SCRCPY for {len(ids)} instances...")
        for i in ids:
            port = BASE_ADB_PORT + (i - 1)
            name = f"redroid_instance_{i}"
            connect_and_open_scrcpy(port, name)
        return

    if args.stop:
        stop_container(args.stop)
        return

    if args.delete:
        delete_container(args.delete)
        return

    if args.count is None:
        parser.print_help()
        return

    print(f"[*] Starting {args.count} isolated Redroid instances...")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.count) as executor:
        futures = [executor.submit(start_container, i) for i in range(1, args.count + 1)]
        concurrent.futures.wait(futures)

    print("\n[*] All requested instances processed.")

if __name__ == "__main__":
    main()

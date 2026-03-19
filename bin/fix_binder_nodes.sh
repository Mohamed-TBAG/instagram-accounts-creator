#!/bin/bash
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
    echo "This script must be run as root." >&2
    exit 1
fi

echo "Unmounting binderfs..."
# Force unmount if busy
umount -l /dev/binderfs || true

echo "Unloading binder_linux module..."
# Might fail if in use, force?
rmmod binder_linux || echo "Module in use or not loaded"

echo "Reloading binder_linux module with devices parameter..."
# Clean load
modprobe binder_linux devices="binder,hwbinder,vndbinder"

echo "Remounting binderfs..."
if [ ! -d "/dev/binderfs" ]; then
    mkdir -p /dev/binderfs
fi
mount -t binder binder /dev/binderfs

echo "Checking nodes..."
ls -l /dev/binderfs

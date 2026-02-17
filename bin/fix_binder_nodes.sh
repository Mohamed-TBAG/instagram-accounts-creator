#!/bin/bash
set -e
echo "Unmounting binderfs..."
# Force unmount if busy
sudo umount -l /dev/binderfs || true

echo "Unloading binder_linux module..."
# Might fail if in use, force?
sudo rmmod binder_linux || echo "Module in use or not loaded"

echo "Reloading binder_linux module with devices parameter..."
# Clean load
sudo modprobe binder_linux devices="binder,hwbinder,vndbinder"

echo "Remounting binderfs..."
if [ ! -d "/dev/binderfs" ]; then
    sudo mkdir -p /dev/binderfs
fi
sudo mount -t binder binder /dev/binderfs

echo "Checking nodes..."
ls -l /dev/binderfs

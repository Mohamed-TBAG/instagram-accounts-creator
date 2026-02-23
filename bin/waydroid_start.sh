#!/bin/bash
# bin/waydroid_start.sh

# Stop any running session first
waydroid session stop
pkill -f weston

# Wait for cleanup
sleep 2

# Start Weston in background (headless or background window)
# We use weston-socket name 'wayland-1' explicitly
export WAYLAND_DISPLAY=wayland-1
export XDG_RUNTIME_DIR=/run/user/$(id -u)

# Ensure runtime dir exists
mkdir -p $XDG_RUNTIME_DIR
chmod 0700 $XDG_RUNTIME_DIR

# Start Weston on a free display
echo "Starting Weston..."
weston --socket=$WAYLAND_DISPLAY --backend=headless-backend.so &
# Alternatively use x11-backend if headless fails, but headless is better for servers/bots
# weston --socket=$WAYLAND_DISPLAY &

WESTON_PID=$!
echo "Weston PID: $WESTON_PID"

# Wait for Weston socket
TIMEOUT=10
while [ ! -S "$XDG_RUNTIME_DIR/$WAYLAND_DISPLAY" ]; do
    if [ $TIMEOUT -le 0 ]; then
        echo "Error: Weston failed to start socket $WAYLAND_DISPLAY"
        exit 1
    fi
    sleep 1
    ((TIMEOUT--))
done

echo "Weston is ready at $WAYLAND_DISPLAY"

# Start Waydroid Session
echo "Starting Waydroid Session..."
waydroid session start &

# Wait for session to initialize
sleep 5

# Show UI (headless mode for mass creation doesn't need visible UI, but Android often pauses if no UI is attached)
# We attach it to the headless Weston
waydroid show-full-ui &

echo "Waydroid started."

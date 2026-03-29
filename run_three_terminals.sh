#!/usr/bin/env bash
set -eu

# Launcher that opens one terminal window with three tabs running:
# 1) python3 main.py (in repo root)
# 2) appium
# 3) scrcpy
# Each tab remains open after its command exits so failures don't close others.

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Commands (use double quotes so we can interpolate ROOT_DIR)
CMD1="cd \"$ROOT_DIR\" && python3 main.py"
CMD2="appium"
CMD3="scrcpy"

run_in_tabs() {
  # gnome-terminal supports multiple --tab
  if command -v gnome-terminal >/dev/null 2>&1; then
    gnome-terminal \
      --tab -- bash -lc "$CMD1; echo; echo \"-- exited with $? --\"; exec bash" \
      --tab -- bash -lc "$CMD2; echo; echo \"-- exited with $? --\"; exec bash" \
      --tab -- bash -lc "$CMD3; echo; echo \"-- exited with $? --\"; exec bash" &
    return 0
  fi

  # konsole: --new-tab -e
  if command -v konsole >/dev/null 2>&1; then
    konsole --new-tab -e bash -lc "$CMD1; echo; echo \"-- exited with $? --\"; exec bash" \
           --new-tab -e bash -lc "$CMD2; echo; echo \"-- exited with $? --\"; exec bash" \
           --new-tab -e bash -lc "$CMD3; echo; echo \"-- exited with $? --\"; exec bash" &
    return 0
  fi

  # xfce4-terminal and mate-terminal use --tab --command
  if command -v xfce4-terminal >/dev/null 2>&1; then
    xfce4-terminal \
      --tab --command="bash -lc '$CMD1; echo; echo \"-- exited with \$? --\"; exec bash'" \
      --tab --command="bash -lc '$CMD2; echo; echo \"-- exited with \$? --\"; exec bash'" \
      --tab --command="bash -lc '$CMD3; echo; echo \"-- exited with \$? --\"; exec bash'" &
    return 0
  fi
  if command -v mate-terminal >/dev/null 2>&1; then
    mate-terminal \
      --tab --command="bash -lc '$CMD1; echo; echo \"-- exited with \$? --\"; exec bash'" \
      --tab --command="bash -lc '$CMD2; echo; echo \"-- exited with \$? --\"; exec bash'" \
      --tab --command="bash -lc '$CMD3; echo; echo \"-- exited with \$? --\"; exec bash'" &
    return 0
  fi

  # terminator can split windows but CLI for tabs is less standard; try terminator with three commands in tabs
  if command -v terminator >/dev/null 2>&1; then
    terminator -T "Launcher" -e "bash -lc '$CMD1; echo; echo \"-- exited with \$? --\"; exec bash'" &
    sleep 0.2
    terminator -a -e "bash -lc '$CMD2; echo; echo \"-- exited with \$? --\"; exec bash'" &
    sleep 0.2
    terminator -a -e "bash -lc '$CMD3; echo; echo \"-- exited with \$? --\"; exec bash'" &
    return 0
  fi

  return 1
}

run_in_window_fallback() {
  # Fallback: open separate windows (for terminals without tab support)
  if command -v xterm >/dev/null 2>&1; then
    xterm -hold -e bash -lc "$CMD1; echo; echo \"-- exited with $? --\"; exec bash" &
    xterm -hold -e bash -lc "$CMD2; echo; echo \"-- exited with $? --\"; exec bash" &
    xterm -hold -e bash -lc "$CMD3; echo; echo \"-- exited with $? --\"; exec bash" &
    return
  fi
  if command -v x-terminal-emulator >/dev/null 2>&1; then
    x-terminal-emulator -e bash -lc "$CMD1; echo; echo \"-- exited with $? --\"; exec bash" &
    x-terminal-emulator -e bash -lc "$CMD2; echo; echo \"-- exited with $? --\"; exec bash" &
    x-terminal-emulator -e bash -lc "$CMD3; echo; echo \"-- exited with $? --\"; exec bash" &
    return
  fi

  # Final fallback: background shells
  bash -lc "$CMD1; echo; echo \"-- exited with $? --\"" &
  bash -lc "$CMD2; echo; echo \"-- exited with $? --\"" &
  bash -lc "$CMD3; echo; echo \"-- exited with $? --\"" &
}

if run_in_tabs; then
  echo "Opened a single terminal window with three tabs."
else
  echo "No tab-capable terminal found; opening separate windows/fallback shells."
  run_in_window_fallback
fi


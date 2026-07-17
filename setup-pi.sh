#!/usr/bin/env bash
# One-shot bring-up for the OTC2310K04-PIKA HAT on a Raspberry Pi 5.
#
# Idempotent: safe to re-run. Detects whether each step has already been
# done and skips if so. Reboots only if SPI config changed.
#
# Run as the unprivileged user (it will sudo where needed). Verified on
# Debian 13 Trixie / Raspberry Pi OS Bookworm with a Pi 5.

set -euo pipefail

CONFIG=/boot/firmware/config.txt
NEEDS_REBOOT=0

red()    { printf '\033[1;31m%s\033[0m\n' "$*"; }
green()  { printf '\033[1;32m%s\033[0m\n' "$*"; }
yellow() { printf '\033[1;33m%s\033[0m\n' "$*"; }
log()    { printf '  %s\n' "$*"; }

if [[ ! -f "$CONFIG" ]]; then
    red "ERROR: $CONFIG not found. Are you on Raspberry Pi OS?"
    exit 1
fi

# ----------------------------------------------------------------------
green "[1/4] Enabling SPI in $CONFIG"
# ----------------------------------------------------------------------

if grep -qE '^[[:space:]]*dtparam=spi=on' "$CONFIG"; then
    log "dtparam=spi=on already present — skipping"
else
    log "adding dtparam=spi=on (raspi-config)"
    sudo raspi-config nonint do_spi 0
    NEEDS_REBOOT=1
fi

if grep -qE '^[[:space:]]*dtoverlay=spi0-0cs' "$CONFIG"; then
    log "dtoverlay=spi0-0cs already present — skipping"
else
    log "appending dtoverlay=spi0-0cs (frees GPIO 8 / CE0 for manual control)"
    echo 'dtoverlay=spi0-0cs' | sudo tee -a "$CONFIG" >/dev/null
    NEEDS_REBOOT=1
fi

# ----------------------------------------------------------------------
green "[2/4] Verifying user is in spi + gpio groups"
# ----------------------------------------------------------------------

USER_NAME="$(whoami)"
for grp in spi gpio; do
    if id -nG "$USER_NAME" | grep -qw "$grp"; then
        log "user $USER_NAME already in '$grp' group"
    else
        log "adding user $USER_NAME to '$grp' group"
        sudo usermod -aG "$grp" "$USER_NAME"
        yellow "  -> log out and back in (or reboot) for group change to apply"
        NEEDS_REBOOT=1
    fi
done

# ----------------------------------------------------------------------
green "[3/4] Installing system Python deps (apt)"
# ----------------------------------------------------------------------

# Trixie ships RPi.GPIO 0.7.2 system-wide that works on Pi 5; we use it via
# --system-site-packages venv. spidev is the SPI userspace lib.
sudo apt-get update -qq
sudo apt-get install -y python3-pip python3-venv python3-spidev python3-rpi.gpio git

# ----------------------------------------------------------------------
green "[4/4] Setting up Python venv at python/venv"
# ----------------------------------------------------------------------

REPO_PYTHON_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_PYTHON_DIR"

if [[ -d venv ]]; then
    log "venv already exists at $REPO_PYTHON_DIR/venv — leaving in place"
else
    log "creating venv with --system-site-packages (inherits RPi.GPIO + spidev)"
    python3 -m venv --system-site-packages venv
fi

# Install pure-Python deps from requirements.txt
log "installing pip requirements"
./venv/bin/pip install --quiet --upgrade pip
./venv/bin/pip install --quiet -r requirements.txt || {
    yellow "pip install partially failed — continuing (system pkgs likely cover it)"
}

# ----------------------------------------------------------------------
echo
green "Setup complete."
echo
log "verify with:"
log "  ls /dev/spidev0.0           # should exist after reboot if SPI was just enabled"
log "  pinctrl get 8,9,10,11       # GPIO 9/10/11 should show 'a0' (SPI0_*)"
log "                               # GPIO 8 should show 'no' (free for driver)"
log "  source venv/bin/activate"
log "  python3 examples/03_load_ahf.py ../Documentation/pika/pikapy-main/4osc.ahf"
echo
if [[ "$NEEDS_REBOOT" == "1" ]]; then
    yellow "REBOOT REQUIRED for SPI config / group changes to take effect."
    yellow "Run:  sudo reboot"
else
    green "No reboot needed. You can run the first-light test immediately."
fi

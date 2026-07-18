#!/usr/bin/env bash
# WADForge Linux build script
# Run this on a Linux machine to produce the binary.
# Usage: chmod +x build_linux.sh && ./build_linux.sh

set -e

echo "=== WADForge Linux Build ==="

# Ensure python3 and tkinter are available
if ! command -v python3 &>/dev/null; then
    echo "Installing python3..."
    if command -v apt-get &>/dev/null; then
        sudo apt-get update && sudo apt-get install -y python3 python3-pip python3-tk
    elif command -v dnf &>/dev/null; then
        sudo dnf install -y python3 python3-pip python3-tkinter
    elif command -v pacman &>/dev/null; then
        sudo pacman -S --noconfirm python python-pip tk
    else
        echo "ERROR: Unsupported distro. Install python3, pip, and tkinter manually."
        exit 1
    fi
fi

echo "Python: $(python3 --version)"

# Install dependencies
python3 -m pip install --upgrade pip
python3 -m pip install Pillow pyinstaller

# Build
echo "Building WADForge for Linux..."
rm -rf build_temp build_output
mkdir -p build_output

python3 -m PyInstaller \
    --onefile \
    --name "WADForge" \
    --distpath "build_output" \
    --workpath "build_temp" \
    --specpath "build_temp" \
    main.py

# Cleanup
rm -rf build_temp

echo ""
echo "=== Done ==="
echo "Binary: build_output/WADForge"
ls -lh build_output/WADForge

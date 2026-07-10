#!/bin/bash
# ==============================================================================
# 🦅 Mohawk Inference Engine Full-Stack Shell Wrapper
# ==============================================================================

# Set color formatting
CRIMSON="\033[38;5;196m"
GOLD="\033[38;5;220m"
CYAN="\033[38;5;51m"
EMERALD="\033[38;5;46m"
WHITE="\033[37m"
RESET="\033[0m"
BOLD="\033[1m"

echo -e "${CYAN}================================================================${RESET}"
echo -e "${BOLD}${WHITE}🦅 MOHAWK INFERENCE ENGINE - LAUNCHER BOOTSTRAPPER${RESET}"
echo -e "${CYAN}================================================================${RESET}"

# Verify Python 3
if ! command -v python3 &> /dev/null; then
    echo -e "${CRIMSON}[ERROR] Python 3 was not found on your system path.${RESET}"
    echo -e "${CRIMSON}Please install Python 3.10+ and try again.${RESET}"
    return 1 2>/dev/null || exit 1
fi

# Determine if we should set up virtualenv
if [ ! -d "venv" ]; then
    echo -e "${GOLD}[INFO] No virtual environment found. Creating local venv...${RESET}"
    python3 -m venv venv
    echo -e "${EMERALD}[✓] Virtual environment created successfully.${RESET}"
fi

# Activate virtualenv
echo -e "${WHITE}Activating virtual environment...${RESET}"
source venv/bin/activate || . venv/bin/activate

# Check if packages are already installed to make boot sub-second
echo -e "${WHITE}Verifying library dependencies...${RESET}"
if ! python3 -c "import fastapi, uvicorn, requests, cryptography, zeroconf, psutil" &> /dev/null; then
    echo -e "${GOLD}[INFO] Missing packages detected. Installing required dependencies from requirements.txt...${RESET}"
    pip install --upgrade pip
    pip install -r requirements.txt
    echo -e "${EMERALD}[✓] Dependencies successfully synchronized.${RESET}"
else
    echo -e "${EMERALD}[✓] All library dependencies are fully up to date.${RESET}"
fi

echo -e "${WHITE}Launching Mohawk Launcher Engine...${RESET}"
echo -e "${CYAN}----------------------------------------------------------------${RESET}"
sleep 0.5

# Forward all arguments to launch.py
python3 launch.py "$@"

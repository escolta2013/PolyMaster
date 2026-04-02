#!/bin/bash
# PolyMaster EC2 Setup Script
# Run this ONCE on a fresh Ubuntu 22.04 instance
# Usage: bash setup_ec2.sh

set -e
echo "===================================="
echo " PolyMaster EC2 Setup"
echo "===================================="

# 1. System update
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3.11 python3.11-venv python3-pip git

# 2. Verify Python version
python3.11 --version

# 3. Clone repo (replace with your GitHub URL if private)
REPO_URL="https://github.com/escolta2013/PolyMaster.git"
INSTALL_DIR="/home/ubuntu/PolyMaster"

if [ -d "$INSTALL_DIR" ]; then
  echo "Repo already cloned. Pulling latest..."
  cd "$INSTALL_DIR" && git pull
else
  git clone "$REPO_URL" "$INSTALL_DIR"
fi

# 4. Create Python virtual environment
cd "$INSTALL_DIR/backend"
python3.11 -m venv .venv
source .venv/bin/activate

# 5. Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "===================================="
echo " Dependencies installed."
echo " NEXT STEP: Create the .env file"
echo "===================================="
echo " Run: nano /home/ubuntu/PolyMaster/backend/.env"
echo ""
echo " Required variables for REAL TRADING:"
echo "   SUPABASE_URL=..."
echo "   SUPABASE_KEY=..."
echo "   OPENAI_API_KEY=..."
echo "   PK=0x...                      <- Your Polygon wallet private key"
echo "   CLOB_API_KEY=...              <- Generated from your wallet"
echo "   CLOB_SECRET=..."
echo "   CLOB_PASSPHRASE=..."
echo "   TELEGRAM_BOT_TOKEN=..."
echo "   TELEGRAM_ADMIN_CHAT_ID=..."
echo "   COPY_SIMULATION=false"
echo "   PAPER_TRADING_MODE=false"
echo "   ENABLE_AUTONOMOUS_TRADING=true"
echo "   AUTONOMOUS_CONFIDENCE_THRESHOLD=0.68"
echo "   AUTONOMOUS_MAX_SIZE=20.0"
echo "   COPY_MAX_PER_TRADE=20.0"
echo "   COPY_MAX_DAILY=100.0"
echo "   GLOBAL_STOP_LOSS_PCT=0.60"
echo "===================================="

# 6. Install systemd services
echo ""
echo "Installing systemd services..."
sudo cp "$INSTALL_DIR/deploy/polymaster-api.service" /etc/systemd/system/
sudo cp "$INSTALL_DIR/deploy/polymaster-bot.service" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable polymaster-api polymaster-bot

echo ""
echo "===================================="
echo " Services installed."
echo " After creating .env, run:"
echo "   sudo systemctl start polymaster-api"
echo "   sudo systemctl start polymaster-bot"
echo ""
echo " Check status:"
echo "   sudo systemctl status polymaster-api"
echo "   sudo systemctl status polymaster-bot"
echo ""
echo " Live logs:"
echo "   journalctl -fu polymaster-bot"
echo ""
echo " Dashboard:"
echo "   http://$(curl -s ifconfig.me):8000/dashboard"
echo "===================================="

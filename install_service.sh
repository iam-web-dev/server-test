#!/bin/bash
# ==============================================================================
# Debian 13 (Trixie) Minimal - Server Master Bot Autostart Installer
# ==============================================================================
set -e

SERVICE_NAME="server-master-bot"
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_EXEC="${APP_DIR}/.venv/bin/python"

if [ ! -f "${PYTHON_EXEC}" ]; then
    echo "⚠️ .venv/bin/python topilmadi! Tizim python3 ishlatiladi..."
    PYTHON_EXEC="$(which python3)"
fi

echo "🚀 [1/4] Server Master Bot papkasi: ${APP_DIR}"
echo "🐍 [2/4] Python interpretator: ${PYTHON_EXEC}"

# Service faylini yaratish
SERVICE_PATH="/etc/systemd/system/${SERVICE_NAME}.service"

echo "📝 [3/4] ${SERVICE_PATH} fayli yaratilmoqda..."
cat <<EOF | tee "${SERVICE_PATH}" > /dev/null
[Unit]
Description=Server SysAdmin & DevOps Master Tool Telegram Bot
After=network.target network-online.target systemd-journald.service
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=${APP_DIR}
ExecStart=${PYTHON_EXEC} main.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
Environment="PYTHONUNBUFFERED=1"
Environment="DEBIAN_FRONTEND=noninteractive"

[Install]
WantedBy=multi-user.target
EOF

echo "⚙️ [4/4] Systemd yangilanmoqda va servis yoqilmoqda..."
systemctl daemon-reload
systemctl enable "${SERVICE_NAME}.service"
systemctl restart "${SERVICE_NAME}.service"

echo ""
echo "✅ MUVAFFAQITYATLI O'RNATILDI!"
echo "Serveringiz qayta yoqilganda (reboot) bot avtomatik ishga tushadi va Telegramga xabar beradi."
echo "Holatni ko'rish: systemctl status ${SERVICE_NAME}"

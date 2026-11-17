import os
from dotenv import load_dotenv

# .env faylini yuklash
load_dotenv()

# Telegram Bot Token
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

# Admin autentifikatsiyasi uchun Login va Parol
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin").strip()
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123").strip()

# Kuzatiladigan servislar yoki jarayonlar ro'yxati (vergul bilan ajratilgan)
# Masalan: nginx,docker,postgresql,mysql,redis,ssh,bot
raw_services = os.getenv("MONITORED_SERVICES", "nginx,docker,postgresql,mysql,redis,ssh")
MONITORED_SERVICES = [s.strip() for s in raw_services.split(",") if s.strip()]

# Kuzatish oralig'i (soniyalarda, default: 15 soniya)
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "15"))

# Resurslar bo'yicha ogohlantirish (Alert) chegaralari (foizda)
CPU_THRESHOLD = float(os.getenv("CPU_THRESHOLD", "85.0"))
RAM_THRESHOLD = float(os.getenv("RAM_THRESHOLD", "90.0"))
DISK_THRESHOLD = float(os.getenv("DISK_THRESHOLD", "90.0"))

# Kuzatiladigan log fayllar (vergul bilan ajratilgan)
raw_logs = os.getenv("WATCH_LOG_FILES", "logs/server_activity.log,logs/server_errors.log")
WATCH_LOG_FILES = [f.strip() for f in raw_logs.split(",") if f.strip()]

# Kuzatiladigan log kategoriyalari (security, service, error, warning, system, action)
raw_categories = os.getenv(
    "WATCH_LOG_CATEGORIES", "security,service,error,warning,system,action"
)
WATCH_LOG_CATEGORIES = set(c.strip().lower() for c in raw_categories.split(",") if c.strip())

# Maxsus foydalanuvchi kalit so'zlari (qo'shimcha kuzatilishi kerak bo'lgan so'zlar)
raw_custom_kw = os.getenv("CUSTOM_LOG_KEYWORDS", "")
CUSTOM_LOG_KEYWORDS = [k.strip().lower() for k in raw_custom_kw.split(",") if k.strip()]

# Systemd journalctl orqali butun server hodisalarini kuzatish (True / False)
ENABLE_JOURNALCTL = os.getenv("ENABLE_JOURNALCTL", "true").strip().lower() in ("true", "1", "yes")

# Bir xil loglar takrorlanganda spam bo'lmasligi uchun cheklov (soniya)
LOG_THROTTLE_SECONDS = int(os.getenv("LOG_THROTTLE_SECONDS", "60"))

# Vaqt mintaqasi
TIMEZONE = os.getenv("TIMEZONE", "Asia/Tashkent")

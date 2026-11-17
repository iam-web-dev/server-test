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
# Masalan: nginx,docker,postgresql,mysql,redis,ssh,tg-manager,server-master-bot
raw_services = os.getenv("MONITORED_SERVICES", "tg-manager,server-master-bot,nginx,docker,postgresql,mysql,redis,ssh")
MONITORED_SERVICES = [s.strip() for s in raw_services.split(",") if s.strip()]

# Kuzatish oralig'i (soniyalarda, default: 20 soniya)
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "20"))

# Resurslar bo'yicha ogohlantirish (Alert) chegaralari (foizda)
CPU_THRESHOLD = float(os.getenv("CPU_THRESHOLD", "90.0"))
RAM_THRESHOLD = float(os.getenv("RAM_THRESHOLD", "92.0"))
DISK_THRESHOLD = float(os.getenv("DISK_THRESHOLD", "92.0"))

# Kuzatiladigan log fayllar (vergul bilan ajratilgan)
raw_logs = os.getenv("WATCH_LOG_FILES", "logs/server_activity.log,logs/server_errors.log")
WATCH_LOG_FILES = [f.strip() for f in raw_logs.split(",") if f.strip()]

# Kuzatiladigan log kategoriyalari (security, system, error)
# Odatiy kichik warninglar va info amallar spam bo'lmasligi uchun standart holatda o'chirilgan
raw_categories = os.getenv(
    "WATCH_LOG_CATEGORIES", "security,system,error"
)
WATCH_LOG_CATEGORIES = set(c.strip().lower() for c in raw_categories.split(",") if c.strip())

# Minimal alert jiddiylik darajasi: CRITICAL, HIGH, WARNING, INFO
# Faqat shu va undan yuqori darajadagi xabarlar adminga push-bildirishnoma sifatida boradi
MIN_ALERT_SEVERITY = os.getenv("MIN_ALERT_SEVERITY", "HIGH").strip().upper()

# Mayda warning va notificationlarni push alertdan o'chirish (True / False)
SILENCE_MINOR_WARNINGS = os.getenv("SILENCE_MINOR_WARNINGS", "true").strip().lower() in ("true", "1", "yes")

# Maxsus foydalanuvchi kalit so'zlari (qo'shimcha kuzatilishi kerak bo'lgan so'zlar)
raw_custom_kw = os.getenv("CUSTOM_LOG_KEYWORDS", "")
CUSTOM_LOG_KEYWORDS = [k.strip().lower() for k in raw_custom_kw.split(",") if k.strip()]

# Systemd journalctl orqali butun server hodisalarini kuzatish (True / False)
ENABLE_JOURNALCTL = os.getenv("ENABLE_JOURNALCTL", "true").strip().lower() in ("true", "1", "yes")

# Bir xil loglar takrorlanganda spam bo'lmasligi uchun cheklov (soniya)
LOG_THROTTLE_SECONDS = int(os.getenv("LOG_THROTTLE_SECONDS", "180"))

# Loyihalar joylashgan asosiy papka
PROJECTS_DIR = os.getenv("PROJECTS_DIR", "/home/server/Projects").strip()

# E'tiborga olinmaydigan (ignorable / spam) log patternlari ro'yxati
IGNORE_LOG_PATTERNS = [
    # Tizim va fondagi odatiy hodisalar
    "session opened for user",
    "session closed for user",
    "pam_unix(cron:session)",
    "pam_unix(systemd-user:session)",
    "starting systemd-user-runtime-dir",
    "cleanup of temporary directories",
    "apt-daily",
    "apt-daily-upgrade",
    "systemd-tmpfiles-clean",
    "snapd",
    "polkit",
    "dbus-daemon",
    # Python & kutubxona ogohlantirishlari (warnings)
    "deprecationwarning",
    "userwarning",
    "futurewarning",
    "syntaxwarning",
    "urllib3",
    "greenlet",
    "greenlet_spawn",
    # Telegram bot vaqtinchalik tarmoq retrylari
    "telegramretryafter",
    "telegramnetworkerror",
    "clientoserror: [errno 104]",
    "sleep for 1.000000 seconds and try again",
    "connection established (tryings =",
    "failed to fetch updates",
    "conflict: terminated by other getupdates",
    "request timeout error",
    # Kichik xatolar / shovqinlar
    "temporary failure in name resolution",
    "no matching distribution found",
    "getpeername: transport endpoint is not connected",
    "could not find a version that satisfies",
]

# Vaqt mintaqasi
TIMEZONE = os.getenv("TIMEZONE", "Asia/Tashkent")

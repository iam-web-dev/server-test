import json
import logging
import os
from datetime import datetime
from zoneinfo import ZoneInfo
import config

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
ADMINS_FILE = os.path.join(DATA_DIR, "admins.json")


def _ensure_data_dir():
    """Ma'lumotlar papkasi va faylini mavjudligini ta'minlash."""
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(ADMINS_FILE):
        with open(ADMINS_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f, indent=2, ensure_ascii=False)


def _load_admins() -> dict:
    _ensure_data_dir()
    try:
        with open(ADMINS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Admins faylini o'qishda xatolik: {e}")
        return {}


def _save_admins(data: dict):
    _ensure_data_dir()
    try:
        with open(ADMINS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Admins faylini saqlashda xatolik: {e}")


def is_authenticated(user_id: int) -> bool:
    """Foydalanuvchi tizimga admin sifatida kirganmi yoki yo'qligini tekshirish."""
    admins = _load_admins()
    return str(user_id) in admins


def authenticate(user_id: int, username: str, password: str, tg_username: str = "", full_name: str = "") -> bool:
    """
    Kiritilgan login va parolni tekshirish hamda foydalanuvchini admin sifatida ro'yxatga olish.
    """
    if username.strip() == config.ADMIN_USERNAME and password.strip() == config.ADMIN_PASSWORD:
        admins = _load_admins()
        now_str = datetime.now(ZoneInfo(config.TIMEZONE)).strftime("%Y-%m-%d %H:%M:%S")
        admins[str(user_id)] = {
            "user_id": user_id,
            "username": username,
            "tg_username": tg_username or "",
            "full_name": full_name or "",
            "authenticated_at": now_str,
        }
        _save_admins(admins)
        logger.info(f"Foydalanuvchi {user_id} ({full_name}) admin sifatida muvaffaqiyatli tizimga kirdi.")
        return True
    return False


def logout(user_id: int) -> bool:
    """Foydalanuvchini tizimdan chiqarish."""
    admins = _load_admins()
    uid_str = str(user_id)
    if uid_str in admins:
        del admins[uid_str]
        _save_admins(admins)
        logger.info(f"Foydalanuvchi {user_id} tizimdan chiqdi.")
        return True
    return False


def get_authenticated_user_ids() -> list[int]:
    """Barcha faol adminlarning Telegram chat ID larini olish."""
    admins = _load_admins()
    return [int(uid) for uid in admins.keys()]


def get_all_admins() -> list[dict]:
    """Barcha adminlar ro'yxatini olish."""
    admins = _load_admins()
    return list(admins.values())

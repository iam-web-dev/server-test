import json
import logging
import os
import platform
import subprocess
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

import auth_manager
import config
import server_monitor

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
STATE_FILE = os.path.join(DATA_DIR, "system_state.json")


def _ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def get_current_boot_id() -> str:
    """Linux kernel random boot ID sini olish."""
    boot_id_file = "/proc/sys/kernel/random/boot_id"
    if os.path.exists(boot_id_file):
        try:
            with open(boot_id_file, "r") as f:
                return f.read().strip()
        except Exception:
            pass

    # Fallback uptime orqali
    try:
        with open("/proc/uptime", "r") as f:
            up = f.readline().split()[0]
            return f"uptime_{up}"
    except Exception:
        return "default_boot_id"


def get_network_ips() -> dict[str, str]:
    """Serverning lokal va ommaviy (public) IP manzillarini olish."""
    local_ip = "127.0.0.1"
    try:
        res = subprocess.run(["hostname", "-I"], capture_output=True, text=True, timeout=2)
        if res.returncode == 0 and res.stdout.strip():
            local_ip = res.stdout.strip().split()[0]
    except Exception:
        pass

    public_ip = "Noma'lum"
    for url in ["https://api.ipify.org", "https://ifconfig.me/ip"]:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "curl/7.68.0"})
            with urllib.request.urlopen(req, timeout=2) as resp:
                public_ip = resp.read().decode("utf-8").strip()
                if public_ip:
                    break
        except Exception:
            continue

    return {"local": local_ip, "public": public_ip}


def _load_state() -> dict:
    _ensure_data_dir()
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"System state faylini o'qishda xatolik: {e}")
    return {}


def _save_state(state: dict):
    _ensure_data_dir()
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"System state faylini saqlashda xatolik: {e}")


def is_new_boot() -> bool:
    """Server qayta yuklanganmi yoki yangi yoqilganmi tekshirish."""
    current_boot_id = get_current_boot_id()
    state = _load_state()
    last_boot_id = state.get("last_boot_id")
    return current_boot_id != last_boot_id


def mark_boot_notified(boot_id: str):
    """Xabar yuborilgan boot ID sini saqlash."""
    now_str = datetime.now(ZoneInfo(config.TIMEZONE)).strftime("%Y-%m-%d %H:%M:%S")
    state = _load_state()
    state["last_boot_id"] = boot_id
    state["last_boot_alert_at"] = now_str
    _save_state(state)


def format_boot_alert() -> str:
    """Server yonganda yuboriladigan alert xabari."""
    sys_info = server_monitor.get_system_info()
    uptime = server_monitor.get_uptime()
    ips = get_network_ips()
    now_str = datetime.now(ZoneInfo(config.TIMEZONE)).strftime("%H:%M:%S (%d.%m.%Y)")
    mem = server_monitor.get_memory_usage()
    disk = server_monitor.get_disk_usage()

    text = (
        f"🟢 <b>SERVER ISHGA TUSHDI / QAYTA YUKLANDI!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🖥 <b>Xost:</b> <code>{sys_info['hostname']}</code>\n"
        f"🐧 <b>OS:</b> <code>{sys_info['os']}</code> ({sys_info['arch']})\n"
        f"⚙️ <b>Yadro:</b> <code>{sys_info['kernel']}</code>\n"
        f"⏱ <b>Uptime:</b> <code>{uptime}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🌐 <b>IP Manzillar:</b>\n"
        f"   └ Public IP: <code>{ips['public']}</code>\n"
        f"   └ Local IP:  <code>{ips['local']}</code>\n\n"
        f"📊 <b>Boshlang'ich holat:</b>\n"
        f"   └ RAM: <code>{mem['used_mb']} MB / {mem['total_mb']} MB ({mem['percent']}%)</code>\n"
        f"   └ Disk: <code>{disk['used_gb']} GB / {disk['total_gb']} GB ({disk['percent']}%)</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🕒 <b>Vaqt:</b> <code>{now_str}</code>\n"
        f"✅ <i>Server Master Bot to'liq faol va monitoring rejimida!</i>"
    )
    return text


async def check_boot_and_notify(bot) -> bool:
    """
    Agar yangi boot aniqlansa, barcha adminlarga alert yuborish.
    """
    if not is_new_boot():
        logger.info("Serverda yangi boot aniqlanmadi.")
        return False

    current_boot_id = get_current_boot_id()
    alert_text = format_boot_alert()
    logger.info(f"Yangi server booti aniqlandi (ID: {current_boot_id}). Alert yuborilmoqda...")

    # background_tasks dagi broadcast orqali yuboramiz
    from background_tasks import broadcast_alert
    await broadcast_alert(bot, alert_text)

    mark_boot_notified(current_boot_id)
    return True

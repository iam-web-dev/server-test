import asyncio
import json
import logging
import os
import platform
import re
import shutil
import subprocess
import time
from datetime import datetime
from zoneinfo import ZoneInfo
import config

logger = logging.getLogger(__name__)


def get_cpu_percent(sample_duration: float = 0.2) -> float:
    """
    /proc/stat orqali protsessor (CPU) dan foydalanish foizini hisoblash.
    """
    try:
        with open("/proc/stat", "r") as f:
            fields1 = [float(col) for col in f.readline().strip().split()[1:5]]
        time.sleep(sample_duration)
        with open("/proc/stat", "r") as f:
            fields2 = [float(col) for col in f.readline().strip().split()[1:5]]

        idle_delta = fields2[3] - fields1[3]
        total_delta = sum(fields2) - sum(fields1)
        if total_delta <= 0:
            return 0.0
        usage = 100.0 * (1.0 - idle_delta / total_delta)
        return max(0.0, min(100.0, round(usage, 1)))
    except Exception as e:
        logger.warning(f"CPU foizini hisoblashda xatolik: {e}")
        return 0.0


def get_load_average() -> tuple[float, float, float]:
    """
    Tizim yuklamasi (Load Average: 1, 5, 15 daqiqa).
    """
    try:
        load1, load5, load15 = os.getloadavg()
        return round(load1, 2), round(load5, 2), round(load15, 2)
    except Exception:
        try:
            with open("/proc/loadavg", "r") as f:
                parts = f.readline().split()
                return float(parts[0]), float(parts[1]), float(parts[2])
        except Exception:
            return 0.0, 0.0, 0.0


def get_memory_usage() -> dict:
    """
    Operativ xotira (RAM) dan foydalanish statistikasi.
    """
    mem = {}
    try:
        with open("/proc/meminfo", "r") as f:
            for line in f:
                parts = line.split(":")
                if len(parts) == 2:
                    key = parts[0].strip()
                    val = parts[1].strip().split()[0]
                    mem[key] = int(val)

        total_kb = mem.get("MemTotal", 0)
        free_kb = mem.get("MemFree", 0)
        avail_kb = mem.get("MemAvailable", free_kb)
        used_kb = max(0, total_kb - avail_kb)

        total_mb = total_kb / 1024
        used_mb = used_kb / 1024
        free_mb = free_kb / 1024
        avail_mb = avail_kb / 1024
        percent = (used_kb / total_kb * 100) if total_kb > 0 else 0.0

        return {
            "total_mb": round(total_mb, 1),
            "used_mb": round(used_mb, 1),
            "free_mb": round(free_mb, 1),
            "avail_mb": round(avail_mb, 1),
            "percent": round(percent, 1),
        }
    except Exception as e:
        logger.warning(f"Xotira statistikasini olishda xato: {e}")
        return {"total_mb": 0.0, "used_mb": 0.0, "free_mb": 0.0, "avail_mb": 0.0, "percent": 0.0}


def get_disk_usage(path: str = "/") -> dict:
    """
    Disk xotirasidan foydalanish ko'rsatkichlari.
    """
    try:
        usage = shutil.disk_usage(path)
        total_gb = usage.total / (1024**3)
        used_gb = usage.used / (1024**3)
        free_gb = usage.free / (1024**3)
        percent = (usage.used / usage.total * 100) if usage.total > 0 else 0.0
        return {
            "total_gb": round(total_gb, 2),
            "used_gb": round(used_gb, 2),
            "free_gb": round(free_gb, 2),
            "percent": round(percent, 1),
        }
    except Exception as e:
        logger.warning(f"Disk statistikasini olishda xato: {e}")
        return {"total_gb": 0.0, "used_gb": 0.0, "free_gb": 0.0, "percent": 0.0}


def get_uptime() -> str:
    """
    Server qancha vaqtdan beri uzluksiz ishlab turganini (Uptime) aniqlash.
    """
    try:
        with open("/proc/uptime", "r") as f:
            seconds = float(f.readline().split()[0])
        days = int(seconds // (24 * 3600))
        hours = int((seconds % (24 * 3600)) // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)

        parts = []
        if days > 0:
            parts.append(f"{days} kun")
        if hours > 0:
            parts.append(f"{hours} soat")
        if minutes > 0:
            parts.append(f"{minutes} daqiqa")
        parts.append(f"{secs} soniya")
        return " ".join(parts)
    except Exception:
        return "Noma'lum"


def get_system_info() -> dict:
    """
    Operatsion tizim va arxitektura ma'lumotlari.
    """
    distro = "Linux"
    if os.path.exists("/etc/os-release"):
        try:
            with open("/etc/os-release") as f:
                for line in f:
                    if line.startswith("PRETTY_NAME="):
                        distro = line.split("=")[1].strip().strip('"')
                        break
        except Exception:
            pass

    return {
        "hostname": platform.node(),
        "os": distro,
        "kernel": platform.release(),
        "arch": platform.machine(),
    }


def get_network_io() -> dict:
    """
    Tarmoq orqali qabul qilingan va uzatilgan trafik hajmi (MB).
    """
    try:
        rx_bytes, tx_bytes = 0, 0
        with open("/proc/net/dev", "r") as f:
            lines = f.readlines()[2:]
            for line in lines:
                parts = line.split(":")
                if len(parts) == 2:
                    iface = parts[0].strip()
                    if iface == "lo":
                        continue
                    data = parts[1].split()
                    rx_bytes += int(data[0])
                    tx_bytes += int(data[8])
        return {
            "rx_mb": round(rx_bytes / (1024**2), 2),
            "tx_mb": round(tx_bytes / (1024**2), 2),
        }
    except Exception:
        return {"rx_mb": 0.0, "tx_mb": 0.0}


def get_top_processes(n: int = 7) -> list[dict]:
    """
    Eng ko'p CPU va RAM ishlatayotgan jarayonlarni aniqlash.
    """
    processes = []
    try:
        res = subprocess.run(
            ["ps", "-eo", "pid,%cpu,%mem,comm", "--sort=-%cpu"],
            capture_output=True,
            text=True,
            timeout=3,
        )
        lines = res.stdout.strip().split("\n")
        for line in lines[1 : n + 1]:
            parts = line.split(maxsplit=3)
            if len(parts) >= 4:
                processes.append({
                    "pid": parts[0],
                    "cpu": parts[1],
                    "mem": parts[2],
                    "comm": parts[3],
                })
    except Exception as e:
        logger.warning(f"Top jarayonlarni olishda xatolik: {e}")
    return processes


def check_service_status(service_name: str) -> dict:
    """
    Biror servis yoki jarayon holatini tekshirish.
    """
    clean_name = service_name.replace(".service", "").strip()

    # 1. systemctl orqali tekshirish
    try:
        res = subprocess.run(
            ["systemctl", "is-active", service_name],
            capture_output=True,
            text=True,
            timeout=2,
        )
        out = res.stdout.strip()
        err = res.stderr.strip()
        if "not been booted with systemd" not in err and "not been booted with systemd" not in out:
            if out == "active":
                return {"name": clean_name, "status": "active", "type": "systemd", "details": "Faol ishlab turibdi"}
            elif out == "failed":
                err_log = ""
                try:
                    j_res = subprocess.run(
                        ["journalctl", "-u", service_name, "-n", "3", "--no-pager"],
                        capture_output=True,
                        text=True,
                        timeout=2,
                    )
                    err_log = j_res.stdout.strip()
                except Exception:
                    pass
                return {
                    "name": clean_name,
                    "status": "failed",
                    "type": "systemd",
                    "details": err_log or "Servis ishlamay qoldi (failed)",
                }
            elif out in ("inactive", "deactivating"):
                return {"name": clean_name, "status": "inactive", "type": "systemd", "details": "Servis to'xtatilgan"}
    except Exception:
        pass

    # 2. Process (ps) orqali tekshirish
    try:
        res = subprocess.run(["ps", "-eo", "comm,args"], capture_output=True, text=True, timeout=2)
        lines = res.stdout.lower()
        for line in lines.split("\n"):
            if clean_name.lower() in line and "ps -eo" not in line and "check_service" not in line:
                return {"name": clean_name, "status": "active", "type": "process", "details": "Jarayon faol"}
        return {"name": clean_name, "status": "inactive", "type": "process", "details": "Jarayon topilmadi"}
    except Exception as e:
        return {"name": clean_name, "status": "unknown", "type": "unknown", "details": str(e)}


def check_all_services(services: list[str]) -> list[dict]:
    """Barcha monitoring qilinadigan servislarni tekshirish."""
    return [check_service_status(s) for s in services]


# =====================================================================
# KENGAYTIRILGAN LOG VA SERVER HARAKATLARINI TAHLIL QILISH (CLASSIFIER)
# =====================================================================
def classify_log_entry(raw_line: str, source: str = "") -> dict | None:
    """
    Har qanday log satrini tahlil qilib, uning qaysi server harakati yoki
    hodisasi ekanligini (Security, Sudo, Service, Error, Warning, System, Action) aniqlaydi.
    """
    line = raw_line.strip()
    if not line:
        return None

    line_lower = line.lower()

    # 1. XAVFSIZLIK VA KIRISH AMALLARI (SECURITY)
    if "security" in config.WATCH_LOG_CATEGORIES:
        # Muvaffaqiyatsiz kirish urinishlari (Brute-force xavfi)
        if any(kw in line_lower for kw in [
            "failed password for",
            "authentication failure",
            "invalid user",
            "pam: authentication failure",
            "failed publickey",
        ]):
            return {
                "category": "security",
                "emoji": "🚨",
                "title": "XAVFSIZLIK: Muvaffaqiyatsiz Kirish Urinishi",
                "severity": "HIGH",
                "source": source,
                "text": line,
            }

        # Muvaffaqiyatli SSH / Tizim kirishlari
        if any(kw in line_lower for kw in [
            "accepted password for",
            "accepted publickey for",
            "accepted keyboard-interactive",
        ]):
            return {
                "category": "security",
                "emoji": "🔐",
                "title": "XAVFSIZLIK: Yangi SSH Kirishi Muvaffaqiyatli",
                "severity": "NOTICE",
                "source": source,
                "text": line,
            }

        # SUDO orqali buyruq bajarilishi
        if "command=" in line_lower and ("sudo" in line_lower or "sudo:" in line_lower):
            return {
                "category": "security",
                "emoji": "👤",
                "title": "SUDO: Administrator Buyrug'i Bajarildi",
                "severity": "NOTICE",
                "source": source,
                "text": line,
            }

        # Sessiya ochilishi (Session opened)
        if "session opened for user" in line_lower and "cron" not in line_lower:
            return {
                "category": "security",
                "emoji": "🔑",
                "title": "XAVFSIZLIK: Yangi Tizim Sessiyasi Ochildi",
                "severity": "INFO",
                "source": source,
                "text": line,
            }

    # 2. TIZIM VA RESURS AVARIYALARI (SYSTEM)
    if "system" in config.WATCH_LOG_CATEGORIES:
        # OOM Killer (xotira yetishmovchiligidan jarayon o'ldirilishi)
        if any(kw in line_lower for kw in ["out of memory: killed process", "oom-killer", "invoked oom-killer"]):
            return {
                "category": "system",
                "emoji": "💀",
                "title": "TIZIM: Jarayon Xotira Yetishmovchiligidan O'ldirildi (OOM Killer)",
                "severity": "CRITICAL",
                "source": source,
                "text": line,
            }

        # Server o'chishi yoki qayta yuklanishi
        if any(kw in line_lower for kw in [
            "system is rebooting",
            "system is powering down",
            "reached target reboot.target",
            "reached target shutdown.target",
            "reboot.target",
        ]):
            return {
                "category": "system",
                "emoji": "⚠️",
                "title": "TIZIM: Server O'chirilmoqda yoki Qayta Yuklanmoqda",
                "severity": "CRITICAL",
                "source": source,
                "text": line,
            }

        # Kernel Panic
        if "kernel panic" in line_lower or "bug: unable to handle page fault" in line_lower:
            return {
                "category": "system",
                "emoji": "🔥",
                "title": "TIZIM: Yadro Xatoligi (Kernel Panic)",
                "severity": "CRITICAL",
                "source": source,
                "text": line,
            }

    # 3. SERVISLAR AMALLARI VA O'ZGARISHLARI (SERVICE)
    if "service" in config.WATCH_LOG_CATEGORIES:
        if "started " in line_lower and any(k in line_lower for k in ["service", "systemd", "server", "daemon"]):
            return {
                "category": "service",
                "emoji": "🟢",
                "title": "SERVIS: Servis Ishga Tushdi (Started)",
                "severity": "INFO",
                "source": source,
                "text": line,
            }
        if "stopped " in line_lower and any(k in line_lower for k in ["service", "systemd", "server", "daemon"]):
            return {
                "category": "service",
                "emoji": "⚪️",
                "title": "SERVIS: Servis To'xtatildi (Stopped)",
                "severity": "WARNING",
                "source": source,
                "text": line,
            }
        if any(kw in line_lower for kw in ["reloading ", "reloaded ", "restarting "]):
            return {
                "category": "service",
                "emoji": "🔄",
                "title": "SERVIS: Servis Qayta Yuklandi / Ishga Tushirildi",
                "severity": "INFO",
                "source": source,
                "text": line,
            }
        if any(kw in line_lower for kw in ["failed with result", "unit entered failed state", "failed to start"]):
            return {
                "category": "service",
                "emoji": "🔴",
                "title": "SERVIS: Servis Ishlamay Qoldi (Failed)",
                "severity": "CRITICAL",
                "source": source,
                "text": line,
            }

    # 4. XATOLIKLAR VA AVARIYALAR (ERROR)
    if "error" in config.WATCH_LOG_CATEGORIES:
        if any(kw in line_lower for kw in [
            "[error]",
            "error:",
            "critical:",
            "fatal:",
            "exception:",
            "traceback (most recent call last)",
            "segmentation fault",
            "core dumped",
        ]):
            return {
                "category": "error",
                "emoji": "🔴",
                "title": "XATOLIK: Tizim yoki Dastur Xatosi",
                "severity": "ERROR",
                "source": source,
                "text": line,
            }

    # 5. OGOHLANTIRISHLAR (WARNING)
    if "warning" in config.WATCH_LOG_CATEGORIES:
        if any(kw in line_lower for kw in [
            "[warn]",
            "[warning]",
            "warning:",
            "permission denied",
            "access denied",
            "connection refused",
            "connection timed out",
            "network is unreachable",
        ]):
            return {
                "category": "warning",
                "emoji": "🟡",
                "title": "OGOHLANTIRISH: Tizim Ogohlantirishi",
                "severity": "WARNING",
                "source": source,
                "text": line,
            }

    # 6. MUHIM OPERATSIYALAR VA AMALLAR (ACTION)
    if "action" in config.WATCH_LOG_CATEGORIES:
        if any(kw in line_lower for kw in [
            "[deploy]",
            "[backup]",
            "[cron]",
            "[migration]",
            "installed:",
            "upgraded:",
            "erased:",
            "git pull",
            "docker run",
            "docker stop",
        ]):
            return {
                "category": "action",
                "emoji": "📦",
                "title": "HARAKAT: Muhim Operatsiya Bajarildi",
                "severity": "INFO",
                "source": source,
                "text": line,
            }

    # 7. FOYDALANUVCHI MAXSUS KALIT SO'ZLARI (CUSTOM KEYWORDS)
    if config.CUSTOM_LOG_KEYWORDS:
        for kw in config.CUSTOM_LOG_KEYWORDS:
            if kw in line_lower:
                return {
                    "category": "custom",
                    "emoji": "📌",
                    "title": f"MAXSUS HARAKAT: «{kw}» bo'yicha hodisa",
                    "severity": "NOTICE",
                    "source": source,
                    "text": line,
                }

    return None


# =====================================================================
# JOURNALCTL BILAN ISHLASH (SYSTEM-WIDE EVENT STREAM)
# =====================================================================
def get_journalctl_cursor() -> str | None:
    """Systemd journalctl ning hozirgi oxirgi kursorini olish."""
    if not config.ENABLE_JOURNALCTL:
        return None
    try:
        res = subprocess.run(
            ["journalctl", "-n", "1", "-o", "json"],
            capture_output=True,
            text=True,
            timeout=3,
        )
        if res.returncode == 0 and res.stdout.strip():
            data = json.loads(res.stdout.strip().split("\n")[-1])
            return data.get("__CURSOR")
    except Exception:
        pass
    return None


def fetch_journalctl_events_after(cursor: str, max_entries: int = 40) -> tuple[list[dict], str | None]:
    """
    Kursor orqali oxirgi marta o'qilgandan so'ng yuz bergan yangi barcha tizim hodisalarini o'qish.
    """
    if not config.ENABLE_JOURNALCTL or not cursor:
        return [], cursor

    cmd = ["journalctl", f"--after-cursor={cursor}", "-n", str(max_entries), "-o", "json"]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=4)
        if res.returncode != 0 or not res.stdout.strip():
            return [], cursor

        new_entries = []
        last_cursor = cursor
        for raw_item in res.stdout.strip().split("\n"):
            if not raw_item.strip():
                continue
            try:
                obj = json.loads(raw_item)
                last_cursor = obj.get("__CURSOR", last_cursor)
                msg = obj.get("MESSAGE", "")
                ident = obj.get("SYSLOG_IDENTIFIER") or obj.get("_COMM") or "system"
                line = f"{ident}: {msg}" if ident else msg

                classified = classify_log_entry(line, source="journalctl")
                if classified:
                    new_entries.append(classified)
            except Exception:
                continue

        return new_entries, last_cursor
    except Exception as e:
        logger.debug(f"Journalctl o'qishda xatolik: {e}")
        return [], cursor


# =====================================================================
# LOGLARNI O'QISH VA STATISTIKA
# =====================================================================
def get_recent_categorized_logs(category: str = "all", limit: int = 15) -> str:
    """
    Serverdagi so'nggi muhim harakatlar va loglarni o'qib, chiroyli ro'yxat ko'rinishida qaytarish.
    """
    raw_lines = []

    # 1. Log fayllardan o'qiymiz
    for f_path in config.WATCH_LOG_FILES:
        if os.path.exists(f_path):
            try:
                with open(f_path, "r", encoding="utf-8", errors="replace") as f:
                    lines = f.readlines()
                    for l in lines[-limit:]:
                        raw_lines.append((l.strip(), os.path.basename(f_path)))
            except Exception:
                pass

    # 2. Agar journalctl mavjud bo'lsa, undan ham oxirgi hodisalarni qo'shamiz
    if config.ENABLE_JOURNALCTL:
        try:
            res = subprocess.run(
                ["journalctl", "-n", str(limit * 2), "--no-pager"],
                capture_output=True,
                text=True,
                timeout=3,
            )
            if res.returncode == 0 and res.stdout.strip():
                for l in res.stdout.strip().split("\n")[-limit:]:
                    raw_lines.append((l.strip(), "journalctl"))
        except Exception:
            pass

    if not raw_lines:
        return "ℹ️ Hozircha hech qanday loglar topilmadi."

    matched_logs = []
    for line, src in raw_lines:
        classified = classify_log_entry(line, source=src)
        if classified:
            if category == "all" or classified["category"] == category:
                matched_logs.append(classified)

    if not matched_logs:
        return f"ℹ️ «{category}» kategoriyasiga mos keluvchi yangi loglar topilmadi."

    formatted_items = []
    for item in matched_logs[-limit:]:
        short_text = item["text"]
        if len(short_text) > 120:
            short_text = short_text[:120] + "..."
        formatted_items.append(f"{item['emoji']} <b>{item['title']}</b>\n<code>{short_text}</code>")

    return "\n\n".join(formatted_items)


def append_test_activity_log(category: str = "security", custom_message: str = "") -> str:
    """
    Turli server harakatlarini (SSH, Sudo, Servis, Xatolik, Deploy) sinash uchun test logi yozish.
    """
    log_dir = os.path.join(os.path.dirname(__file__), "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "server_activity.log")

    now_str = datetime.now(ZoneInfo(config.TIMEZONE)).strftime("%Y-%m-%d %H:%M:%S")

    sample_templates = {
        "security": f"[{now_str}] sshd[4912]: Failed password for root from 192.168.1.140 port 54210 ssh2",
        "ssh_ok": f"[{now_str}] sshd[4915]: Accepted publickey for admin from 192.168.1.50 port 51120 ssh2",
        "sudo": f"[{now_str}] sudo: iamwebdev : TTY=pts/0 ; COMMAND=/usr/bin/systemctl restart nginx",
        "service": f"[{now_str}] systemd[1]: Started Nginx HTTP and reverse proxy server.",
        "error": f"[{now_str}] [ERROR] [BackendAPI] DatabaseConnectionError: Connection to database socket failed.",
        "warning": f"[{now_str}] [WARN] [Proxy] High latency detected on upstream server (timeout: 5000ms).",
        "action": f"[{now_str}] [DEPLOY] Application version v3.4.0 deployed successfully by CI/CD pipeline.",
    }

    log_line = custom_message or sample_templates.get(category, sample_templates["security"])
    log_line = log_line.strip() + "\n"

    with open(log_file, "a", encoding="utf-8") as f:
        f.write(log_line)

    return log_file

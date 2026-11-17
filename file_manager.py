import asyncio
import logging
import os
import shutil
import subprocess

import server_monitor

logger = logging.getLogger(__name__)


def tail_file(filepath: str, lines: int = 40) -> tuple[bool, str]:
    """Faylning oxirgi qatorlarini xotirani to'ldirmasdan xavfsiz o'qish."""
    clean_path = os.path.abspath(filepath.strip())
    if not os.path.exists(clean_path):
        return False, f"⚠️ Fayl topilmadi: <code>{clean_path}</code>"

    if os.path.isdir(clean_path):
        return False, f"⚠️ Bu katalog (papka), fayl emas: <code>{clean_path}</code>"

    # 1. Agar tizimda tail buyrug'i mavjud bo'lsa (Linux da eng tezkor va xavfsiz)
    if shutil.which("tail"):
        try:
            res = subprocess.run(
                ["tail", "-n", str(lines), clean_path],
                capture_output=True,
                text=True,
                timeout=3,
                errors="replace",
            )
            out = res.stdout
            if not out.strip():
                out = "(Fayl bo'sh)"
            return True, out
        except Exception:
            pass

    # 2. Python fallback: faqat oxirgi 128KB blokni o'qish (OOM ni oldini oladi)
    try:
        buffer_size = 128 * 1024
        file_size = os.path.getsize(clean_path)
        with open(clean_path, "r", encoding="utf-8", errors="replace") as f:
            if file_size > buffer_size:
                f.seek(file_size - buffer_size)
            all_lines = f.readlines()
            tail_lines = all_lines[-lines:] if file_size <= buffer_size else all_lines[1:][-lines:]
            content = "".join(tail_lines)
            if not content.strip():
                content = "(Fayl bo'sh)"
            return True, content
    except Exception as e:
        return False, f"❌ Faylni o'qishda xatolik: {e}"


def prepare_file_for_download(filepath: str, max_size_mb: int = 45) -> tuple[bool, str, bytes | None, str]:
    """
    Faylni Telegram orqali yuklashga tayyorlash.
    Qaytaradi: (ok, message, file_bytes, filename)
    """
    clean_path = os.path.abspath(filepath.strip())
    filename = os.path.basename(clean_path)

    if not os.path.exists(clean_path):
        return False, f"⚠️ Fayl topilmadi: <code>{clean_path}</code>", None, filename

    if os.path.isdir(clean_path):
        return False, f"⚠️ Bu katalog: <code>{clean_path}</code>. Faqat fayllarni yuklash mumkin.", None, filename

    try:
        size_bytes = os.path.getsize(clean_path)
        size_mb = size_bytes / (1024 * 1024)
        if size_mb > max_size_mb:
            return (
                False,
                f"⚠️ Fayl juda katta (<code>{round(size_mb, 1)} MB</code>). Telegram bot chegarasi: {max_size_mb} MB.",
                None,
                filename,
            )

        with open(clean_path, "rb") as f:
            data = f.read()

        return True, "✅ Fayl tayyorlandi.", data, filename
    except PermissionError:
        return False, f"⛔️ Faylni o'qish uchun huquq yetarli emas: <code>{clean_path}</code>", None, filename
    except Exception as e:
        return False, f"❌ Xatolik: {str(e)}", None, filename


async def clean_system_cache() -> dict[str, str]:
    """
    Server keshini tozalash (journalctl vacuum, apt clean, docker system prune).
    """
    before_disk = server_monitor.get_disk_usage()
    actions_done = []

    # 1. Journalctl vacuum
    if shutil.which("journalctl"):
        try:
            proc = await asyncio.create_subprocess_exec(
                "journalctl", "--vacuum-time=2d",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            actions_done.append("• Journalctl loglari (2 kundan eskisi) tozalandi.")
        except Exception:
            pass

    # 2. Apt clean
    if shutil.which("apt-get"):
        try:
            proc = await asyncio.create_subprocess_exec(
                "apt-get", "clean",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()
            actions_done.append("• APT paketlar kesh /var/cache/apt/archives tozalandi.")
        except Exception:
            pass

    # 3. Docker system prune
    if shutil.which("docker"):
        try:
            proc = await asyncio.create_subprocess_exec(
                "docker", "system", "prune", "-f",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            actions_done.append("• Docker ishlatilmayotgan resurslari tozalandi.")
        except Exception:
            pass

    after_disk = server_monitor.get_disk_usage()
    freed_gb = max(0.0, round(after_disk["free_gb"] - before_disk["free_gb"], 2))

    summary = (
        f"🧹 <b>SERVER KESHI VA KERAKSIZ FAYLLAR TOZALANDI!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        + "\n".join(actions_done or ["• Hech qanday tozalash amali mavjud emas."]) +
        f"\n━━━━━━━━━━━━━━━━━━━━\n"
        f"💾 <b>Hozirgi disk bo'sh joyi:</b> <code>{after_disk['free_gb']} GB</code> ({after_disk['percent']}% band)\n"
        f"🎉 <i>Bo'shatilgan joy: taxminan {freed_gb} GB</i>"
    )

    return {
        "status": "success",
        "details": summary,
        "freed_gb": str(freed_gb),
    }

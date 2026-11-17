import asyncio
import html
import logging
import os
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramRetryAfter

import auth_manager
import boot_notifier
import config
import server_monitor

logger = logging.getLogger(__name__)

# Servislarning oxirgi holatlarini eslab qolish
last_service_states: dict[str, str] = {}

# Resurslar bo'yicha spam ogohlantirishlarni oldini olish uchun cooldown (soniya)
RESOURCE_COOLDOWN = 600  # 10 daqiqa
last_resource_alerts: dict[str, float] = {
    "cpu": 0.0,
    "ram": 0.0,
    "disk": 0.0,
}

# Kuzatiladigan log fayllarining oxirgi o'qilgan bayt pozitsiyasi
log_file_offsets: dict[str, int] = {}

# Systemd journalctl oxirgi o'qilgan kursori
journalctl_cursor: str | None = None

# Bir xil loglar spam bo'lmasligi uchun cheklov xotirasi (Throttling)
# Key: (category, signature) -> Value: (last_timestamp, repeat_count)
recent_log_throttles: dict[str, list] = {}

SEVERITY_ORDER = {"CRITICAL": 4, "HIGH": 3, "WARNING": 2, "NOTICE": 1, "INFO": 0, "LOW": 0}


def is_alert_allowed(item: dict) -> bool:
    """
    Faqat belgilangan darajadagi (default: HIGH va CRITICAL) muhim hodisalarni adminga push-alert qilish.
    Oddiy kichik dastur ogohlantirishlari (warnings) yoki mayda xatolar spam bo'lmasligi uchun cheklanadi.
    """
    min_sev = getattr(config, "MIN_ALERT_SEVERITY", "HIGH").upper()
    min_level = SEVERITY_ORDER.get(min_sev, 3)
    item_sev = item.get("severity", "INFO").upper()
    return SEVERITY_ORDER.get(item_sev, 0) >= min_level


async def broadcast_alert(bot: Bot, text: str):
    """
    Tizimga kirgan barcha faol adminlarga ogohlantirish xabarini yuborish.
    """
    admin_ids = auth_manager.get_authenticated_user_ids()
    if not admin_ids:
        logger.debug("Ogohlantirish yuborish uchun faol adminlar topilmadi.")
        return

    for chat_id in admin_ids:
        try:
            await bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
            )
        except TelegramForbiddenError:
            logger.warning(f"Admin {chat_id} botni bloklagan. Tizimdan chiqarilmoqda.")
            auth_manager.logout(chat_id)
        except TelegramRetryAfter as e:
            logger.warning(f"Telegram flood limit: {e.retry_after} soniya kutilmoqda.")
            await asyncio.sleep(e.retry_after)
        except TelegramBadRequest as e:
            logger.warning(f"Admin {chat_id} ga xabar yuborishda xato: {e.message}")
        except Exception as e:
            logger.error(f"Xabar yuborishda kutilmagan xatolik (ID: {chat_id}): {e}")


def _should_throttle(item: dict) -> bool:
    """
    Bir xil yoki ketma-ket takrorlanuvchi loglar adminga spam bo'lmasligi uchun tekshirish.
    """
    signature = f"{item['category']}_{item['title']}_{item['text'][:40]}"
    now = time.time()

    if signature in recent_log_throttles:
        last_time, count = recent_log_throttles[signature]
        if now - last_time < config.LOG_THROTTLE_SECONDS:
            # Vaqt oralig'ida takrorlandi, sonini oshiramiz va yubormaymiz
            recent_log_throttles[signature] = [last_time, count + 1]
            return True
        else:
            # Yangi davr boshlandi
            recent_log_throttles[signature] = [now, 0]
            return False
    else:
        recent_log_throttles[signature] = [now, 0]
        # Eski yozuvlarni tozalash (xotira to'lib ketmasligi uchun)
        if len(recent_log_throttles) > 200:
            for k in list(recent_log_throttles.keys())[:50]:
                del recent_log_throttles[k]
        return False


def _init_log_offsets():
    """Boshlang'ich holatda mavjud loglarning oxirgi pozitsiyasini belgilab olish."""
    global journalctl_cursor
    for log_path in config.WATCH_LOG_FILES:
        if os.path.exists(log_path):
            try:
                log_file_offsets[log_path] = os.path.getsize(log_path)
            except Exception:
                log_file_offsets[log_path] = 0
        else:
            log_file_offsets[log_path] = 0

    # Journalctl kursorini boshlang'ich pozitsiyaga qo'yish
    if config.ENABLE_JOURNALCTL:
        journalctl_cursor = server_monitor.get_journalctl_cursor()


async def check_services_and_alert(bot: Bot, is_initial: bool = False):
    """
    Servislar yoki jarayonlar holatini tekshirish.
    Agar holat o'zgarsa (masalan: active -> inactive/failed yoki aksincha), alert yuborish.
    """
    now_str = datetime.now(ZoneInfo(config.TIMEZONE)).strftime("%H:%M:%S (%d.%m.%Y)")

    for service_name in config.MONITORED_SERVICES:
        info = server_monitor.check_service_status(service_name)
        current_status = info["status"]
        prev_status = last_service_states.get(service_name)

        if is_initial:
            last_service_states[service_name] = current_status
            continue

        if prev_status is not None and prev_status != current_status:
            # Holat o'zgardi!
            if current_status in ("inactive", "failed"):
                alert_text = (
                    f"🚨 <b>DIQQAT: SERVIS O'CHDI YOKI O'ZGARDI!</b>\n\n"
                    f"⚙️ <b>Servis nomi:</b> <code>{service_name}</code>\n"
                    f"🔴 <b>Yangi holat:</b> <code>{current_status.upper()}</code>\n"
                    f"⚪️ <b>Oldingi holat:</b> <code>{prev_status}</code>\n"
                    f"🕒 <b>Vaqt:</b> <code>{now_str}</code>\n"
                    f"📋 <b>Tafsilot:</b> {info['details']}\n\n"
                    f"<i>Iltimos, serverdagi holatni tekshiring!</i>"
                )
                await broadcast_alert(bot, alert_text)
            elif current_status == "active":
                alert_text = (
                    f"✅ <b>SERVIS QAYTA ISHGA TUSHDI:</b>\n\n"
                    f"⚙️ <b>Servis nomi:</b> <code>{service_name}</code>\n"
                    f"🟢 <b>Yangi holat:</b> <code>ACTIVE</code>\n"
                    f"🕒 <b>Vaqt:</b> <code>{now_str}</code>\n"
                    f"📋 <b>Tafsilot:</b> {info['details']}"
                )
                await broadcast_alert(bot, alert_text)

            last_service_states[service_name] = current_status
        elif prev_status is None:
            last_service_states[service_name] = current_status


async def check_resources_and_alert(bot: Bot):
    """
    CPU, RAM, Disk ko'rsatkichlarini tekshirish va yuqori yuklamada ogohlantirish.
    """
    current_time = time.time()
    now_str = datetime.now(ZoneInfo(config.TIMEZONE)).strftime("%H:%M:%S (%d.%m.%Y)")

    # 1. CPU
    cpu_pct = server_monitor.get_cpu_percent(sample_duration=0.2)
    if cpu_pct >= config.CPU_THRESHOLD:
        if current_time - last_resource_alerts["cpu"] >= RESOURCE_COOLDOWN:
            last_resource_alerts["cpu"] = current_time
            load1, load5, load15 = server_monitor.get_load_average()
            alert_text = (
                f"⚠️ <b>OGOHLANTIRISH: YUQORI CPU YUKLAMASI!</b>\n\n"
                f"🔥 <b>CPU ko'rsatkichi:</b> <code>{cpu_pct}%</code> (Chegara: {config.CPU_THRESHOLD}%)\n"
                f"📊 <b>Load Average:</b> <code>{load1}, {load5}, {load15}</code>\n"
                f"🕒 <b>Vaqt:</b> <code>{now_str}</code>\n\n"
                f"<i>Serverdagi faol jarayonlarni tekshirish uchun «⚡️ Top Jarayonlar» tugmasidan foydalaning.</i>"
            )
            await broadcast_alert(bot, alert_text)

    # 2. RAM
    mem = server_monitor.get_memory_usage()
    if mem["percent"] >= config.RAM_THRESHOLD:
        if current_time - last_resource_alerts["ram"] >= RESOURCE_COOLDOWN:
            last_resource_alerts["ram"] = current_time
            alert_text = (
                f"⚠️ <b>OGOHLANTIRISH: XOTIRA (RAM) TO'LMOQDA!</b>\n\n"
                f"🧠 <b>Ishlatilayotgan RAM:</b> <code>{mem['percent']}%</code>\n"
                f"📦 <b>Ishlatilgan / Jami:</b> <code>{mem['used_mb']} MB / {mem['total_mb']} MB</code>\n"
                f"🆓 <b>Bo'sh xotira:</b> <code>{mem['avail_mb']} MB</code>\n"
                f"🕒 <b>Vaqt:</b> <code>{now_str}</code>"
            )
            await broadcast_alert(bot, alert_text)

    # 3. Disk
    disk = server_monitor.get_disk_usage()
    if disk["percent"] >= config.DISK_THRESHOLD:
        if current_time - last_resource_alerts["disk"] >= (RESOURCE_COOLDOWN * 2):
            last_resource_alerts["disk"] = current_time
            alert_text = (
                f"🚨 <b>DIQQAT: DISK XOTIRASI TO'LIB BORMOQDA!</b>\n\n"
                f"💾 <b>Disk bandligi:</b> <code>{disk['percent']}%</code>\n"
                f"📦 <b>Ishlatilgan / Jami:</b> <code>{disk['used_gb']} GB / {disk['total_gb']} GB</code>\n"
                f"🆓 <b>Bo'sh joy:</b> <code>{disk['free_gb']} GB</code>\n"
                f"🕒 <b>Vaqt:</b> <code>{now_str}</code>"
            )
            await broadcast_alert(bot, alert_text)


async def check_log_events_and_alert(bot: Bot):
    """
    Fayllar va journalctl dagi barcha muhim server harakatlari va loglarini tekshirish.
    """
    global journalctl_cursor
    now_str = datetime.now(ZoneInfo(config.TIMEZONE)).strftime("%H:%M:%S")

    # 1. Kuzatiladigan log fayllarni tekshirish
    for log_path in config.WATCH_LOG_FILES:
        if not os.path.exists(log_path):
            continue

        try:
            curr_size = os.path.getsize(log_path)
            prev_offset = log_file_offsets.get(log_path, curr_size)

            if curr_size < prev_offset:
                prev_offset = 0

            if curr_size > prev_offset:
                with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                    f.seek(prev_offset)
                    new_lines = f.readlines()
                    log_file_offsets[log_path] = f.tell()

                for raw_line in new_lines:
                    classified = server_monitor.classify_log_entry(raw_line, source=os.path.basename(log_path))
                    if classified:
                        if not is_alert_allowed(classified):
                            continue
                        if _should_throttle(classified):
                            continue

                        snippet = classified["text"]
                        if len(snippet) > 600:
                            snippet = snippet[:600] + "... [qisqartirildi]"

                        escaped_snippet = html.escape(snippet)
                        alert_text = (
                            f"{classified['emoji']} <b>MUHIM SERVER HARAKATI:</b>\n"
                            f"━━━━━━━━━━━━━━━━━━━━\n"
                            f"📌 <b>Hodisa:</b> <b>{classified['title']}</b>\n"
                            f"📁 <b>Manba:</b> <code>{classified['source']}</code>\n"
                            f"🕒 <b>Vaqt:</b> <code>{now_str}</code>\n"
                            f"📋 <b>Log matni:</b>\n"
                            f"<pre>{escaped_snippet}</pre>"
                        )
                        await broadcast_alert(bot, alert_text)
            else:
                log_file_offsets[log_path] = curr_size
        except Exception as e:
            logger.warning(f"Log faylini tekshirishda xatolik ({log_path}): {e}")

    # 2. Systemd journalctl orqali server bo'ylab yangi hodisalarni tekshirish
    if config.ENABLE_JOURNALCTL and journalctl_cursor:
        try:
            events, new_cursor = server_monitor.fetch_journalctl_events_after(journalctl_cursor, max_entries=30)
            if new_cursor:
                journalctl_cursor = new_cursor

            for ev in events:
                if not is_alert_allowed(ev):
                    continue
                if _should_throttle(ev):
                    continue

                snippet = ev["text"]
                if len(snippet) > 600:
                    snippet = snippet[:600] + "... [qisqartirildi]"

                escaped_snippet = html.escape(snippet)
                alert_text = (
                    f"{ev['emoji']} <b>MUHIM SERVER HARAKATI:</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n"
                    f"📌 <b>Hodisa:</b> <b>{ev['title']}</b>\n"
                    f"⚙️ <b>Manba:</b> <code>journalctl (tizim)</code>\n"
                    f"🕒 <b>Vaqt:</b> <code>{now_str}</code>\n"
                    f"📋 <b>Log matni:</b>\n"
                    f"<pre>{escaped_snippet}</pre>"
                )
                await broadcast_alert(bot, alert_text)
        except Exception as e:
            logger.debug(f"Journalctl hodisalarini tekshirishda xato: {e}")


async def start_server_monitoring(bot: Bot):
    """
    Doimiy orqa fonda ishlovchi asosiy server monitoring jarayoni.
    """
    logger.info("Ko'p funksiyali server monitoring va log harakatlarini kuzatuvchi worker ishga tushdi.")
    _init_log_offsets()

    # Boshlang'ich servislar holatini olib olamiz
    await check_services_and_alert(bot, is_initial=True)

    # Server qayta yoqilgan bo'lsa (yangi boot), darhol adminlarga alert yuboramiz
    try:
        await boot_notifier.check_boot_and_notify(bot)
    except Exception as e:
        logger.warning(f"Boot tekshiruvida xatolik: {e}")

    while True:
        try:
            await asyncio.sleep(config.CHECK_INTERVAL)

            # 1. Servislar holatini tekshirish (o'chgan/yoqilganini aniqlash)
            await check_services_and_alert(bot, is_initial=False)

            # 2. Resurslar (CPU, RAM, Disk) yuklamasini tekshirish
            await check_resources_and_alert(bot)

            # 3. Serverdagi barcha muhim harakatlar va loglarni tekshirish
            await check_log_events_and_alert(bot)

        except asyncio.CancelledError:
            logger.info("Server monitoring fon jarayoni to'xtatildi.")
            break
        except Exception as e:
            logger.error(f"Monitoring fon jarayonida kutilmagan xatolik: {e}")
            await asyncio.sleep(5)

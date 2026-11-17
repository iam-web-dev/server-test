import asyncio
import html
import logging
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import Bot, Dispatcher, F, types
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BufferedInputFile, InlineKeyboardButton, InlineKeyboardMarkup

import auth_manager
import background_tasks
import boot_notifier
import config
import docker_manager
import file_manager
import keyboards
import network_manager
import project_manager
import server_monitor
import terminal_manager

# Loglarni sozlash
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


# FSM Holatlari
class LoginStates(StatesGroup):
    waiting_for_username = State()
    waiting_for_password = State()


class TerminalStates(StatesGroup):
    in_terminal = State()


dp = Dispatcher(storage=MemoryStorage())


# ==========================================
# YORDAMCHI MATN FORMATLASH FUNKSIYALARI
# ==========================================
def format_server_stats() -> str:
    """Server ko'rsatkichlarini chiroyli HTML formatga keltirish."""
    sys_info = server_monitor.get_system_info()
    cpu_pct = server_monitor.get_cpu_percent(sample_duration=0.2)
    load1, load5, load15 = server_monitor.get_load_average()
    mem = server_monitor.get_memory_usage()
    disk = server_monitor.get_disk_usage()
    uptime = server_monitor.get_uptime()
    net = server_monitor.get_network_io()
    now_str = datetime.now(ZoneInfo(config.TIMEZONE)).strftime("%H:%M:%S (%d.%m.%Y)")

    cpu_icon = "🟢" if cpu_pct < 60 else ("🟡" if cpu_pct < 85 else "🔴")
    ram_icon = "🟢" if mem["percent"] < 70 else ("🟡" if mem["percent"] < 90 else "🔴")
    disk_icon = "🟢" if disk["percent"] < 75 else ("🟡" if disk["percent"] < 90 else "🔴")

    text = (
        f"📊 <b>SERVER STATISTIKASI VA HOLATI</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🖥 <b>Xost:</b> <code>{sys_info['hostname']}</code>\n"
        f"🐧 <b>OS:</b> <code>{sys_info['os']}</code>\n"
        f"⚙️ <b>Yadro / Arx:</b> <code>{sys_info['kernel']} ({sys_info['arch']})</code>\n"
        f"⏱ <b>Uptime:</b> <code>{uptime}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{cpu_icon} <b>CPU bandligi:</b> <code>{cpu_pct}%</code>\n"
        f"📈 <b>Load Average:</b> <code>{load1}, {load5}, {load15}</code>\n\n"
        f"{ram_icon} <b>RAM (Operativ xotira):</b> <code>{mem['percent']}%</code>\n"
        f"   └ Ishlatilgan: <code>{mem['used_mb']} MB</code> / <code>{mem['total_mb']} MB</code>\n"
        f"   └ Bo'sh / Mavjud: <code>{mem['avail_mb']} MB</code>\n\n"
        f"{disk_icon} <b>Disk (Asosiy /):</b> <code>{disk['percent']}%</code>\n"
        f"   └ Ishlatilgan: <code>{disk['used_gb']} GB</code> / <code>{disk['total_gb']} GB</code>\n"
        f"   └ Bo'sh joy: <code>{disk['free_gb']} GB</code>\n\n"
        f"🌐 <b>Tarmoq (Trafik):</b>\n"
        f"   └ Qabul qilindi (RX): <code>{net['rx_mb']} MB</code>\n"
        f"   └ Uzatildi (TX): <code>{net['tx_mb']} MB</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🕒 <i>Yangilangan vaqt: {now_str}</i>"
    )
    return text


def format_top_processes() -> str:
    """Eng ko'p resurs ishlatayotgan jarayonlarni formatlash."""
    procs = server_monitor.get_top_processes(n=7)
    now_str = datetime.now(ZoneInfo(config.TIMEZONE)).strftime("%H:%M:%S")

    if not procs:
        return "⚠️ Faol jarayonlar haqida ma'lumot olib bo'lmadi."

    lines = ["⚡️ <b>ENG KO'P RESURS ISHLATAYOTGAN JARAYONLAR:</b>", "━━━━━━━━━━━━━━━━━━━━"]
    lines.append("<code> PID    CPU%   MEM%   BUYRUQ/NOMI</code>")
    lines.append("<code>-----------------------------------</code>")

    for p in procs:
        cmd = p["comm"][:14]
        lines.append(f"<code>{p['pid']:<6} {p['cpu']:<6} {p['mem']:<6} {cmd}</code>")

    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"🕒 <i>Yangilangan vaqt: {now_str}</i>")
    return "\n".join(lines)


def format_projects_summary(projects: dict) -> str:
    """Serverdagi loyihalar (PM2, Docker, Systemd, Jarayonlar) ro'yxatini chiqarish."""
    lines = [
        "🚀 <b>SERVERDAGI FAOL LOYIHALAR VA JARAYONLAR:</b>",
        "━━━━━━━━━━━━━━━━━━━━",
    ]

    has_any = False

    # PM2
    pm2_list = projects.get("pm2", [])
    if pm2_list:
        has_any = True
        lines.append("⚡️ <b>PM2 Ilovalari:</b>")
        for p in pm2_list:
            s_icon = "🟢" if p.get("status") == "online" else "🔴"
            lines.append(f"  {s_icon} <b>{p['name']}</b>: <code>{p['status']}</code> ({p.get('details', '')})")
        lines.append("")

    # Docker
    docker_list = projects.get("docker", [])
    if docker_list:
        has_any = True
        lines.append("🐳 <b>Docker Konteynerlari:</b>")
        for d in docker_list:
            d_icon = "🟢" if "running" in d.get("status", "").lower() or "up" in d.get("status", "").lower() else "⚪️"
            lines.append(f"  {d_icon} <b>{d['name']}</b>: <code>{d['status']}</code>")
        lines.append("")

    # Systemd app services
    systemd_list = projects.get("systemd", [])
    if systemd_list:
        has_any = True
        lines.append("⚙️ <b>Systemd Maxsus Servislari:</b>")
        for s in systemd_list:
            s_icon = "🟢" if s.get("status") == "active" else "🔴"
            lines.append(f"  {s_icon} <b>{s['name']}</b>: <code>{s['status']}</code>")
        lines.append("")

    # Standalone processes
    proc_list = projects.get("processes", [])
    if proc_list:
        has_any = True
        lines.append("⚡️ <b>Faol App Jarayonlari (Python/Node/Bot):</b>")
        for pr in proc_list[:6]:
            lines.append(f"  • PID <code>{pr['pid']}</code>: <b>{pr['name']}</b> ({pr.get('details', '')})")
        lines.append("")

    if not has_any:
        lines.append("ℹ️ Serverda hozircha alohida loyihalar topilmadi.")

    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append("<i>Boshqarish (Restart/Stop/Logs) yoki jarayonni o'chirish uchun tugmalardan foydalaning:</i>")
    return "\n".join(lines)


def format_services_status() -> str:
    """Kuzatilayotgan barcha servislar holatini formatlash."""
    services = server_monitor.check_all_services(config.MONITORED_SERVICES)
    now_str = datetime.now(ZoneInfo(config.TIMEZONE)).strftime("%H:%M:%S")

    lines = ["⚙️ <b>MONITORING QILINAYOTGAN SERVISLAR HOLATI:</b>", "━━━━━━━━━━━━━━━━━━━━"]

    active_count = 0
    for s in services:
        name = s["name"]
        status = s["status"]
        if status == "active":
            active_count += 1
            lines.append(f"🟢 <b>{name}</b>: <code>FAOL (Active)</code>")
        elif status == "inactive":
            lines.append(f"⚪️ <b>{name}</b>: <code>O'CHIRILGAN (Inactive)</code>")
        elif status == "failed":
            lines.append(f"🔴 <b>{name}</b>: <code>XATOLIK (Failed)</code>\n   └ <i>{s['details'][:60]}</i>")
        else:
            lines.append(f"⚠️ <b>{name}</b>: <code>NOMA'LUM ({status})</code>")

    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"📊 Jami: <b>{len(services)}</b> ta | Ishlayapti: <b>{active_count}</b> ta")
    lines.append(f"🕒 <i>Yangilangan vaqt: {now_str}</i>")
    return "\n".join(lines)


def format_monitoring_status() -> str:
    """Monitoring tizimining o'zi haqida hisobot."""
    admins = auth_manager.get_all_admins()
    now_str = datetime.now(ZoneInfo(config.TIMEZONE)).strftime("%H:%M:%S (%d.%m.%Y)")

    admin_lines = []
    for a in admins:
        tg_info = f"(@{a['tg_username']})" if a.get("tg_username") else ""
        admin_lines.append(f"• <code>{a['user_id']}</code> - {a.get('full_name', '')} {tg_info}")

    admins_str = "\n".join(admin_lines) if admin_lines else "<i>Hozircha faol admin yo'q.</i>"
    services_str = ", ".join([f"<code>{s}</code>" for s in config.MONITORED_SERVICES])
    logs_str = "\n".join([f"• <code>{f}</code>" for f in config.WATCH_LOG_FILES])
    categories_str = ", ".join([f"<code>{c}</code>" for c in config.WATCH_LOG_CATEGORIES])

    text = (
        f"🔔 <b>MONITORING VA MASTER TIZIM HOLATI</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🟢 <b>Monitoring holati:</b> <code>FAOL (Ishlamoqda)</code>\n"
        f"⏱ <b>Tekshirish davriyligi:</b> har <code>{config.CHECK_INTERVAL}</code> soniyada\n"
        f"🔍 <b>Journalctl monitoringi:</b> <code>{'Yoqilgan' if config.ENABLE_JOURNALCTL else 'O‘chirilgan'}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🚨 <b>Kuzatilayotgan kategoriyalar:</b>\n{categories_str}\n\n"
        f"⚙️ <b>Kuzatilayotgan servislar ({len(config.MONITORED_SERVICES)} ta):</b>\n{services_str}\n\n"
        f"📜 <b>Kuzatilayotgan log fayllar:</b>\n{logs_str}\n\n"
        f"📈 <b>Alert chegaralari:</b>\n"
        f"   └ CPU: <code>{config.CPU_THRESHOLD}%</code> | RAM: <code>{config.RAM_THRESHOLD}%</code> | Disk: <code>{config.DISK_THRESHOLD}%</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 <b>Ogohlantirish oluvchi faol adminlar ({len(admins)} ta):</b>\n{admins_str}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🕒 <i>Hozirgi vaqt: {now_str}</i>"
    )
    return text


# ==========================================
# START VA AUTENTIFIKATSIYA HANDLERLARI
# ==========================================
@dp.message(CommandStart())
async def command_start_handler(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    full_name = message.from_user.full_name

    if auth_manager.is_authenticated(user_id):
        text = (
            f"Assalomu alaykum, hurmatli <b>{full_name}</b>!\n\n"
            f"👑 Siz <b>Server SysAdmin & DevOps Master Tool</b> boshqaruvidasiz.\n"
            f"Server holati, loyihalar, terminal, portlar va tizim amallarini boshqarishingiz mumkin:"
        )
        await message.answer(text, reply_markup=keyboards.admin_main_keyboard, parse_mode=ParseMode.HTML)
    else:
        text = (
            f"Salom, <b>{full_name}</b>!\n\n"
            f"🔒 <b>Tizim himoyalangan!</b>\n"
            f"Ushbu bot server monitoringi va to'liq boshqaruvi uchun maxsus Master Tool botidir.\n\n"
            f"Kirish uchun, iltimos, <b>Admin Logini</b>ni kiriting:"
        )
        await state.set_state(LoginStates.waiting_for_username)
        await message.answer(text, reply_markup=keyboards.cancel_keyboard, parse_mode=ParseMode.HTML)


@dp.message(F.text == "❌ Bekor qilish")
@dp.message(Command("cancel"))
async def cancel_handler(message: types.Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    if auth_manager.is_authenticated(user_id):
        await message.answer("Amal bekor qilindi.", reply_markup=keyboards.admin_main_keyboard)
    else:
        await message.answer(
            "Amal bekor qilindi. Qayta kirish uchun «🔑 Tizimga kirish» tugmasini bosing.",
            reply_markup=keyboards.login_keyboard,
        )


@dp.message(F.text == "🔑 Tizimga kirish")
@dp.message(Command("login"))
async def login_command_handler(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if auth_manager.is_authenticated(user_id):
        await message.answer(
            "✅ Siz allaqachon tizimga kirgansiz!",
            reply_markup=keyboards.admin_main_keyboard,
        )
        return

    await state.set_state(LoginStates.waiting_for_username)
    await message.answer(
        "🔑 Iltimos, <b>Admin Logini</b>ni kiriting:",
        reply_markup=keyboards.cancel_keyboard,
        parse_mode=ParseMode.HTML,
    )


@dp.message(StateFilter(LoginStates.waiting_for_username))
async def process_username(message: types.Message, state: FSMContext):
    username_input = message.text.strip()
    await state.update_data(username=username_input)
    await state.set_state(LoginStates.waiting_for_password)
    await message.answer(
        "🔒 Endi <b>Admin Paroli</b>ni kiriting:",
        reply_markup=keyboards.cancel_keyboard,
        parse_mode=ParseMode.HTML,
    )


@dp.message(StateFilter(LoginStates.waiting_for_password))
async def process_password(message: types.Message, state: FSMContext):
    password_input = message.text.strip()
    user_data = await state.get_data()
    username_input = user_data.get("username", "")

    user_id = message.from_user.id
    tg_username = message.from_user.username or ""
    full_name = message.from_user.full_name or ""

    is_ok = auth_manager.authenticate(
        user_id=user_id,
        username=username_input,
        password=password_input,
        tg_username=tg_username,
        full_name=full_name,
    )

    await state.clear()

    if is_ok:
        text = (
            f"🎉 <b>Muvaffaqiyatli kirdingiz!</b>\n\n"
            f"Xush kelibsiz, <b>{full_name}</b>. Siz server administratori sifatida tasdiqlandingiz.\n\n"
            f"Endi bot orqali serverda istalgan amalni bajarishingiz mumkin:\n"
            f"• 💻 <b>Root Terminal:</b> <code>/sh &lt;komanda&gt;</code> orqali to'liq boshqaruv;\n"
            f"• 🚀 <b>Loyihalar Hubi:</b> PM2, Docker, Systemd bot/backend loyihalarni boshqarish;\n"
            f"• 🌐 <b>Tarmoq & Portlar:</b> Eshitilayotgan barcha ochiq portlarni ko'rish;\n"
            f"• 📜 <b>Loglar & Tozalash:</b> Loglarni ko'rish, fayl yuklash va kesh tozalash;\n"
            f"• 🟢 <b>Boot Alert:</b> Server o'chib yongan zahoti Telegramga darhol xabar kelishi."
        )
        await message.answer(text, reply_markup=keyboards.admin_main_keyboard, parse_mode=ParseMode.HTML)
    else:
        text = (
            f"❌ <b>Xatolik: Login yoki parol noto'g'ri!</b>\n\n"
            f"Iltimos, qaytadan urinib ko'ring.\n"
            f"Kirish uchun: /login"
        )
        await message.answer(text, reply_markup=keyboards.login_keyboard, parse_mode=ParseMode.HTML)


@dp.message(F.text == "🚪 Chiqish")
@dp.message(Command("logout"))
async def logout_handler(message: types.Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    if auth_manager.is_authenticated(user_id):
        auth_manager.logout(user_id)
        await message.answer(
            "🚪 <b>Siz tizimdan chiqdingiz.</b>\n"
            "Server ma'lumotlari va ogohlantirish xabarnomalari endi sizga yuborilmaydi.",
            reply_markup=keyboards.login_keyboard,
            parse_mode=ParseMode.HTML,
        )
    else:
        await message.answer("Siz tizimga kirmagansiz.", reply_markup=keyboards.login_keyboard)


# ==========================================
# TERMINAL VA ROOT BUYRUQLAR (TERMINAL & SHELL)
# ==========================================
@dp.message(F.text == "💻 Terminal & Shell")
@dp.message(Command("terminal"))
async def terminal_menu_handler(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if not auth_manager.is_authenticated(user_id):
        await message.answer("⛔️ Ruxsat etilmadi! Avval /login qiling.", reply_markup=keyboards.login_keyboard)
        return

    cwd = terminal_manager.get_user_cwd(user_id)
    await state.set_state(TerminalStates.in_terminal)

    text = (
        f"💻 <b>INTERAKTIV TERMINAL REJIMI (Root Shell)</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📁 <b>Joriy papka:</b> <code>{cwd}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Istalgan buyruqni to'g'ridan-to'g'ri yozib yuboring (masalan: <code>ls -la</code>, <code>docker ps</code>, <code>apt update</code>).\n\n"
        f"<i>Tezkor buyruqlardan foydalanish uchun quyidagi tugmalardan birini bosing:</i>\n"
        f"Chiqish uchun: <code>/exit</code> yoki pastdagi menyudan foydalaning."
    )
    await message.answer(text, reply_markup=keyboards.get_terminal_inline_keyboard(), parse_mode=ParseMode.HTML)


@dp.message(Command("sh", "cmd", "exec"))
async def terminal_command_handler(message: types.Message, state: FSMContext | None = None):
    """To'g'ridan-to'g'ri /sh <komanda> orqali buyruq bajarish."""
    user_id = message.from_user.id
    if not auth_manager.is_authenticated(user_id):
        await message.answer("⛔️ Ruxsat etilmadi! Avval /login qiling.", reply_markup=keyboards.login_keyboard)
        return

    # Komandani ajratamiz
    text_content = message.text or ""
    parts = text_content.split(maxsplit=1)
    if len(parts) < 2:
        cwd = terminal_manager.get_user_cwd(user_id)
        await message.answer(
            f"ℹ️ <b>Buyruq kiritilmadi!</b>\n"
            f"Foydalanish: <code>/sh &lt;buyruq&gt;</code>\n"
            f"Masalan: <code>/sh uptime</code> yoki <code>/sh cd /var/www && ls</code>\n"
            f"Joriy papka: <code>{cwd}</code>",
            parse_mode=ParseMode.HTML,
            reply_markup=keyboards.get_terminal_inline_keyboard(),
        )
        return

    cmd = parts[1]
    wait_msg = await message.answer("⏳ <i>Buyruq bajarilmoqda...</i>", parse_mode=ParseMode.HTML)

    resp_text, file_bytes, new_cwd = await terminal_manager.execute_command(cmd, user_id=user_id)

    try:
        await wait_msg.delete()
    except Exception:
        pass

    if file_bytes:
        doc = BufferedInputFile(file_bytes, filename=f"output_{int(datetime.now().timestamp())}.txt")
        await message.answer_document(doc, caption=resp_text, parse_mode=ParseMode.HTML)
    else:
        await message.answer(resp_text, parse_mode=ParseMode.HTML)


@dp.message(StateFilter(TerminalStates.in_terminal))
async def process_terminal_input(message: types.Message, state: FSMContext):
    """Terminal rejimida kiritilgan har bir xabarni buyruq sifatida bajarish."""
    user_id = message.from_user.id
    cmd = (message.text or "").strip()

    if cmd.lower() in ("/exit", "exit", "quit", "/cancel", "❌ bekor qilish"):
        await state.clear()
        await message.answer("🚪 Terminal rejimidan chiqildi.", reply_markup=keyboards.admin_main_keyboard)
        return

    # Asosiy menyu tugmalaridan biri bosilgan bo'lsa
    if cmd in ("📊 Server Statlari", "⚡️ Top Jarayonlar", "🚀 Loyihalar & Saytlar", "⚙️ Servislar & Docker", "🌐 Tarmoq & Portlar", "📜 Loglar & Tozalash", "🔔 Tizim Holati", "🚪 Chiqish"):
        await state.clear()
        # Marshrutlaymiz
        if cmd == "📊 Server Statlari":
            await server_stats_handler(message)
        elif cmd == "⚡️ Top Jarayonlar":
            await top_processes_handler(message)
        elif cmd == "🚀 Loyihalar & Saytlar":
            await projects_menu_handler(message)
        elif cmd == "⚙️ Servislar & Docker":
            await services_status_handler(message)
        elif cmd == "🌐 Tarmoq & Portlar":
            await network_ports_handler(message)
        elif cmd == "📜 Loglar & Tozalash":
            await logs_handler(message)
        elif cmd == "🔔 Tizim Holati":
            await status_handler(message)
        elif cmd == "🚪 Chiqish":
            await logout_handler(message, state)
        return

    resp_text, file_bytes, new_cwd = await terminal_manager.execute_command(cmd, user_id=user_id)

    if file_bytes:
        doc = BufferedInputFile(file_bytes, filename=f"output_{int(datetime.now().timestamp())}.txt")
        await message.answer_document(doc, caption=resp_text, parse_mode=ParseMode.HTML)
    else:
        await message.answer(resp_text, parse_mode=ParseMode.HTML)


# ==========================================
# LOYIHALAR VA JARAYONLAR (PROJECTS HUB)
# ==========================================
@dp.message(F.text == "🚀 Loyihalar & Saytlar")
@dp.message(Command("projects", "apps"))
async def projects_menu_handler(message: types.Message):
    user_id = message.from_user.id
    if not auth_manager.is_authenticated(user_id):
        await message.answer("⛔️ Ruxsat etilmadi! Avval /login qiling.", reply_markup=keyboards.login_keyboard)
        return

    projects = project_manager.scan_all_projects()
    text = format_projects_summary(projects)
    await message.answer(
        text,
        reply_markup=keyboards.get_projects_inline_keyboard(projects),
        parse_mode=ParseMode.HTML,
    )


# ==========================================
# TARMOQ VA OCHIQ PORTLAR (NETWORK & PORTS)
# ==========================================
@dp.message(F.text == "🌐 Tarmoq & Portlar")
@dp.message(Command("ports", "network"))
async def network_ports_handler(message: types.Message):
    user_id = message.from_user.id
    if not auth_manager.is_authenticated(user_id):
        await message.answer("⛔️ Ruxsat etilmadi! Avval /login qiling.", reply_markup=keyboards.login_keyboard)
        return

    text = network_manager.format_listening_ports()
    await message.answer(text, reply_markup=keyboards.get_network_inline_keyboard(), parse_mode=ParseMode.HTML)


# ==========================================
# FAYL YUKLAB OLISH VA TAIL
# ==========================================
@dp.message(Command("getfile"))
async def getfile_command_handler(message: types.Message):
    """Serverdan istalgan faylni Telegram orqali yuklab olish: /getfile <path>"""
    user_id = message.from_user.id
    if not auth_manager.is_authenticated(user_id):
        await message.answer("⛔️ Ruxsat etilmadi!")
        return

    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        await message.answer(
            "ℹ️ <b>Foydalanish:</b> <code>/getfile &lt;fayl_yo'li&gt;</code>\n"
            "Masalan: <code>/getfile /var/log/nginx/error.log</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    fpath = parts[1].strip()
    ok, msg, data, filename = file_manager.prepare_file_for_download(fpath)

    if not ok:
        await message.answer(msg, parse_mode=ParseMode.HTML)
        return

    doc = BufferedInputFile(data, filename=filename)
    await message.answer_document(doc, caption=f"📄 Fayl: <code>{fpath}</code>", parse_mode=ParseMode.HTML)


@dp.message(Command("tail"))
async def tail_command_handler(message: types.Message):
    """Faylning oxirgi qatorlarini o'qish: /tail <path> [lines]"""
    user_id = message.from_user.id
    if not auth_manager.is_authenticated(user_id):
        await message.answer("⛔️ Ruxsat etilmadi!")
        return

    parts = (message.text or "").split()
    if len(parts) < 2:
        await message.answer(
            "ℹ️ <b>Foydalanish:</b> <code>/tail &lt;fayl_yo'li&gt; [qatorlar_soni]</code>\n"
            "Masalan: <code>/tail /var/log/syslog 50</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    fpath = parts[1]
    lines_count = 40
    if len(parts) >= 3 and parts[2].isdigit():
        lines_count = min(max(1, int(parts[2])), 200)

    ok, content = file_manager.tail_file(fpath, lines=lines_count)
    if not ok:
        await message.answer(content, parse_mode=ParseMode.HTML)
        return

    if len(content) > 3800:
        content = content[-3800:]

    escaped_content = html.escape(content)
    text = (
        f"📜 <b>FAYL LOGLARI:</b> <code>{html.escape(fpath)}</code> (oxirgi {lines_count} qator)\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"<pre>{escaped_content}</pre>"
    )
    await message.answer(text, parse_mode=ParseMode.HTML)


# ==========================================
# ASOSIY MONITORING VA STATISTIKA HANDLERLARI
# ==========================================
@dp.message(F.text == "📊 Server Statlari")
@dp.message(Command("stats"))
async def server_stats_handler(message: types.Message):
    user_id = message.from_user.id
    if not auth_manager.is_authenticated(user_id):
        await message.answer(
            "⛔️ <b>Ruxsat etilmadi!</b>\nServer ma'lumotlarini ko'rish uchun avval /login orqali tizimga kiring.",
            parse_mode=ParseMode.HTML,
            reply_markup=keyboards.login_keyboard,
        )
        return

    text = format_server_stats()
    await message.answer(text, reply_markup=keyboards.get_stats_inline_keyboard(), parse_mode=ParseMode.HTML)


@dp.message(F.text == "⚡️ Top Jarayonlar")
@dp.message(Command("top"))
async def top_processes_handler(message: types.Message):
    user_id = message.from_user.id
    if not auth_manager.is_authenticated(user_id):
        await message.answer("⛔️ Ruxsat etilmadi! Avval /login qiling.", reply_markup=keyboards.login_keyboard)
        return

    text = format_top_processes()
    await message.answer(text, reply_markup=keyboards.get_top_inline_keyboard(), parse_mode=ParseMode.HTML)


@dp.message(F.text == "⚙️ Servislar & Docker")
@dp.message(Command("services"))
async def services_status_handler(message: types.Message):
    user_id = message.from_user.id
    if not auth_manager.is_authenticated(user_id):
        await message.answer("⛔️ Ruxsat etilmadi! Avval /login qiling.", reply_markup=keyboards.login_keyboard)
        return

    text = format_services_status()
    await message.answer(text, reply_markup=keyboards.get_services_inline_keyboard(), parse_mode=ParseMode.HTML)


@dp.message(F.text.in_(["📜 Muhim Loglar", "📜 Oxirgi Loglar", "📜 Loglar & Tozalash"]))
@dp.message(Command("logs"))
async def logs_handler(message: types.Message):
    user_id = message.from_user.id
    if not auth_manager.is_authenticated(user_id):
        await message.answer("⛔️ Ruxsat etilmadi! Avval /login qiling.", reply_markup=keyboards.login_keyboard)
        return

    categorized_logs = server_monitor.get_recent_categorized_logs(category="all", limit=10)
    text = (
        f"📜 <b>SERVERNING SO'NGGI MUHIM HARAKATLARI VA LOGLARI:</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{categorized_logs}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"<i>Kategoriyalar bo'yicha saralash yoki keshni tozalash uchun tugmalardan foydalaning:</i>"
    )
    await message.answer(text, reply_markup=keyboards.get_logs_inline_keyboard(active_cat="all"), parse_mode=ParseMode.HTML)


@dp.message(F.text == "🔔 Tizim Holati")
@dp.message(Command("status"))
async def status_handler(message: types.Message):
    user_id = message.from_user.id
    if not auth_manager.is_authenticated(user_id):
        await message.answer("⛔️ Ruxsat etilmadi! Avval /login qiling.", reply_markup=keyboards.login_keyboard)
        return

    text = format_monitoring_status()
    await message.answer(text, parse_mode=ParseMode.HTML)


@dp.message(Command("test_alert"))
async def test_alert_command(message: types.Message):
    """Admin alert tizimini tekshirishi uchun test xabarlar menyusi."""
    user_id = message.from_user.id
    if not auth_manager.is_authenticated(user_id):
        await message.answer("⛔️ Ruxsat etilmadi!")
        return

    await message.answer(
        "🧪 <b>Qaysi turdagi server harakatini sinab ko'rmoqchisiz?</b>\n\n"
        "Quyidagi tugmalardan birini tanlang, bot test hodisasini hosil qiladi va fon tekshiruvi uni darhol aniqlab sizga ALERT yuboradi:",
        reply_markup=keyboards.get_test_actions_keyboard(),
        parse_mode=ParseMode.HTML,
    )


# ==========================================
# INLINE CALLBACK HANDLERLARI
# ==========================================
@dp.callback_query(F.data == "refresh_stats")
async def callback_refresh_stats(callback: types.CallbackQuery):
    if not auth_manager.is_authenticated(callback.from_user.id):
        await callback.answer("⛔️ Ruxsat yo'q!", show_alert=True)
        return

    new_text = format_server_stats()
    try:
        await callback.message.edit_text(
            new_text,
            reply_markup=keyboards.get_stats_inline_keyboard(),
            parse_mode=ParseMode.HTML,
        )
        await callback.answer("✅ Yangilandi!")
    except Exception:
        await callback.answer("ℹ️ O'zgarish yo'q.")


@dp.callback_query(F.data == "show_stats")
async def callback_show_stats(callback: types.CallbackQuery):
    if not auth_manager.is_authenticated(callback.from_user.id):
        await callback.answer("⛔️ Ruxsat yo'q!", show_alert=True)
        return

    text = format_server_stats()
    try:
        await callback.message.edit_text(
            text,
            reply_markup=keyboards.get_stats_inline_keyboard(),
            parse_mode=ParseMode.HTML,
        )
        await callback.answer()
    except Exception:
        await callback.answer()


@dp.callback_query(F.data.in_(["refresh_top", "show_top"]))
async def callback_top(callback: types.CallbackQuery):
    if not auth_manager.is_authenticated(callback.from_user.id):
        await callback.answer("⛔️ Ruxsat yo'q!", show_alert=True)
        return

    text = format_top_processes()
    try:
        await callback.message.edit_text(
            text,
            reply_markup=keyboards.get_top_inline_keyboard(),
            parse_mode=ParseMode.HTML,
        )
        await callback.answer("✅ Yangilandi!")
    except Exception:
        await callback.answer()


@dp.callback_query(F.data.in_(["refresh_services", "show_services"]))
async def callback_services(callback: types.CallbackQuery):
    if not auth_manager.is_authenticated(callback.from_user.id):
        await callback.answer("⛔️ Ruxsat yo'q!", show_alert=True)
        return

    text = format_services_status()
    try:
        await callback.message.edit_text(
            text,
            reply_markup=keyboards.get_services_inline_keyboard(),
            parse_mode=ParseMode.HTML,
        )
        await callback.answer("✅ Yangilandi!")
    except Exception:
        await callback.answer()


# Loyihalar callbacklari
@dp.callback_query(F.data == "menu_projects")
async def callback_menu_projects(callback: types.CallbackQuery):
    if not auth_manager.is_authenticated(callback.from_user.id):
        await callback.answer("⛔️ Ruxsat yo'q!", show_alert=True)
        return

    projects = project_manager.scan_all_projects()
    text = format_projects_summary(projects)
    try:
        await callback.message.edit_text(
            text,
            reply_markup=keyboards.get_projects_inline_keyboard(projects),
            parse_mode=ParseMode.HTML,
        )
        await callback.answer("✅ Loyihalar yangilandi!")
    except Exception:
        await callback.answer()


@dp.callback_query(F.data.startswith("proj_menu:"))
async def callback_proj_menu(callback: types.CallbackQuery):
    if not auth_manager.is_authenticated(callback.from_user.id):
        await callback.answer("⛔️ Ruxsat yo'q!", show_alert=True)
        return

    parts = callback.data.split(":")
    if len(parts) >= 3:
        proj_type = parts[1]
        proj_id = parts[2]
        text = (
            f"🚀 <b>LOYIHA BOSHQARUVI:</b> <code>{proj_id}</code>\n"
            f"⚙️ <b>Turi:</b> <code>{proj_type.upper()}</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"Quyidagi amallardan birini tanlang:"
        )
        await callback.message.edit_text(
            text,
            reply_markup=keyboards.get_project_action_keyboard(proj_type, proj_id),
            parse_mode=ParseMode.HTML,
        )
    await callback.answer()


@dp.callback_query(F.data.startswith("p_act:"))
async def callback_proj_act(callback: types.CallbackQuery):
    if not auth_manager.is_authenticated(callback.from_user.id):
        await callback.answer("⛔️ Ruxsat yo'q!", show_alert=True)
        return

    parts = callback.data.split(":")
    if len(parts) >= 4:
        action = parts[1]
        proj_type = parts[2]
        proj_id = parts[3]

        await callback.answer(f"⏳ {action.upper()} bajarilmoqda...")
        ok, res_msg = await project_manager.control_project(proj_type, proj_id, action)

        text = (
            f"{res_msg}\n\n"
            f"🚀 <b>Loyiha:</b> <code>{proj_id}</code> ({proj_type.upper()})"
        )
        await callback.message.edit_text(
            text,
            reply_markup=keyboards.get_project_action_keyboard(proj_type, proj_id),
            parse_mode=ParseMode.HTML,
        )


@dp.callback_query(F.data.startswith("p_logs:"))
async def callback_proj_logs(callback: types.CallbackQuery):
    if not auth_manager.is_authenticated(callback.from_user.id):
        await callback.answer("⛔️ Ruxsat yo'q!", show_alert=True)
        return

    parts = callback.data.split(":")
    if len(parts) >= 3:
        proj_type = parts[1]
        proj_id = parts[2]

        await callback.answer("⏳ Loglar olinmoqda...")
        logs = await project_manager.get_project_logs(proj_type, proj_id, lines=30)
        escaped_logs = html.escape(logs)
        text = (
            f"📜 <b>OXIRGI LOGLAR:</b> <code>{html.escape(proj_id)}</code>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"<pre>{escaped_logs}</pre>"
        )
        await callback.message.edit_text(
            text,
            reply_markup=keyboards.get_project_action_keyboard(proj_type, proj_id),
            parse_mode=ParseMode.HTML,
        )


@dp.callback_query(F.data.startswith("proc_info:"))
async def callback_proc_info(callback: types.CallbackQuery):
    if not auth_manager.is_authenticated(callback.from_user.id):
        await callback.answer("⛔️ Ruxsat yo'q!", show_alert=True)
        return

    pid_str = callback.data.split(":")[1]
    text = (
        f"⚡️ <b>JARAYON MA'LUMOTI:</b> PID <code>{pid_str}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Ushbu jarayonni majburiy to'xtatish (Kill) ni xohlaysizmi?"
    )
    await callback.message.edit_text(
        text,
        reply_markup=keyboards.get_process_action_keyboard(pid_str),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("kill_pid:"))
async def callback_kill_pid(callback: types.CallbackQuery):
    if not auth_manager.is_authenticated(callback.from_user.id):
        await callback.answer("⛔️ Ruxsat yo'q!", show_alert=True)
        return

    pid_str = callback.data.split(":")[1]
    try:
        pid = int(pid_str)
        ok, msg = await project_manager.kill_process_by_pid(pid)
        await callback.answer("✅ Bajarildi!", show_alert=True)
        await callback.message.edit_text(
            f"{msg}\n\nLoyihalar ro'yxatiga qaytish uchun tugmani bosing:",
            reply_markup=keyboards.get_projects_inline_keyboard(project_manager.scan_all_projects()),
            parse_mode=ParseMode.HTML,
        )
    except Exception as e:
        await callback.answer(f"Xato: {e}", show_alert=True)


# Terminal tezkor buyruqlari
@dp.callback_query(F.data.startswith("t_run:"))
async def callback_terminal_quick_run(callback: types.CallbackQuery):
    if not auth_manager.is_authenticated(callback.from_user.id):
        await callback.answer("⛔️ Ruxsat yo'q!", show_alert=True)
        return

    cmd = callback.data.replace("t_run:", "")
    await callback.answer(f"⏳ «{cmd}» bajarilmoqda...")

    resp_text, file_bytes, new_cwd = await terminal_manager.execute_command(cmd, user_id=callback.from_user.id)

    if file_bytes:
        doc = BufferedInputFile(file_bytes, filename=f"output_{int(datetime.now().timestamp())}.txt")
        await callback.message.answer_document(doc, caption=resp_text, parse_mode=ParseMode.HTML)
    else:
        await callback.message.answer(
            resp_text,
            reply_markup=keyboards.get_terminal_inline_keyboard(),
            parse_mode=ParseMode.HTML,
        )


@dp.callback_query(F.data == "t_reset_cwd")
async def callback_reset_cwd(callback: types.CallbackQuery):
    if not auth_manager.is_authenticated(callback.from_user.id):
        await callback.answer("⛔️ Ruxsat yo'q!", show_alert=True)
        return

    terminal_manager.reset_user_cwd(callback.from_user.id)
    await callback.answer("✅ Ishchi papka boshlang'ich holatga qaytarildi!", show_alert=True)


@dp.callback_query(F.data == "menu_network")
async def callback_menu_network(callback: types.CallbackQuery):
    if not auth_manager.is_authenticated(callback.from_user.id):
        await callback.answer("⛔️ Ruxsat yo'q!", show_alert=True)
        return

    text = network_manager.format_listening_ports()
    try:
        await callback.message.edit_text(
            text,
            reply_markup=keyboards.get_network_inline_keyboard(),
            parse_mode=ParseMode.HTML,
        )
        await callback.answer("✅ Yangilandi!")
    except Exception:
        await callback.answer()


@dp.callback_query(F.data == "menu_clean_cache")
async def callback_menu_clean_cache(callback: types.CallbackQuery):
    if not auth_manager.is_authenticated(callback.from_user.id):
        await callback.answer("⛔️ Ruxsat yo'q!", show_alert=True)
        return

    text = (
        f"🧹 <b>SERVER KESHINI TOZALASH</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Quyidagi amallar bajariladi:\n"
        f"• <code>journalctl --vacuum-time=2d</code> (2 kundan eski loglarni o'chirish);\n"
        f"• <code>apt-get clean</code> (Yuklangan paketlar keshini tozalash);\n"
        f"• <code>docker system prune -f</code> (Ishlatilmayotgan Docker keshini tozalash);\n\n"
        f"<b>Davom ettirishni tasdiqlaysizmi?</b>"
    )
    await callback.message.edit_text(
        text,
        reply_markup=keyboards.get_clean_confirm_keyboard(),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()


@dp.callback_query(F.data == "confirm_clean_cache")
async def callback_confirm_clean_cache(callback: types.CallbackQuery):
    if not auth_manager.is_authenticated(callback.from_user.id):
        await callback.answer("⛔️ Ruxsat yo'q!", show_alert=True)
        return

    await callback.answer("⏳ Tozalanmoqda...")
    res = await file_manager.clean_system_cache()
    await callback.message.edit_text(
        res["details"],
        reply_markup=keyboards.get_logs_inline_keyboard(active_cat="all"),
        parse_mode=ParseMode.HTML,
    )


# Docker menyusi
@dp.callback_query(F.data == "menu_docker")
async def callback_menu_docker(callback: types.CallbackQuery):
    if not auth_manager.is_authenticated(callback.from_user.id):
        await callback.answer("⛔️ Ruxsat yo'q!", show_alert=True)
        return

    containers = await docker_manager.get_containers_summary()
    if not containers:
        await callback.answer("Docker konteynerlar topilmadi yoki Docker o'rnatilmagan.", show_alert=True)
        return

    lines = ["🐳 <b>DOCKER KONTEYNERLARI HOLATI:</b>", "━━━━━━━━━━━━━━━━━━━━"]
    buttons = []
    for c in containers:
        c_icon = "🟢" if c["is_running"] else "⚪️"
        lines.append(f"{c_icon} <b>{c['name']}</b>: <code>{c['state']}</code> ({c['image'][:20]})")
        buttons.append([
            InlineKeyboardButton(text=f"🔄 {c['name'][:15]}", callback_data=f"p_act:restart:docker:{c['name']}"),
            InlineKeyboardButton(text="📜 Log", callback_data=f"p_logs:docker:{c['name']}"),
        ])

    buttons.append([InlineKeyboardButton(text="⬅️ Servislarga qaytish", callback_data="show_services")])

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode=ParseMode.HTML,
    )
    await callback.answer()


# Loglar filtrlash (Kategoriyalar bo'yicha)
@dp.callback_query(F.data.startswith("log_filter_"))
async def callback_log_filter(callback: types.CallbackQuery):
    if not auth_manager.is_authenticated(callback.from_user.id):
        await callback.answer("⛔️ Ruxsat yo'q!", show_alert=True)
        return

    category = callback.data.replace("log_filter_", "")
    cat_names = {
        "all": "Barcha Harakatlar",
        "security": "Xavfsizlik & Loginlar",
        "service": "Servislar Amallari",
        "error": "Xatoliklar (Errors)",
        "warning": "Ogohlantirishlar (Warnings)",
        "action": "Muhim Operatsiyalar",
    }
    cat_title = cat_names.get(category, category.upper())

    categorized_logs = server_monitor.get_recent_categorized_logs(category=category, limit=10)
    text = (
        f"📜 <b>LOGLAR: {cat_title.upper()}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{categorized_logs}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"<i>Kategoriya bo'yicha tanlang:</i>"
    )

    try:
        await callback.message.edit_text(
            text,
            reply_markup=keyboards.get_logs_inline_keyboard(active_cat=category),
            parse_mode=ParseMode.HTML,
        )
        await callback.answer("✅ Yangilandi!")
    except Exception:
        await callback.answer()


# Test amallari menyusi
@dp.callback_query(F.data == "menu_test_actions")
async def callback_menu_test_actions(callback: types.CallbackQuery):
    if not auth_manager.is_authenticated(callback.from_user.id):
        await callback.answer("⛔️ Ruxsat yo'q!", show_alert=True)
        return

    text = (
        "🧪 <b>TEST HARAKATLARINI TANLANG:</b>\n\n"
        "Qaysi hodisani sinab ko'rmoqchisiz? Tugmani bossangiz, sun'iy test harakati yoziladi va bot uni zudlik bilan aniqlab ALERT yuboradi:"
    )
    try:
        await callback.message.edit_text(
            text,
            reply_markup=keyboards.get_test_actions_keyboard(),
            parse_mode=ParseMode.HTML,
        )
        await callback.answer()
    except Exception:
        await callback.answer()


# Har bir turdagi test hodisasi
@dp.callback_query(F.data.startswith("test_act_"))
async def callback_trigger_test_act(callback: types.CallbackQuery):
    if not auth_manager.is_authenticated(callback.from_user.id):
        await callback.answer("⛔️ Ruxsat yo'q!", show_alert=True)
        return

    act_type = callback.data.replace("test_act_", "")
    user_name = callback.from_user.full_name

    custom_msgs = {
        "security": f"sshd[7712]: Failed password for root from 192.168.1.199 port 54312 ssh2 (Test: {user_name})",
        "ssh_ok": f"sshd[7715]: Accepted publickey for admin from 192.168.1.50 port 51234 ssh2 (Test: {user_name})",
        "sudo": f"sudo: {user_name} : TTY=pts/1 ; COMMAND=/usr/bin/systemctl restart nginx",
        "service": f"systemd[1]: Started Nginx HTTP and reverse proxy server. (Test by {user_name})",
        "error": f"[ERROR] [BackendApp] DatabaseConnectionError: Failed to connect to MySQL database socket. (Test: {user_name})",
        "action": f"[DEPLOY] Version v4.0.0 successfully deployed by admin ({user_name}).",
    }

    msg = custom_msgs.get(act_type, f"Test action: {act_type} by {user_name}")
    server_monitor.append_test_activity_log(category=act_type, custom_message=msg)

    await callback.answer(f"🧪 Test hodisasi yozildi! Yaqin soniyalarda ALERT keladi.", show_alert=True)


# ==========================================
# ASOSIY ISHGA TUSHIRISH (MAIN)
# ==========================================
async def main():
    if not config.BOT_TOKEN:
        logger.error("BOT_TOKEN ko'rsatilmagan! Iltimos, .env fayliga bot tokeningizni kiriting.")
        print("\n[XATOLIK] BOT_TOKEN topilmadi! .env fayliga BOT_TOKEN=... ni kiriting.\n")
        return

    bot = Bot(token=config.BOT_TOKEN)

    # Server monitoring fon jarayonini ishga tushiramiz (Boot Notifier va Alertlar)
    monitor_task = asyncio.create_task(background_tasks.start_server_monitoring(bot))

    try:
        logger.info("SysAdmin & DevOps Master Tool Boti ishga tushmoqda...")
        await dp.start_polling(bot)
    finally:
        monitor_task.cancel()
        await bot.session.close()
        logger.info("Bot to'xtatildi.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot to'xtatildi.")

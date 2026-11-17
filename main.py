import asyncio
import logging
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import Bot, Dispatcher, F, types
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

import auth_manager
import background_tasks
import config
import keyboards
import server_monitor

# Loglarni sozlash
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


# FSM Holatlari: Login va Parol kiritish jarayoni uchun
class LoginStates(StatesGroup):
    waiting_for_username = State()
    waiting_for_password = State()


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
        f"🔔 <b>MONITORING VA XAVFSIZLIK TIZIMI HOLATI</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🟢 <b>Monitoring holati:</b> <code>FAOL (Ishlamoqda)</code>\n"
        f"⏱ <b>Tekshirish davriyligi:</b> har <code>{config.CHECK_INTERVAL}</code> soniyada\n"
        f"🔍 <b>Journalctl monitoringi:</b> <code>{'Yoqilgan' if config.ENABLE_JOURNALCTL else 'O‘chirilgan'}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🚨 <b>Kuzatilayotgan harakatlar kategoriyalari:</b>\n"
        f"{categories_str}\n\n"
        f"⚙️ <b>Kuzatilayotgan servislar ({len(config.MONITORED_SERVICES)} ta):</b>\n"
        f"{services_str}\n\n"
        f"📜 <b>Kuzatilayotgan log fayllar:</b>\n"
        f"{logs_str}\n\n"
        f"📈 <b>Alert chegaralari:</b>\n"
        f"   └ CPU: <code>{config.CPU_THRESHOLD}%</code> | RAM: <code>{config.RAM_THRESHOLD}%</code> | Disk: <code>{config.DISK_THRESHOLD}%</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 <b>Ogohlantirish oluvchi faol adminlar ({len(admins)} ta):</b>\n"
        f"{admins_str}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🕒 <i>Hozirgi vaqt: {now_str}</i>"
    )
    return text


# ==========================================
# START VA AUTENTIFIKATSIYA (LOGIN) HANDLERLARI
# ==========================================
@dp.message(CommandStart())
async def command_start_handler(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    full_name = message.from_user.full_name

    if auth_manager.is_authenticated(user_id):
        text = (
            f"Assalomu alaykum, hurmatli <b>{full_name}</b>!\n\n"
            f"✅ Siz server administratori sifatida tizimdasiz.\n"
            f"Server holati, servislar, barcha server harakatlari va xatoliklarni quyidagi tugmalar orqali boshqarishingiz mumkin:"
        )
        await message.answer(text, reply_markup=keyboards.admin_main_keyboard, parse_mode=ParseMode.HTML)
    else:
        text = (
            f"Salom, <b>{full_name}</b>!\n\n"
            f"🔒 <b>Tizim himoyalangan!</b>\n"
            f"Ushbu bot server monitoringi, barcha muhim server harakatlari (SSH, Sudo, Servislar) va xatoliklarni kuzatuvchi maxsus botdir.\n\n"
            f"Ma'lumotlarni ko'rish va xabarnomalarni olish uchun, iltimos, <b>Admin Logini</b>ni kiriting:"
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
            f"Endi serverdagi barcha muhim harakatlar bo'yicha ogohlantirish olasiz:\n"
            f"• 🔐 <b>SSH & Xavfsizlik:</b> Kimdir SSH orqali kirsa yoki noto'g'ri parol tersa;\n"
            f"• 👤 <b>Sudo Amallari:</b> Serverda kimdir <code>sudo</code> buyrug'ini ishlatsa;\n"
            f"• ⚙️ <b>Servislar:</b> Servislar ishga tushsa, to'xtasa yoki o'chib qolsa;\n"
            f"• 🔴 <b>Xatoliklar:</b> Tizim va dastur loglarida xato (ERROR/CRITICAL) yuz bersa;\n"
            f"• 💀 <b>Resurslar:</b> CPU/RAM to'lsa yoki OOM-killer jarayonni o'ldirsa.\n\n"
            f"Boshqaruv uchun quyidagi menyudan foydalaning:"
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
async def logout_handler(message: types.Message):
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


@dp.message(F.text == "⚙️ Servislar Holati")
@dp.message(Command("services"))
async def services_status_handler(message: types.Message):
    user_id = message.from_user.id
    if not auth_manager.is_authenticated(user_id):
        await message.answer("⛔️ Ruxsat etilmadi! Avval /login qiling.", reply_markup=keyboards.login_keyboard)
        return

    text = format_services_status()
    await message.answer(text, reply_markup=keyboards.get_services_inline_keyboard(), parse_mode=ParseMode.HTML)


@dp.message(F.text.in_(["📜 Muhim Loglar", "📜 Oxirgi Loglar"]))
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
        f"<i>Kategoriyalar bo'yicha saralash uchun quyidagi tugmalardan foydalaning:</i>"
    )
    await message.answer(text, reply_markup=keyboards.get_logs_inline_keyboard(active_cat="all"), parse_mode=ParseMode.HTML)


@dp.message(F.text == "🔔 Monitoring Holati")
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
# INLINE CALLBACK HANDLERLARI (DINAMIK YANGILASH)
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

    # Server monitoring fon jarayonini ishga tushiramiz
    monitor_task = asyncio.create_task(background_tasks.start_server_monitoring(bot))

    try:
        logger.info("Ko'p funksiyali Server Monitoring Boti ishga tushmoqda...")
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

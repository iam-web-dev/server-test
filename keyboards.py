from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove

# Asosiy admin boshqaruv paneli (Reply Keyboard)
admin_main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📊 Server Statlari"), KeyboardButton(text="⚡️ Top Jarayonlar")],
        [KeyboardButton(text="🚀 Loyihalar & Saytlar"), KeyboardButton(text="💻 Terminal & Shell")],
        [KeyboardButton(text="⚙️ Servislar & Docker"), KeyboardButton(text="🌐 Tarmoq & Portlar")],
        [KeyboardButton(text="📜 Loglar & Tozalash"), KeyboardButton(text="🔔 Tizim Holati")],
        [KeyboardButton(text="🚪 Chiqish")],
    ],
    resize_keyboard=True,
    is_persistent=True,
)

# Kirish va bekor qilish klaviaturalari
login_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="🔑 Tizimga kirish")]],
    resize_keyboard=True,
)

cancel_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="❌ Bekor qilish")]],
    resize_keyboard=True,
)

remove_keyboard = ReplyKeyboardRemove()


# Inline klaviaturalar (dinamik yangilanish uchun)
def get_stats_inline_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔄 Yangilash", callback_data="refresh_stats"),
                InlineKeyboardButton(text="⚡️ Top Jarayonlar", callback_data="show_top"),
            ],
            [
                InlineKeyboardButton(text="🚀 Loyihalar", callback_data="menu_projects"),
                InlineKeyboardButton(text="💻 Terminal", callback_data="menu_terminal"),
            ],
            [
                InlineKeyboardButton(text="🌐 Portlar", callback_data="menu_network"),
                InlineKeyboardButton(text="📜 Loglar", callback_data="log_filter_all"),
            ],
        ]
    )


def get_services_inline_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔄 Qayta tekshirish", callback_data="refresh_services"),
                InlineKeyboardButton(text="🐳 Docker Konteynerlar", callback_data="menu_docker"),
            ],
            [
                InlineKeyboardButton(text="📊 Server Statlari", callback_data="show_stats"),
            ],
        ]
    )


def get_top_inline_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔄 Yangilash", callback_data="refresh_top"),
                InlineKeyboardButton(text="📊 Server Statlari", callback_data="show_stats"),
            ]
        ]
    )


def get_logs_inline_keyboard(active_cat: str = "all") -> InlineKeyboardMarkup:
    """Kategoriyalar bo'yicha filtrlash imkoniyatiga ega loglar klaviaturasi."""
    mark = lambda cat, label: f"✅ {label}" if active_cat == cat else label

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=mark("all", "🔘 Barchasi"), callback_data="log_filter_all"),
                InlineKeyboardButton(text=mark("security", "🔐 Xavfsizlik"), callback_data="log_filter_security"),
            ],
            [
                InlineKeyboardButton(text=mark("service", "⚙️ Servislar"), callback_data="log_filter_service"),
                InlineKeyboardButton(text=mark("error", "🔴 Xatolar"), callback_data="log_filter_error"),
            ],
            [
                InlineKeyboardButton(text=mark("warning", "🟡 Ogohlantirish"), callback_data="log_filter_warning"),
                InlineKeyboardButton(text=mark("action", "📦 Amallar"), callback_data="log_filter_action"),
            ],
            [
                InlineKeyboardButton(text="🔄 Yangilash", callback_data=f"log_filter_{active_cat}"),
                InlineKeyboardButton(text="🧹 Tizimni Tozalash", callback_data="menu_clean_cache"),
            ],
            [
                InlineKeyboardButton(text="🧪 Test Harakat", callback_data="menu_test_actions"),
                InlineKeyboardButton(text="📊 Server Statlari", callback_data="show_stats"),
            ],
        ]
    )


def get_test_actions_keyboard() -> InlineKeyboardMarkup:
    """Turli xil server harakatlarini sinash uchun tugmalar."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🚨 Test: Muvaffaqiyatsiz Login", callback_data="test_act_security"),
                InlineKeyboardButton(text="🔐 Test: SSH Kirish", callback_data="test_act_ssh_ok"),
            ],
            [
                InlineKeyboardButton(text="👤 Test: Sudo Buyrug'i", callback_data="test_act_sudo"),
                InlineKeyboardButton(text="🟢 Test: Servis Ishga Tushdi", callback_data="test_act_service"),
            ],
            [
                InlineKeyboardButton(text="🔴 Test: Dastur Xatoligi", callback_data="test_act_error"),
                InlineKeyboardButton(text="📦 Test: Deploy / Amal", callback_data="test_act_action"),
            ],
            [
                InlineKeyboardButton(text="⬅️ Loglarga qaytish", callback_data="log_filter_all"),
            ],
        ]
    )


def get_projects_inline_keyboard(projects: dict) -> InlineKeyboardMarkup:
    """Serverdagi barcha loyihalar (Projects papkasi, Systemd, PM2, Docker, Jarayonlar) bo'yicha interaktiv tugmalar."""
    buttons = []

    # 1. Projects papkasidagi asosiy loyihalar (tg-manager, frontend, backend, va h.k.)
    for item in projects.get("apps", []):
        st = item.get("status", "").lower()
        status_icon = "🟢" if "active" in st or "running" in st else ("🔴" if "failed" in st else "⚪️")
        proj_type = item.get("type", "manage")
        buttons.append([
            InlineKeyboardButton(
                text=f"{status_icon} 🚀 {item['name']} ({item['type'].upper()})",
                callback_data=f"proj_menu:{proj_type}:{item['id']}",
            )
        ])

    # 2. PM2 ilovalar
    for item in projects.get("pm2", [])[:4]:
        status_icon = "🟢" if item.get("status") == "online" else "🔴"
        buttons.append([
            InlineKeyboardButton(
                text=f"{status_icon} [PM2] {item['name'][:18]}",
                callback_data=f"proj_menu:pm2:{item['id']}",
            )
        ])

    # 3. Docker konteynerlar
    for item in projects.get("docker", [])[:4]:
        status_icon = "🟢" if "running" in item.get("status", "").lower() or "up" in item.get("status", "").lower() else "⚪️"
        buttons.append([
            InlineKeyboardButton(
                text=f"{status_icon} [Docker] {item['name'][:18]}",
                callback_data=f"proj_menu:docker:{item['id']}",
            )
        ])

    # 4. Maxsus systemd servislari
    for item in projects.get("systemd", [])[:4]:
        # Agar bu servis allaqachon apps ro'yxatida bo'lsa, takrorlamaymiz
        if any(app['name'] == item['name'] for app in projects.get("apps", [])):
            continue
        status_icon = "🟢" if item.get("status") == "active" else "🔴"
        buttons.append([
            InlineKeyboardButton(
                text=f"{status_icon} [Systemd] {item['name'][:18]}",
                callback_data=f"proj_menu:systemd:{item['id']}",
            )
        ])

    # 5. Erkin yurgan alohida jarayonlar (backend, frontend, worker)
    for item in projects.get("processes", [])[:4]:
        buttons.append([
            InlineKeyboardButton(
                text=f"⚡️ {item['name'][:22]}",
                callback_data=f"proc_info:{item['id']}",
            )
        ])

    # Boshqaruv tugmalari
    buttons.append([
        InlineKeyboardButton(text="🔄 Qayta skanerlash", callback_data="menu_projects"),
        InlineKeyboardButton(text="📊 Server Statlari", callback_data="show_stats"),
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_project_action_keyboard(proj_type: str, proj_id: str) -> InlineKeyboardMarkup:
    """Tanlangan loyiha uchun Start/Stop/Restart/Status/Logs amallari."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔄 Restart", callback_data=f"p_act:restart:{proj_type}:{proj_id}"),
                InlineKeyboardButton(text="⏹ Stop", callback_data=f"p_act:stop:{proj_type}:{proj_id}"),
                InlineKeyboardButton(text="▶️ Start", callback_data=f"p_act:start:{proj_type}:{proj_id}"),
            ],
            [
                InlineKeyboardButton(text="📊 Holat (Status)", callback_data=f"p_act:status:{proj_type}:{proj_id}"),
                InlineKeyboardButton(text="📜 Oxirgi Loglar", callback_data=f"p_logs:{proj_type}:{proj_id}"),
            ],
            [
                InlineKeyboardButton(text="⬅️ Loyihalar ro'yxati", callback_data="menu_projects"),
            ],
        ]
    )


def get_process_action_keyboard(pid: str) -> InlineKeyboardMarkup:
    """Erkin jarayon uchun Kill tugmasi."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="💀 Jarayonni o'ldirish (Kill)", callback_data=f"kill_pid:{pid}"),
                InlineKeyboardButton(text="⬅️ Orqaga", callback_data="menu_projects"),
            ]
        ]
    )


def get_terminal_inline_keyboard() -> InlineKeyboardMarkup:
    """Terminal uchun tezkor qulay buyruqlar tugmalari."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="💾 df -h", callback_data="t_run:df -h"),
                InlineKeyboardButton(text="🧠 free -m", callback_data="t_run:free -m"),
                InlineKeyboardButton(text="⏱ uptime", callback_data="t_run:uptime"),
            ],
            [
                InlineKeyboardButton(text="🐳 docker ps", callback_data="t_run:docker ps"),
                InlineKeyboardButton(text="🚀 pm2 status", callback_data="t_run:pm2 status"),
                InlineKeyboardButton(text="🌐 ss -tulpn", callback_data="t_run:ss -tulpn"),
            ],
            [
                InlineKeyboardButton(text="👤 whoami & id", callback_data="t_run:whoami && id"),
                InlineKeyboardButton(text="📁 pwd & ls", callback_data="t_run:pwd && ls -la"),
            ],
            [
                InlineKeyboardButton(text="🔄 Papkani tiklash (~)", callback_data="t_reset_cwd"),
                InlineKeyboardButton(text="❌ Chiqish", callback_data="show_stats"),
            ],
        ]
    )


def get_network_inline_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔄 Yangilash", callback_data="menu_network"),
                InlineKeyboardButton(text="📊 Server Statlari", callback_data="show_stats"),
            ]
        ]
    )


def get_clean_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🧹 Tozalashni tasdiqlash", callback_data="confirm_clean_cache"),
                InlineKeyboardButton(text="❌ Bekor qilish", callback_data="log_filter_all"),
            ]
        ]
    )

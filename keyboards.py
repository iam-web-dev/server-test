from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove

# Asosiy admin boshqaruv paneli (Reply Keyboard)
admin_main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📊 Server Statlari"), KeyboardButton(text="⚡️ Top Jarayonlar")],
        [KeyboardButton(text="⚙️ Servislar Holati"), KeyboardButton(text="📜 Muhim Loglar")],
        [KeyboardButton(text="🔔 Monitoring Holati"), KeyboardButton(text="🚪 Chiqish")],
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
                InlineKeyboardButton(text="⚙️ Servislar", callback_data="show_services"),
                InlineKeyboardButton(text="📜 Muhim Loglar", callback_data="log_filter_all"),
            ],
        ]
    )


def get_services_inline_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔄 Qayta tekshirish", callback_data="refresh_services"),
                InlineKeyboardButton(text="📊 Server Statlari", callback_data="show_stats"),
            ]
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
                InlineKeyboardButton(text="🧪 Test Harakat Yuborish", callback_data="menu_test_actions"),
            ],
            [
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

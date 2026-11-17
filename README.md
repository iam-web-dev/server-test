# 🖥 Server Monitoring & Alert Telegram Boti (aiogram 3)

Ushbu bot Linux serveringiz holatini real vaqt rejimida monitoring qilish, server ko'rsatkichlarini (CPU, RAM, Disk, Uptime, Jarayonlar) ko'rish hamda serverda yuz beradigan **barcha muhim harakatlar, xavfsizlik hodisalari, servis amallari va xatoliklar** bo'yicha administratorga **avtomatik ogohlantirish (Alert)** yuborish uchun mo'ljallangan to'liq tizimdir.

---

## 🌟 Asosiy Imkoniyatlar

1. 🔒 **Xavfsiz Admin Autentifikatsiyasi (Login / Parol):**
   - Begona foydalanuvchilar server ma'lumotlarini ko'ra olmaydi.
   - Botga kirganda foydalanuvchidan `.env` da belgilangan **Admin Logini** va **Paroli** so'raladi (FSM orqali).
   - Tizimga muvaffaqiyatli kirgan adminlarning sessiyasi `data/admins.json` faylida xavfsiz saqlanadi (bot qayta yonganda ham saqlanib qoladi).
   - Istalgan vaqtda **«🚪 Chiqish»** (`/logout`) tugmasi orqali sessiyani tugatish mumkin.

2. 📊 **Server Statistikasi (Real-time Stats):**
   - **CPU**: Protsessor bandligi (%) va Load Average (1m, 5m, 15m).
   - **RAM**: Operativ xotira (Ishlatilgan / Jami MB, bandlik foizi).
   - **Disk**: Asosiy qattiq disk bo'sh joyi va bandligi (GB / %).
   - **Uptime**: Server qancha vaqtdan beri uzluksiz ishlab turgani.
   - **Tizim**: Operatsion tizim (OS), yadro versiyasi, arxitektura va xost nomi.
   - **Tarmoq (Network)**: Qabul qilingan (RX) va uzatilgan (TX) trafik hajmi (MB).
   - **«🔄 Yangilash»** inline tugmasi orqali xabarni joyida qayta yangilash.

3. ⚡️ **Top Jarayonlar (Top Processes):**
   - Serverda eng ko'p protsessor (CPU) va xotira (RAM) sarflayotgan top-7 jarayonlar ro'yxati (PID, CPU%, MEM%, Jarayon nomi).

4. ⚙️ **Servislar va Operatsiyalarni Kuzatish:**
   - Istalgan servislarni (masalan: `nginx`, `docker`, `postgresql`, `mysql`, `redis`, `ssh` yoki bot/ilova jarayoni) kuzatish.
   - Servis holatlarini tekshirish (`systemctl` va faol `process` darajasida).

5. 🚨 **Barcha Server Harakatlari va Muhim Loglar Monitoringi:**
   Bot faqatgina xatolarni emas, balki butun server hayotidagi **eng muhim hodisalarni** toifalarga ajratib kuzatadi:
   - 🔐 **Xavfsizlik va Kirish amallari (`security`):**
     - SSH orqali yangi kirishlar (`Accepted password`, `Accepted publickey`);
     - Noto'g'ri parol terish va buzib kirishga urinishlar (`Failed password`, `Invalid user`);
     - `sudo` orqali administrator buyruqlari bajarilishi (`sudo: COMMAND=...`);
     - Tizim sessiyalari ochilishi (`session opened for user ...`).
   - ⚙️ **Servislar hayoti (`service`):**
     - Servislar ishga tushishi (`Started ...`), to'xtatilishi (`Stopped ...`), qayta yuklanishi (`Restarting/Reloaded`), yoki qulashi (`Failed`).
   - 💀 **Tizim avariyalari (`system`):**
     - OOM-Killer: Xotira tugab biror jarayon majburiy o'ldirilsa (`Out of memory: Killed process`);
     - Server o'chirilishi yoki qayta yuklanishi (`reboot`, `shutdown`);
     - Yadro xatoliklari (`Kernel panic`).
   - 🔴 **Xatoliklar va Avariyalar (`error`):**
     - Dastur yoki tizim loglaridagi `ERROR`, `CRITICAL`, `FATAL`, `EXCEPTION`, `TRACEBACK`.
   - 🟡 **Ogohlantirishlar (`warning`):**
     - `WARNING`, `WARN`, `Permission denied`, `Connection refused`, `Timeout`.
   - 📦 **Muhim Operatsiyalar (`action`):**
     - Deploy, Backup, Git pull, yangi paketlar o'rnatilishi yoki yangilanishi (`Installed:`, `Upgraded:`).
   - 📌 **Maxsus kalit so'zlar (`CUSTOM_LOG_KEYWORDS`):**
     - O'zingiz belgilagan istalgan maxsus kalit so'zlar bo'yicha ogohlantirishlar.

---

## 🛠 O'rnatish va Sozlash

### 1. Virtual muhitni faollashtirish va paketlarni o'rnatish
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. `.env` Faylini Sozlash
```env
# Telegram Bot Token (@BotFather dan)
BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrSTUvwxYZ

# Admin kirish ma'lumotlari (Botga kirishda so'raladi)
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123

# Kuzatiladigan servislar (systemd servis yoki jarayon nomi, vergul bilan)
MONITORED_SERVICES=nginx,docker,postgresql,mysql,redis,ssh

# Monitoring tekshirish oralig'i (soniyalarda)
CHECK_INTERVAL=15

# Resurslar chegarasi (%)
CPU_THRESHOLD=85.0
RAM_THRESHOLD=90.0
DISK_THRESHOLD=90.0

# Kuzatiladigan log fayllar (vergul bilan ajratilgan)
WATCH_LOG_FILES=logs/server_activity.log,logs/server_errors.log

# Kuzatiladigan harakatlar toifalari:
# security, service, error, warning, system, action
WATCH_LOG_CATEGORIES=security,service,error,warning,system,action

# O'zingizga kerakli maxsus kalit so'zlar (ixtiyoriy)
CUSTOM_LOG_KEYWORDS=deploy,backup,restart,database,fail

# Tizim hodisalarini to'g'ridan-to'g'ri journalctl dan kuzatish
ENABLE_JOURNALCTL=true

# Bir xil loglar uchun spamga qarshi cheklov (soniya)
LOG_THROTTLE_SECONDS=60

# Vaqt mintaqasi
TIMEZONE=Asia/Tashkent
```

---

## 🚀 Botni Ishga Tushirish

```bash
python3 main.py
```

### Tizimga kirish:
1. Telegramda botingizga `/start` bosing.
2. Bot **Admin Logini**ni so'raydi (`admin`).
3. So'ngra **Admin Paroli**ni so'raydi (`admin123`).
4. To'g'ri kiritilgach, admin paneli ochiladi va siz serverdagi barcha hodisalar bo'yicha zudlik bilan ALERT olasiz.

---

## 🧪 Server Harakatlari va Alertlarni Sinash (Test)

Bot ichida `/test_alert` buyrug'ini yuboring yoki **«📜 Muhim Loglar»** bo'limidagi **«🧪 Test Harakat Yuborish»** tugmasini bosing:
- 🚨 **Test: Muvaffaqiyatsiz Login** (Brute-force urinishi);
- 🔐 **Test: SSH Kirish** (Yangi SSH sessiyasi);
- 👤 **Test: Sudo Buyrug'i** (Admin komandasi);
- 🟢 **Test: Servis Ishga Tushdi** (Nginx/Docker va h.k.);
- 🔴 **Test: Dastur Xatoligi** (Database xatosi);
- 📦 **Test: Deploy / Amal** (Versiya yangilanishi).

Tugmani bosganingizdan so'ng, botingiz bir necha soniya ichida ushbu hodisani ilg'ab, sizga avtomatik chiroyli formatda xabar yuboradi!

---

## 📁 Loyiha Strukturasi

```
Bots/
├── main.py              # Asosiy bot handlerlari va FSM kirish oqimi
├── server_monitor.py    # Linux stats, jarayonlar, servislar va Log tahlilchisi (Classifier)
├── background_tasks.py  # Orqa fonda doimiy kuzatuvchi va alert jo'natuvchi worker
├── auth_manager.py      # Adminlarni tekshirish va sessiyalarni saqlash
├── keyboards.py         # Reply va filtrli Inline klaviaturalar
├── config.py            # .env sozlamalarini boshqarish
├── requirements.txt     # Python kutubxonalari
├── .env                 # Maxfiy sozlamalar (Token, login, parol, toifalar)
├── data/
│   └── admins.json      # Tizimga kirgan adminlar bazasi
└── logs/
    ├── server_activity.log # Server harakatlari log fayli
    └── server_errors.log   # Xatoliklar log fayli
```

# 👑 Server SysAdmin & DevOps Master Tool Telegram Boti (aiogram 3)

Ushbu bot **Linux (Debian 13 Minimal / Ubuntu / CentOS)** serverlarini to'liq boshqarish, monitoring qilish hamda serverda administrator (Root) sifatida istalgan amallarni bajarish imkonini beruvchi professional **All-in-One Master Tool** tizimidir.

---

## 🌟 Asosiy Master Tool Imkoniyatlari

### 1. 💻 Root Terminal & Shell Boshqaruvi
- **Istalgan buyruqni bajarish:** `/sh <komanda>` (masalan: `/sh docker ps`, `/sh apt update`, `/sh git status`).
- **Interaktiv Terminal Rejimi:** «💻 Terminal & Shell» bo'limida to'g'ridan-to'g'ri terminal sessiyasiga kirib, buyruqlarni xabarlar orqali uzluksiz yuborish.
- **Aqlli CWD (Ishchi papka):** `cd /var/www` qilsangiz, bot ishchi papkani eslab qoladi va keyingi barcha buyruqlar o'sha papkada bajariladi (`/sh pwd && ls`).
- **Natijalarni avtomatik formatlash:** Natija 3800 belgidan oshib ketsa, bot Telegram xabari chegarasidan oshib xatolik bermaydi, balki natijani to'liq `.txt` hujjat qilib yuboradi.
- **Tezkor buyruqlar:** Tugmalar orqali `df -h`, `free -m`, `uptime`, `whoami`, `docker ps`, `pm2 status`, `ss -tulpn` larni bitta bosishda chiqarish.

### 2. 🚀 Loyihalar va Dasturlar Hubi (Project Manager)
Serverda ishlayotgan barcha mustaqil dasturlar avtomatik tarzda aniqlanadi:
- **PM2 Ilovalari:** Node.js, Frontend va Python jarayonlari (CPU, RAM, Status).
- **Docker Konteynerlari:** Barcha faol va to'xtatilgan konteynerlar (Image, State).
- **Systemd Loyihalari:** `/etc/systemd/system/` dagi maxsus ilova servislari.
- **Faol App Jarayonlari:** Python, Uvicorn, Gunicorn, Celery, Node va Telegram botlar.
- **Boshqaruv tugmalari:**
  - `[ 🔄 Restart ]` — Loyihani qayta ishga tushirish;
  - `[ ⏹ Stop ]` — Loyihani to'xtatish;
  - `[ ▶️ Start ]` — Loyihani ishga tushirish;
  - `[ 📜 Oxirgi Loglar ]` — Loyihaning so'nggi 30-40 qator loglarini ko'rish;
  - `[ 💀 Kill PID ]` — Katta resurs yeyotgan yoki qotib qolgan jarayonni majburiy to'xtatish.

### 3. 🟢 Debian 13 Minimal Autostart & Boot Alert
- **Server yonganda darhol xabar:** Server o'chib-yongan yoki qayta yuklangan zahoti (`/proc/sys/kernel/random/boot_id` orqali aniqlanadi), bot adminlarga zudlik bilan alert yuboradi:
  - 🖥 Xost nomi va OS versiyasi (Debian 13 Trixie);
  - 🌐 Serverning Public va Local IP manzillari;
  - ⏱ Uptime va yadro versiyasi;
  - 📊 Boshlang'ich RAM va Disk holati.
- **1-bosqichli Systemd o'rnatish:** `./install_service.sh` skripti orqali Debian 13 minimal serverida bitta buyruq bilan `systemd` servisi o'rnatiladi va avtomatik ishga tushadi (`Restart=always`).

### 4. 🌐 Tarmoq va Ochiq Portlar (Network & Ports)
- `/ports` yoki «🌐 Tarmoq & Portlar» bo'limi orqali serverda eshitilayotgan barcha portlarni (`ss -tulpn` / `netstat`) qulay jadval ko'rinishida ko'rish:
  - Port raqami (masalan: 80, 443, 8000, 3000, 5432, 22);
  - Protokol (TCP / UDP);
  - Qaysi jarayon (PID va Nomi) ushbu portni band qilganligi.

### 5. 📁 Fayl Yuklash va Tizim Keshini Tozalash
- **Faylni Telegramga yuklab olish:** `/getfile <path>` (masalan: `/getfile /var/log/nginx/error.log` yoki `/getfile /etc/hosts`).
- **Fayl loglarini ko'rish:** `/tail <path> [lines]` (masalan: `/tail /var/log/syslog 50`).
- **Kesh va Diskni Tozalash:** «📜 Loglar & Tozalash» bo'limida:
  - `journalctl --vacuum-time=2d` (eski tizim loglarini tozalash);
  - `apt-get clean` (paketlar keshini tozalash);
  - `docker system prune -f` (ishlatilmayotgan Docker resurslarini tozalash);
  - Bo'shagan disk maydoni hisoboti.

### 6. 📊 Real-time Monitoring va Alertlar
- CPU (bandlik va Load Average: 1m, 5m, 15m).
- RAM (Ishlatilgan / Jami MB, bandlik foizi).
- Disk (Bo'sh joy va bandlik GB / %).
- Uptime va Tarmoq trafigi (RX / TX).
- Avtomatik xavfsizlik va tizim alertlari:
  - SSH orqali kirishlar va muvaffaqiyatsiz urinishlar (Brute-force);
  - `sudo` administrator buyruqlari;
  - Resurslar to'lishi (CPU/RAM/Disk threshold) va OOM-Killer.

---

## 🛠 O'rnatish va Ishga Tushirish

### 1. Paketlarni o'rnatish
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. `.env` faylini sozlash
`.env` faylida Telegram bot tokeni va admin login/parolini belgilang:
```env
BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrSTUvwxYZ
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
TIMEZONE=Asia/Tashkent
```

### 3. Debian 13 Minimal da Autostart O'rnatish (Tavsiya etiladi)
Server yoqilishi bilan botning o'zi avtomatik ishlab ketishi va har safar xabar berishi uchun:
```bash
sudo chmod +x install_service.sh
sudo ./install_service.sh
```
Holatni tekshirish:
```bash
systemctl status server-master-bot
```

### 4. Qo'lda (Manual) ishga tushirish
```bash
python3 main.py
```

---

## 🧪 Testlarni Ishga Tushirish (Unit & E2E)
Barcha 29 ta testni (terminal, loyihalar, boot alert, tarmoq, fayllar, klaviaturalar) tekshirish:
```bash
.venv/bin/python -m unittest discover tests
```

---

## 📁 Yangilangan Loyiha Strukturasi

```
Bots/
├── main.py                   # Asosiy bot handlerlari va FSM marshrutlash
├── terminal_manager.py       # Root terminal komandalari, CWD tracking, chiqishni formatlash
├── project_manager.py        # Backend, frontend, botlar (PM2, Docker, Systemd) boshqaruvi
├── boot_notifier.py          # Server qayta yoqilishini (boot_id) aniqlash va darhol alert yuborish
├── docker_manager.py         # Docker konteynerlari boshqaruvi
├── network_manager.py        # Ochiq portlar (ss -tulpn) jadvali
├── file_manager.py           # Fayllarni yuklab olish (/getfile) va tizim keshini tozalash
├── server_monitor.py         # CPU, RAM, Disk, Uptime va Log hodisalari tahlili
├── background_tasks.py       # Doimiy monitoring va hodisalar workeri
├── auth_manager.py           # Admin autentifikatsiyasi va sessiyalar
├── keyboards.py              # Reply va barcha interaktiv Inline klaviaturalar
├── install_service.sh        # Debian 13 minimal autostart o'rnatuvchi
├── server-master-bot.service # Systemd unit konfiguratsiyasi
├── tests/                    # 29 ta to'liq unit va e2e testlar
└── docs/                     # Arxitektura va ijro rejalari
```

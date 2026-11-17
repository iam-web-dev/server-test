# SysAdmin & DevOps Master Tool Telegram Boti — Loyiha Dizayni (Design Document)

**Sana:** 2026-11-17  
**Holat:** Ko'rib chiqildi (Builder Check o'tkazildi)  
**Tizim:** Debian 13 (Trixie) Minimal / Linux  
**Texnologiyalar:** Python 3.11+, aiogram 3.x, systemd, asyncio, subprocess  

---

## 1. Kirish va Maqsad (Intent & The Why)

Hozirgi server monitoring boti faqat passiv ko'rsatkichlarni (CPU, RAM, Disk) va log ogohlantirishlarini chiqarib beradi. Server ma'muri (DevOps / SysAdmin) muammo yuz berganda yoki biror amal bajarmoqchi bo'lganda (masalan, servis to'xtab qolganda, yangi deploy bo'lganda, xotira to'lganda yoki terminal buyrug'i kerak bo'lganda) kompyuterni ochib SSH orqali kirishga majbur bo'ladi.

**Asosiy maqsad:** Ushbu botni to'laqonli **Master Tool**ga aylantirish. Administrator o'z Telegram messenjeri orqali xuddi serverda `root` huquqida o'tirgandek:
1. Serverdagi barcha mustaqil loyihalarni (backend, frontend, botlar, saytlar, PM2, Docker, Uvicorn, Nginx) bir joydan ko'rish va boshqarish;
2. Serverda istalgan terminal buyruqlarini xavfsiz va to'liq erkin bajarish (`/sh <komanda>` yoki terminal rejimi);
3. Server o'chib-yongan zahoti avtomatik ravishda `systemd` orqali ishga tushib, Telegramga darhol xabarnoma (IP, Uptime, tizim holati) yuborishi;
4. Portlar, tarmoq, fayllarni yuklab olish va tizim keshini tozalash amallarini amalga oshira olishi kerak.

---

## 2. Maqsadlar, No-Maqsadlar va Anti-Maqsadlar

### Maqsadlar (Goals):
- **Root-level Terminal Execution:** Istalgan Linux buyrug'ini `root` huquqida bajarish, stdout/stderr ni qaytarish, uzoq davom etuvchi buyruqlar uchun timeout (standart 60 soniya) va xatoliklarni xavfsiz ushlash.
- **Aqlli chiqish (Output Pagination & File Upload):** Chiqish 3800 belgidan oshsa, Telegram xabari chegarasidan chiqib xatolik bermasdan, natijani `.txt` fayl sifatida foydalanuvchiga yuborish.
- **Loyiha va Jarayonlarni boshqarish (Project Hub):** Serverda ishlayotgan Node/PM2 ilovalari, Python/Uvicorn/Gunicorn backendlar, Telegram botlar, Docker konteynerlar va Nginx saytlarini avtomatik aniqlash va ularni alohida menyu orqali restart/stop/start va loglarini ko'rish imkoniyati.
- **Debian 13 Minimal Systemd Integratsiyasi & Boot Alert:** Server o'chib-yonganini aniqlash (`/proc/sys/kernel/random/boot_id` yoki uptime orqali). Tizim yuklanishi bilan bot ishga tushib, barcha faol adminlarga *"🟢 SERVER YOQILDI / QAYTA YUKLANDI"* deb batafsil ma'lumot jo'natishi.
- **O'rnatish skripti (`install_service.sh`):** Debian 13 minimal serverida bitta buyruq bilan `systemd` servis yaratish, faollashtirish va ishga tushirish.
- **Docker va Tarmoq boshqaruvi:** Konteynerlarni ko'rish va boshqarish, ochiq portlarni (`ss -tulpn`) ko'rish.
- **Fayllar va Loglarni olish:** Serverdagi istalgan faylni Telegramga yuklab olish (`/getfile <path>`) va loglarning oxirgi qismini ko'rish (`/tail <path> <lines>`).
- **Disk va Tizim tozalash:** `journalctl --vacuum-time`, `apt clean`, `docker system prune` kabi operatsiyalarni bitta tugma bilan bajarish.

### No-Maqsadlar (Non-Goals):
- VIM yoki Nano kabi to'liq interaktiv curses-muhitlarni Telegram orqali emulyatsiya qilish (buning o'rniga buyruqlar yoki fayl yuklash yetarli).
- Ko'p serverli klasterlarni (Kubernetes) boshqarish — bot bitta mustaqil Linux serveri (Debian 13 minimal) uchun super-qurol hisoblanadi.

### Anti-Maqsadlar (Anti-Goals):
- Autentifikatsiyadan o'tmagan begona foydalanuvchilarga har qanday buyruq yoki ma'lumotni ochish (faqat `auth_manager` dagi tasdiqlangan adminlargina kira oladi).
- Botning qulashiga olib keluvchi bloklovchi (synchronous/blocking) operatsiyalar — barcha terminal va I/O jarayonlari `asyncio` asosida asinxron ishlaydi.

---

## 3. Cheklovlar va Arxitekturaviy Qarorlar (Builder Calls & Decisions)

1. **Privilege Model (Root):**
   * *Qaror:* Botning `server-master-bot.service` foni to'g'ridan-to'g'ri `User=root` sifatida ishlaydi.
   * *Sababi:* Debian 13 minimal tizimida odatda `sudo` o'rnatilmagan bo'ladi. Foydalanuvchi serverda "root user kabi to'liq erkinlik" talab qilgan. Bu parolsiz, to'siqlarsiz tizim boshqaruvini ta'minlaydi.
2. **Terminal va Stdin boshqaruvi:**
   * *Qaror:* Terminal komandalari `DEBIAN_FRONTEND=noninteractive` va `stdin=asyncio.subprocess.DEVNULL` muhitida bajariladi.
   * *Sababi:* `apt` yoki skriptlar tasdiqlash (`[y/N]`) so'rab qotib qolishining oldi olinadi. O'rnatishlarda `-y` bayrog'i ishlatiladi.
3. **Loyiha va Jarayonlarning hayot sikli (Lifecycle Semantics):**
   * *Qaror:* To'liq **Start / Stop / Restart / Logs** boshqaruvi nazorat qilinadigan (supervised) platformalar uchun amalga oshiriladi:
     - **Systemd** dasturiy servislari (`/etc/systemd/system/*.service`);
     - **PM2** ilovalari (`pm2 start/stop/restart/logs`);
     - **Docker** konteynerlari (`docker start/stop/restart/logs`).
   * Erkin (unsupervised) fon jarayonlari (masalan, `ps` da ko'ringan alohida `python script.py`):
     - Ko'rish (PID, CPU%, MEM%, Uptime, buyruq qatori);
     - To'xtatish (**Kill / SIGTERM / SIGKILL** tugmasi orqali).
     - Qayta ishga tushirish terminal orqali `/sh` yordamida amalga oshiriladi.
4. **Nginx saytlari boshqaruvi:**
   * *Qaror:* Virtual hostlar (`/etc/nginx/sites-enabled/`) ro'yxati, domenlar va proksi portlarini ko'rish, vhost loglarini o'qish, konfiguratsiyani tekshirish (`nginx -t`) va Nginx'ni qayta yuklash (`systemctl reload nginx`).
5. **Servislar filtrlash:**
   * `/etc/systemd/system/` dagi maxsus servislar va PM2/Docker = `[ 🚀 Loyihalar & Saytlar ]`.
   * Standart infratuzilma servislari (`nginx`, `postgresql`, `mysql`, `redis`, `docker`, `ssh`) = `[ ⚙️ Servislar & Docker ]`.

---

## 4. Tizim Modullari va Strukturasi

```
Bots/
├── main.py                   # Asosiy handlerlar, yangilangan klaviaturalar va marshrutlash
├── terminal_manager.py       # Root komandalarni bajarish, cwd tracking, formatlash, timeout
├── project_manager.py        # Backend, frontend, botlar, PM2, Docker, Nginx larni aniqlash va boshqarish
├── docker_manager.py         # Docker konteynerlari monitoringi va boshqaruvi
├── network_manager.py        # Ochiq portlar (ss), IP, faol ulanishlar
├── file_manager.py           # Fayllarni yuklash, loglarni tail qilish, tizimni tozalash
├── boot_notifier.py          # Server yoqilishi (boot_id) ni aniqlash va darhol alert yuborish
├── server_monitor.py         # Mavjud CPU/RAM/Disk/Log monitor (saqlanadi va kengaytiriladi)
├── background_tasks.py       # Fon monitoringi + boot alert tekshiruvi
├── auth_manager.py           # Admin sessiyalari (saqlanadi)
├── keyboards.py              # Kengaytirilgan boshqaruv menyusi va inline klaviaturalar
├── config.py                 # Yangi konfiguratsiya parametrlari
├── install_service.sh        # Debian 13 minimal uchun systemd autostart o'rnatuvchi skript
└── server-master-bot.service # Systemd unit fayli
```

### 4.1. `terminal_manager.py` (Root Terminal & Shell)
- `execute_command(command: str, user_id: int) -> tuple[str, str | None]`:
  - Har bir admin uchun joriy ishchi papkani (`cwd`) eslab qoladi (`cd /var/www` qilsa, keyingi buyruq o'sha papkada bajariladi).
  - `asyncio.create_subprocess_shell` orqali buyruqni bajaradi.
  - Timeout: 60 soniya.
  - Chiqish uzunligi 3800 belgidan oshsa, natijani `BufferedInputFile` sifatida `output_<timestamp>.txt` ko'rinishida jo'natadi.

### 4.2. `project_manager.py` (Loyihalar va Ilovalar Hubi)
- `get_all_projects() -> list[dict]`:
  - PM2 ro'yxati (`pm2 jlist`);
  - Docker konteynerlari (`docker ps --format json`);
  - Foydalanuvchi systemd servislari (`/etc/systemd/system/*.service`);
  - Python/Node.js faol jarayonlari (`ps -eo pid,user,%cpu,%mem,args`).
- Amallar:
  - `restart_project(proj_type, proj_id)`
  - `stop_project(proj_type, proj_id)`
  - `start_project(proj_type, proj_id)`
  - `get_project_logs(proj_type, proj_id, lines=30)`
  - `kill_process(pid: int)`

### 4.3. `boot_notifier.py` (Boot Alert & Autostart)
- `check_boot_and_notify(bot: Bot)`:
  - `/proc/sys/kernel/random/boot_id` ni `data/system_state.json` dagi oxirgi boot ID bilan solishtiradi.
  - Yangi boot ID aniqlansa:
    - Public IP (`curl -s ifconfig.me` yoki ip route orqali);
    - Local IP (`hostname -I`);
    - Uptime (`/proc/uptime`);
    - Tizim yadro versiyasi va xotira holati;
    - Barcha faol adminlarga shoshilinch `🟢 SERVER ISHGA TUSHDI / QAYTA YUKLANDI` xabarini yuboradi.
    - Yangi boot ID ni `data/system_state.json` ga yozadi.

### 4.4. `install_service.sh` (Debian 13 Minimal Systemd Installer)
- Bash skript:
  - Skript joylashgan yo'l (`$(pwd)`) va virtual muhit (`.venv/bin/python`) ni aniqlaydi;
  - `/etc/systemd/system/server-master-bot.service` ni yaratadi;
  - `systemctl daemon-reload` va `systemctl enable --now server-master-bot` ni chaqiradi;
  - Botning doimiy ishlab turishini (Restart=always) ta'minlaydi.

### 4.5. `network_manager.py` & `file_manager.py`
- `get_listening_ports()`: `ss -tulpn` ma'lumotlarini qulay jadval qiladi.
- `get_file(path)`: Fayl mavjud bo'lsa, Telegram hujjat sifatida yuboradi.
- `tail_file(path, lines)`: Faylning oxirgi qismini o'qiydi.
- `clean_system_cache()`: `journalctl --vacuum-time=2d`, `apt clean`, `docker system prune -f` larni bajarib bo'shagan joy hisobotini qaytaradi.

---

## 5. Yangilangan Foydalanuvchi Interfeysi (UI)

### Asosiy Reply Keyboard:
```
[ 📊 Server Statlari ] [ ⚡️ Top Jarayonlar ]
[ 🚀 Loyihalar & Saytlar ] [ 💻 Terminal & Shell ]
[ ⚙️ Servislar & Docker ] [ 🌐 Tarmoq & Portlar ]
[ 📜 Loglar & Tozalash ] [ 🔔 Tizim Holati ]
[ 🚪 Chiqish ]
```

---

*Hujjat to'liq tasdiqlandi va rejani amalga oshirishga tayyor.*

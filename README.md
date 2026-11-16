# ⏰ Har daqiqada vaqt jo'natuvchi Telegram Bot (Python / aiogram 3)

Ushbu bot ko'rsatilgan Telegram ID ga har daqiqada (aniq 00-soniyada) O'zbekiston vaqti bo'yicha (`Asia/Tashkent`) hozirgi vaqtni yuborib turadi.

---

## 🚀 Loyihada 2 xil variant mavjud:

1. **`main.py` (Tavsiya etiladi - Dinamik variant):**
   - Foydalanuvchi botga kirib `/start` bossa, uning ID sini aniqlaydi.
   - Menyudagi **«▶️ O'z ID-imga yuborish»** tugmasi orqali o'ziga vaqt jo'natishni boshlash mumkin.
   - Istalgan boshqa **Telegram ID raqamini xabar qilib yuborsa**, bot o'sha ID ga har daqiqada vaqt jo'nata boshlaydi.
   - **«⏹ To'xtatish»** (`/stop`) yoki **«📊 Holat»** (`/status`) buyruqlari mavjud.
   - Xatoliklar (masalan: foydalanuvchi botni bloklagan bo'lsa) xavfsiz boshqariladi.

2. **`single_file_bot.py` (Oddiy bitta faylli variant):**
   - Kod ichidagi `BOT_TOKEN` va `TARGET_CHAT_ID` ga o'zingizning qiymatlaringizni yozib to'g'ridan-to'g'ri ishga tushirishingiz mumkin.

---

## 🛠 O'rnatish va Ishga tushirish

### 1. Virtual muhit yaratish va faollashtirish
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Kutubxonalarni o'rnatish
```bash
pip install -r requirements.txt
```

### 3. Bot Token va Sozlamalarni kiritish
`.env` faylini oching va `@BotFather` dan olgan tokeningizni kiriting:
```env
BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrSTUvwxYZ
```

*(Ixtiyoriy: Agar bot ishga tushishi bilan biror ID ga avtomatik vaqt jo'natishni boshlamoqchi bo'lsangiz, `DEFAULT_TARGET_ID=123456789` qilib yozib qo'yishingiz ham mumkin).*

### 4. Botni ishga tushirish
```bash
python3 main.py
```

---

## ⚠️ Muhim Telegram Qoidasi
Telegram xavfsizlik va spamga qarshi qoidalariga ko'ra:
> **Bot faqat unga kamida bir marta `/start` bosgan foydalanuvchiga xabar yubora oladi!**
> Agar siz biror do'stingiz yoki boshqa ID ga xabar bormoqchi bo'lsangiz, u inson avval botingizga kirib kamida bir marta `/start` bosgan bo'lishi kerak.

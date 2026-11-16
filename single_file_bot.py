"""
Oddiy va qulay bitta faylli bot (Single file script).
Faqat TOKEN va TARGET_ID ni kiritib ishga tushirsangiz kifoya.
"""

import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart

# 1. BOT TOKEN (BotFather dan olingan token)
BOT_TOKEN = "BOT_TOKENINGIZNI_SHU_YERGA_YOZING"

# 2. Xabar borishi kerak bo'lgan Telegram ID
TARGET_CHAT_ID = 123456789  # O'zgartiring

# Toshkent vaqt mintaqasi (UTC+5)
TASHKENT_TZ = ZoneInfo("Asia/Tashkent")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


async def send_time_every_minute():
    """Har 60 soniyada ko'rsatilgan ID ga vaqtni yuborib turuvchi funksiya"""
    while True:
        try:
            # Aniq daqiqa boshlanishiga sinxronlash
            now = datetime.now(TASHKENT_TZ)
            sleep_sec = 60 - now.second - (now.microsecond / 1_000_000)
            await asyncio.sleep(sleep_sec)

            current_time = datetime.now(TASHKENT_TZ).strftime("%H:%M:%S (%d.%m.%Y)")
            await bot.send_message(
                chat_id=TARGET_CHAT_ID,
                text=f"⏰ Hozirgi vaqt: {current_time}"
            )
        except Exception as e:
            print(f"Xatolik yuz berdi: {e}")
            await asyncio.sleep(5)


@dp.message(CommandStart())
async def start_handler(message: types.Message):
    await message.answer(
        f"Salom, {message.from_user.full_name}!\n"
        f"Sizning Telegram ID: {message.from_user.id}"
    )


async def main():
    # Fon vazifasini ishga tushiramiz
    asyncio.create_task(send_time_every_minute())
    print("Bot ishga tushdi va vaqt yuborish boshlandi...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

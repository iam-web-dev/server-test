import asyncio
import logging
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import Bot, Dispatcher, F, types
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramRetryAfter
from aiogram.filters import Command, CommandStart
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

import config

# Loglarni sozlash
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# O'zbekiston vaqt mintaqasi
TASHKENT_TZ = ZoneInfo("Asia/Tashkent")

# Vaqt yuborilishi kerak bo'lgan ID lar to'plami
active_targets: set[int] = set()

# Asosiy tugmalar klaviaturasi
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="▶️ O'z ID-imga yuborish"), KeyboardButton(text="⏹ To'xtatish")],
        [KeyboardButton(text="📊 Holat (Status)"), KeyboardButton(text="❓ Yordam")],
    ],
    resize_keyboard=True,
)


async def send_time_worker(bot: Bot):
    """
    Har daqiqaning boshida (00-soniyada) faol ID larga hozirgi vaqtni yuboruvchi fon vazifasi.
    """
    logger.info("Vaqt yuborish foni (worker) ishga tushdi.")
    while True:
        try:
            # Keyingi daqiqaning 00-soniyasigacha qolgan vaqtni hisoblaymiz (aniq daqiqa boshi uchun)
            now = datetime.now(TASHKENT_TZ)
            seconds_until_next_minute = 60 - now.second - (now.microsecond / 1_000_000)
            await asyncio.sleep(seconds_until_next_minute)

            current_time = datetime.now(TASHKENT_TZ).strftime("%H:%M:%S (%d.%m.%Y)")
            text = f"⏰ <b>Hozirgi vaqt:</b> <code>{current_time}</code>"

            if not active_targets:
                continue

            # Faol ID lar ro'yxati bo'ylab jo'natamiz
            for chat_id in list(active_targets):
                try:
                    await bot.send_message(chat_id=chat_id, text=text, parse_mode=ParseMode.HTML)
                except TelegramForbiddenError:
                    logger.warning(
                        f"Foydalanuvchi {chat_id} botni bloklagan yoki botga /start bosmagan. Ro'yxatdan o'chirilmoqda."
                    )
                    active_targets.discard(chat_id)
                except TelegramBadRequest as e:
                    logger.warning(f"ID {chat_id} ga xabar yuborishda xato: {e.message}")
                except TelegramRetryAfter as e:
                    logger.warning(f"Telegram Flood limit: {e.retry_after} soniya kutilmoqda.")
                    await asyncio.sleep(e.retry_after)
                except Exception as e:
                    logger.error(f"Xabar yuborishda kutilmagan xatolik (ID: {chat_id}): {e}")

        except asyncio.CancelledError:
            logger.info("Vaqt yuborish foni to'xtatildi.")
            break
        except Exception as e:
            logger.error(f"Fon jarayonida xatolik yuz berdi: {e}")
            await asyncio.sleep(2)


dp = Dispatcher()


@dp.message(CommandStart())
async def command_start_handler(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.full_name

    text = (
        f"Assalomu alaykum, <b>{username}</b>!\n\n"
        f"Sizning Telegram ID raqamingiz: <code>{user_id}</code>\n\n"
        "<b>Bot qanday ishlaydi?</b>\n"
        "1️⃣ O'zingizga har daqiqada vaqtni yuborish uchun <b>«▶️ O'z ID-imga yuborish»</b> tugmasini bosing.\n"
        "2️⃣ Boshqa biror Telegram ID ga yubormoqchi bo'lsangiz, o'sha <b>ID raqamini xabar qilib yuboring</b> (masalan: <code>123456789</code>).\n"
        "3️⃣ To'xtatish uchun <b>«⏹ To'xtatish»</b> tugmasini bosing.\n\n"
        "<i>Eslatma: Telegram qoidalariga ko'ra, bot birinchi bo'lib foydalanuvchiga yozishi uchun o'sha foydalanuvchi botga hech bo'lmaganda bir marta /start bosgan bo'lishi shart!</i>"
    )
    await message.answer(text, reply_markup=main_keyboard, parse_mode=ParseMode.HTML)


@dp.message(F.text == "▶️ O'z ID-imga yuborish")
async def start_self_handler(message: types.Message):
    user_id = message.from_user.id
    if user_id in active_targets:
        await message.answer("Sizning ID-ingizga allaqachon har daqiqada vaqt yuborilmoqda! ⏰")
    else:
        active_targets.add(user_id)
        current_time = datetime.now(TASHKENT_TZ).strftime("%H:%M:%S")
        await message.answer(
            f"✅ Boshlandi! Har daqiqada <code>{user_id}</code> ID-ingizga hozirgi vaqt jo'natib turiladi.\n"
            f"Hozirgi vaqt: <b>{current_time}</b>",
            parse_mode=ParseMode.HTML,
        )


@dp.message(F.text == "⏹ To'xtatish")
@dp.message(Command("stop"))
async def stop_handler(message: types.Message):
    args = message.text.split()
    user_id = message.from_user.id

    # Agar /stop 123456 ko'rinishida berilgan bo'lsa
    if len(args) > 1 and args[1].lstrip("-").isdigit():
        target_id = int(args[1])
        if target_id in active_targets:
            active_targets.discard(target_id)
            await message.answer(f"🛑 <code>{target_id}</code> ro'yxatdan olib tashlandi.", parse_mode=ParseMode.HTML)
            return
        else:
            await message.answer(f"<code>{target_id}</code> faol ro'yxatda mavjud emas.", parse_mode=ParseMode.HTML)
            return

    # O'z ID sini to'xtatish
    if user_id in active_targets:
        active_targets.discard(user_id)
        await message.answer("🛑 Vaqt yuborish to'xtatildi.", parse_mode=ParseMode.HTML)
    else:
        await message.answer("Sizga hozirda vaqt yuborilmayapti.")


@dp.message(F.text == "📊 Holat (Status)")
@dp.message(Command("status"))
async def status_handler(message: types.Message):
    if not active_targets:
        await message.answer("Hozircha hech qaysi Telegram ID ga vaqt yuborilmayapti.")
    else:
        id_list = "\n".join([f"• <code>{tid}</code>" for tid in active_targets])
        await message.answer(
            f"📊 <b>Vaqt yuborilayotgan faol ID lar soni:</b> {len(active_targets)} ta\n\n{id_list}",
            parse_mode=ParseMode.HTML,
        )


@dp.message(F.text == "❓ Yordam")
@dp.message(Command("help"))
async def help_handler(message: types.Message):
    help_text = (
        "<b>Botdan foydalanish qo'llanmasi:</b>\n\n"
        "• <b>Telegram ID yuborish:</b> Shunchaki xabar sifatida ID raqam yozib yuboring (masalan: <code>987654321</code>). Bot ushbu ID ga har daqiqada vaqt yuborishni boshlaydi.\n"
        "• <b>/stop [id]:</b> Vaqt yuborishni to'xtatish (masalan: <code>/stop</code> yoki <code>/stop 987654321</code>).\n"
        "• <b>/status:</b> Hozir qaysi ID larga vaqt yuborilayotganini ko'rish.\n\n"
        "<i>Eslatma:</i> Agar bot begonaga xabar yuborishi kerak bo'lsa, o'sha inson botga avval <code>/start</code> bosgan bo'lishi kerak."
    )
    await message.answer(help_text, parse_mode=ParseMode.HTML)


@dp.message()
async def custom_id_handler(message: types.Message):
    raw_text = message.text.strip() if message.text else ""

    # Agar kiritilgan matn butun son bo'lsa (Telegram ID: musbat yoki guruhlar uchun manfiy son bo'lishi mumkin)
    if raw_text.lstrip("-").isdigit():
        target_id = int(raw_text)

        if target_id in active_targets:
            await message.answer(
                f"ℹ️ <code>{target_id}</code> ID si allaqachon faol ro'yxatda bor!",
                parse_mode=ParseMode.HTML,
            )
            return

        active_targets.add(target_id)
        current_time = datetime.now(TASHKENT_TZ).strftime("%H:%M:%S")

        await message.answer(
            f"✅ <b>Qabul qilindi!</b>\n\n"
            f"Endi har daqiqada <code>{target_id}</code> ID raqamiga hozirgi vaqt jo'natiladi.\n"
            f"Hozirgi vaqt: <b>{current_time}</b>\n\n"
            f"<i>To'xtatish uchun:</i> <code>/stop {target_id}</code>",
            parse_mode=ParseMode.HTML,
        )

        # O'sha ID ga birinchi tekshiruv xabarini yuborib ko'ramiz
        if target_id != message.from_user.id:
            try:
                await message.bot.send_message(
                    chat_id=target_id,
                    text=f"Salom! Ushbu ID ga har daqiqada vaqt yuborish xizmati faollashtirildi.\nHozirgi vaqt: {current_time}",
                )
            except TelegramForbiddenError:
                await message.answer(
                    f"⚠️ <b>Diqqat:</b> <code>{target_id}</code> foydalanuvchisi botga hali /start bosmagan yoki botni bloklagan. Shu sababli bot unga xabar yubora olmasligi mumkin.",
                    parse_mode=ParseMode.HTML,
                )
            except Exception as e:
                logger.warning(f"Test xabarida xatolik: {e}")
    else:
        await message.answer(
            "Iltimos, to'g'ri Telegram ID raqamini yuboring (masalan: <code>123456789</code>) yoki menyudagi tugmalardan foydalaning.",
            parse_mode=ParseMode.HTML,
        )


async def main():
    if not config.BOT_TOKEN:
        logger.error("BOT_TOKEN ko'rsatilmagan! Iltimos, .env fayliga bot tokeningizni kiriting.")
        print("\n[XATOLIK] BOT_TOKEN topilmadi! .env fayliga BOT_TOKEN=... ni kiriting.\n")
        return

    # Agar .env da boshlang'ich ID ko'rsatilgan bo'lsa
    if config.DEFAULT_TARGET_ID:
        active_targets.add(config.DEFAULT_TARGET_ID)
        logger.info(f"Boshlang'ich ID yuklandi: {config.DEFAULT_TARGET_ID}")

    bot = Bot(token=config.BOT_TOKEN)

    # Fon vazifasini ishga tushirish (har daqiqada vaqt yuboruvchi task)
    time_task = asyncio.create_task(send_time_worker(bot))

    try:
        logger.info("Bot ishga tushmoqda...")
        await dp.start_polling(bot)
    finally:
        time_task.cancel()
        await bot.session.close()
        logger.info("Bot to'xtatildi.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot to'xtatildi.")

import os
from dotenv import load_dotenv

# .env faylini yuklash
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

# Ixtiyoriy boshlang'ich ID
default_id_raw = os.getenv("DEFAULT_TARGET_ID", "").strip()
DEFAULT_TARGET_ID = int(default_id_raw) if default_id_raw.isdigit() else None

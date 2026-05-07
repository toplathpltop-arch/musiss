import os
import logging
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
SUPERADMIN_ID: int = int(os.getenv("SUPERADMIN_ID", "0"))
LASTFM_API_KEY: str = os.getenv("LASTFM_API_KEY", "")
DATABASE_PATH: str = os.getenv("DATABASE_PATH", "data/bot.db")
MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "50"))
DOWNLOAD_PATH: str = os.getenv("DOWNLOAD_PATH", "./downloads")
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

MAX_FILE_SIZE_BYTES: int = MAX_FILE_SIZE_MB * 1024 * 1024

RATE_LIMIT_REQUESTS: int = 3
RATE_LIMIT_WINDOW: int = 60

os.makedirs(DOWNLOAD_PATH, exist_ok=True)
os.makedirs(os.path.dirname(DATABASE_PATH) if os.path.dirname(DATABASE_PATH) else ".", exist_ok=True)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
)

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN muhit o'zgaruvchisi o'rnatilmagan!")

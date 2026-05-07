import sys
import os
import logging

# Add project root to path so all modules resolve correctly
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from telegram.ext import Application, ApplicationBuilder

from config import BOT_TOKEN, SUPERADMIN_ID
from database import init_db, add_admin, is_admin
from handlers.start import get_handlers as start_handlers
from handlers.downloader import get_handlers as dl_handlers
from handlers.admin import get_handlers as admin_handlers, get_conversation_handlers

logger = logging.getLogger(__name__)


async def post_init(app: Application):
    await init_db()
    if not await is_admin(SUPERADMIN_ID):
        await add_admin(SUPERADMIN_ID, None, SUPERADMIN_ID, role="superadmin")
    logger.info(f"Bot initialized. Superadmin: {SUPERADMIN_ID}")


def main():
    logger.info("Starting bot...")
    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .concurrent_updates(True)
        .build()
    )

    # Conversation handlers must come first
    for h in get_conversation_handlers():
        app.add_handler(h)

    # Start / help
    for h in start_handlers():
        app.add_handler(h)

    # Admin callbacks
    for h in admin_handlers():
        app.add_handler(h)

    # Download + link router (last — catch-all)
    for h in dl_handlers():
        app.add_handler(h)

    logger.info("Bot polling...")
    app.run_polling(
        drop_pending_updates=True,
        allowed_updates=["message", "callback_query"],
    )


if __name__ == "__main__":
    main()

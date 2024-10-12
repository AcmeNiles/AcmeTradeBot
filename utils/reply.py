from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from config import MENU_IMAGE_URL
from config import logger

logger = logging.getLogger(__name__)

async def reply(update: Update, text: str, reply_markup=None):
    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup)
    elif update.callback_query:
        if update.callback_query.message:
            await update.callback_query.message.reply_text(text, reply_markup=reply_markup)
        else:
            logger.warning("Callback query has no associated message.")
    else:
        logger.error("No valid message or callback query to reply to.")

async def reply_photo(update: Update, welcome_text: str, reply_markup: InlineKeyboardMarkup):
    if update.message:
        await update.message.reply_photo(photo=MENU_IMAGE_URL, caption=welcome_text, reply_markup=reply_markup, parse_mode='MarkdownV2')
    elif update.callback_query:
        if update.callback_query.message:
            await update.callback_query.message.reply_photo(photo=MENU_IMAGE_URL, caption=welcome_text, reply_markup=reply_markup, parse_mode='MarkdownV2')
        else:
            logger.warning("Callback query has no associated message.")
            # Optionally, send a message to the user or handle this case as needed

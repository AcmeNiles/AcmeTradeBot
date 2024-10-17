from config import logger
from telegram import Update, Bot
from telegram.error import TelegramError
from telegram.ext import ContextTypes


async def handle_recipient(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return False
    
async def is_valid_telegram_username(bot: Bot, username: str) -> bool:
    """
    Check if a Telegram username exists and is not a bot.

    Args:
        bot (Bot): The Telegram bot instance.
        username (str): The Telegram username to check.

    Returns:
        bool: True if the username exists and is not a bot, False otherwise.
    """
    try:
        user = await bot.get_chat(username)
        # Check if the user is not a bot
        return not user.is_bot
    except TelegramError:
        # If an error occurs (e.g., username does not exist), return False
        return False

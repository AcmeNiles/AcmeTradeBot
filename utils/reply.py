from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext
from config import logger

# Helper function to send a message with MarkdownV2 formatting and optional reply_markup
async def send_message(update: Update, context: CallbackContext, text: str, reply_markup=None):
    chat_id = update.effective_chat.id
    await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode="MarkdownV2", 
        reply_markup=reply_markup
    )

# Helper function to send a photo with caption
async def send_photo(update: Update, context: CallbackContext, photo_url: str, caption: str, reply_markup):
    try:
        if update.message:
            await update.message.reply_photo(
                photo=photo_url,
                caption=caption,
                parse_mode="MarkdownV2",
                reply_markup=reply_markup,
            )
        elif update.callback_query:
            await update.callback_query.message.reply_photo(
                photo=photo_url,
                caption=caption,
                parse_mode="MarkdownV2",
                reply_markup=reply_markup,
            )
        else:
            raise ValueError("Update is neither a message nor a callback query.")
    except Exception as e:
        logger.error(f"Failed to send photo: {str(e)}")
        await send_message(update, context, "An error occurred while sending the trading card.")

# Helper function to send an animation (GIF) with caption
async def send_animation(update: Update, context: CallbackContext, photo_url: str, caption: str, reply_markup):
    try:
        if update.message:
            await update.message.reply_animation(
                animation=photo_url,
                caption=caption,
                parse_mode="MarkdownV2",
                reply_markup=reply_markup,
            )
        elif update.callback_query:
            await update.callback_query.message.reply_animation(
                animation=animation_url,
                caption=caption,
                parse_mode="MarkdownV2",
                reply_markup=reply_markup,
            )
        else:
            raise ValueError("Update is neither a message nor a callback query.")
    except Exception as e:
        logger.error(f"Failed to send animation: {str(e)}")
        await send_message(update, context, "An error occurred while sending the animation.")

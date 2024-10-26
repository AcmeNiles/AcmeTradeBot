from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import CallbackContext, ConversationHandler
from telegram.helpers import escape_markdown
from config import logger, BOT_USERNAME, MAX_LISTED_TOKENS, PHOTO_COYOTE_TABLE
from utils.reply import send_message, send_photo, send_error_message, clear_cache, send_edit_top3_message
from utils.profilePhoto import fetch_user_profile_photo
from utils.tokenValidator import fetch_and_format_token_data
from handlers.auth_handler import get_auth_result

from messages_photos import PHOTO_EXCHANGE
from messages_photos import markdown_v2

# Configurable exchange message
EXCHANGE = (
    "*🚀 [{username_display} Exchange](https://t.me/{bot_username}?start) 🚀*\n\n"
    "👇 Click to buy my *#Top3* tokens:\n\n"
    "{tokens}"
    "💸 Let’s make some money!"
)

NO_TOKENS = "No tokens available for processing"
NO_VALID_TOKENS = "No valid tokens to display."
ERROR_OCCURRED = "An error occurred. Please try again."

async def process_list(update: Update, context: CallbackContext) -> int:
    logger.info("Processing list request.")
    try:
        tokens = context.user_data.get('tokens', [])
        if not tokens:
            logger.warning("No tokens found in user data.")
            await send_error_message(update, context)
            return ConversationHandler.END
            
        receiver_data = context.user_data.get('receiver') or {}
        auth_result = await get_auth_result(update, context) or {}

        # Safely get username
        username = receiver_data.get('name') or auth_result.get('tg_firstName') or BOT_USERNAME

    
        combined_text = ""
        buttons = []
        max_tokens_to_process = min(len(tokens), MAX_LISTED_TOKENS)

        for idx, token in enumerate(tokens[:max_tokens_to_process], start=1):
            try:
                # Pass the current index to handle the symbol selection
                trading_card_text, button = await fetch_and_format_token_data(token, username, idx)
                combined_text += trading_card_text
                buttons.append(button)  # Add the button to the list
            except Exception as e:
                logger.exception(f"Error processing token {token.get('symbol', '')}: {e}")

        # In case there's no combined text
        if not combined_text:
            logger.exception(f"Error processing token {token.get('symbol', '')}: {e}")
            await send_error_message(update, context)
            return ConversationHandler.END
            
        username_display = f"{username}'" if username.endswith('s') else f"{username}'s"

        final_message = markdown_v2(EXCHANGE.format(
            tokens=combined_text,  # Escape combined_text
            username_display=username_display,
            bot_username=BOT_USERNAME
        ))

        reply_markup = InlineKeyboardMarkup(
            [
                buttons,
                [InlineKeyboardButton("Learn more", url=f"https://www.acme.am")]
            ]) if buttons else None
        profile_photo = PHOTO_COYOTE_TABLE
        #profile_photo = await fetch_user_profile_photo(update, context) or PHOTO_EXCHANGE

        await send_photo(update, context, profile_photo, final_message, reply_markup)
        logger.info("Successfully sent the combined trading message.")
        await send_edit_top3_message(update, context)
        return await clear_cache(update, context)

    except KeyError as e:
        logger.error(f"Missing key in user data: {e}")
        await send_message(update, context, escape_markdown(ERROR_OCCURRED))
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        await send_message(update, context, escape_markdown(ERROR_OCCURRED))
    finally:
        return ConversationHandler.END

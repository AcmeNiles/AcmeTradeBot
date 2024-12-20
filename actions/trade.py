from config import logger, BOT_USERNAME, PHOTO_COYOTE_COOK, MAKE_MONEY
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import CallbackContext, ConversationHandler
from utils.tokenValidator import fetch_and_format_token_data
from utils.reply import send_message, send_photo, clear_cache, send_share_message
from handlers.auth_handler import get_auth_result
from messages_photos import markdown_v2

# Configurable exchange message
TRADE_TEMPLATE = (
    "📢 *[{username}](https://t.me/{bot_username}?start)* listed:\n\n"
    "{tokens}"
) + MAKE_MONEY

async def process_trade(update: Update, context: CallbackContext) -> int:
    logger.info("Processing single trade request.")
    try:
        intent = context.user_data.get('intent') or 'trade'
        receiver_data = context.user_data.get('receiver') or {}
        auth_result = await get_auth_result(update, context) or {}

        # Ensure username is set and formatted correctly
        username = (
            receiver_data.get('name') or
            auth_result.get('tg_firstName') or
            BOT_USERNAME
        )
        # Get the first token
        token = context.user_data.get('tokens', [{}])[0]
        logo_url = token.get('logoUrl', PHOTO_COYOTE_COOK)

        try:
            # Format the token data for display
            trading_card_text, button = await fetch_and_format_token_data(token, username, index=0)
            final_message = markdown_v2(TRADE_TEMPLATE.format(
                tokens=trading_card_text,
                username=username,
                bot_username=BOT_USERNAME
            ))

            # Prepare the reply markup with a single button for the trade
            reply_markup = InlineKeyboardMarkup([[button]])
            #logger.debug(f"final_message: {final_message}")
            # Send the photo with the formatted message and button
            await send_photo(update, context, logo_url, final_message, reply_markup)
            logger.info("Successfully sent the trading message.") 
            await send_share_message(update, context) if intent == 'share' else None


        except Exception as e:
            logger.error(f"Error formatting or sending trade data: {str(e)}")
            await send_message(update, context, markdown_v2("An error occurred. Please try again."))

    except Exception as e:
        logger.error(f"Error processing trade data: {str(e)}")
        await send_message(update, context, markdown_v2("An error occurred. Please try again."))

    return await clear_cache(update, context)

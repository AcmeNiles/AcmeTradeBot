from config import logger
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import CallbackContext, ConversationHandler
from utils.createTradingLink import create_trading_link
from messages_photos import TRADE, PHOTO_TRADE, markdown_v2

# Simplified 'process_trade' function
async def process_trade(update: Update, context: CallbackContext) -> int:
    logger.info("Entered process_trade function.")

    try:
        # Retrieve tg_key and token object from user_data
        tg_key = context.user_data.get('tg_key')
        token = context.user_data.get('token')

        # Log the retrieved values
        logger.debug(f"Retrieved tg_key: {tg_key}")
        logger.debug(f"Retrieved token object: {token}")

        # Check for missing tg_key or token
        if not tg_key:
            logger.error("Telegram key not found in user data.")
            await send_message(update, context, "Failed to authenticate. Please try again.")
            return ConversationHandler.END

        if not token:
            logger.warning("No token found for trade.")
            await send_message(update, context, "Please specify a token to trade.")
            return ConversationHandler.END

        # Extract key data from token
        symbol = token.get('symbol', '').strip().upper()
        name = token.get('name', 'Unknown Token')
        price = token.get('price')
        change_24h = token.get('change_24h')
        mcap = token.get('mcap')
        volume_24h = token.get('volume_24h')
        chain_id = token.get('chain_id')
        contract_address = token.get('contract_address')
        logo_url = token.get('logoUrl', PHOTO_TRADE)  # Use fallback if logo is missing
        circulating_supply = token.get('circulating_supply')
        total_supply = token.get('total_supply')

        # Log all extracted values
        logger.debug(f"Extracted token details: {locals()}")

        # Ensure chain_id and contract_address are available
        if not chain_id or not contract_address:
            logger.error("Missing chain ID or contract address.")
            await send_message(update, context, "Token data is incomplete. Please try again.")
            return ConversationHandler.END

        # Create a trading link
        trading_link = await create_trading_link(tg_key, chain_id, contract_address, "")
        logger.debug(f"Trading link: {trading_link}")

        # Validate the trading link
        if not trading_link:
            logger.warning(f"Failed to create trading link for {symbol}.")
            await send_message(update, context, "Trading link couldn't be created.")
            return ConversationHandler.END

        # Prepare the trading card text using the TRADE format
        try:
            # Format the trading card text using the TRADE template
            trading_card_text = markdown_v2(TRADE.format(
                symbol=symbol,
                price=price,  # Keep the price as a string
                change_24h=change_24h,  # Keep the 24h change as a string
                mcap=mcap,  # Keep the market cap as a string
                volume_24h=volume_24h,  # Keep the 24h volume as a string
                circulating_supply=circulating_supply,  # Keep circulating supply as a string
                total_supply=total_supply  # Keep total supply as a string
            ))
        except Exception as e:
            logger.error(f"Error formatting trading card text: {str(e)}")
            trading_card_text = "Error in formatting trading card text."

        logger.debug(f"Trading card text:\n{trading_card_text}")
        # Prepare inline button
        buttons = [[
            InlineKeyboardButton(f"Trade {symbol}", web_app=WebAppInfo(url=trading_link))
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)

        # Send the trading card with the photo
        await send_photo(update, context, logo_url, trading_card_text, reply_markup)
        logger.info("Trading card sent successfully.")

    except Exception as e:
        logger.error(f"Error in process_trade: {str(e)}")
        await send_message(update, context, "An error occurred. Please try again.")

    return ConversationHandler.END  # End the conversation

# Helper function to send a message
async def send_message(update: Update, context: CallbackContext, text: str):
    chat_id = update.effective_chat.id
    await context.bot.send_message(chat_id=chat_id, text=text)

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

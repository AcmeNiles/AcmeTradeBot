from config import logger
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import CallbackContext, ConversationHandler
from utils.createTradingLink import create_trading_link
from utils.getTokenMarketData import fetch_and_format_token_market_data
from messages_photos import TRADE, PHOTO_TRADE, markdown_v2

async def process_trade(update: Update, context: CallbackContext) -> int:
    logger.info("Processing trade request.")

    try:
        # Retrieve tg_key and token object from user_data
        tg_key = context.user_data.get('tg_key')
        token = context.user_data['tokens'][0]

        # Log token data early
        logger.info(f"Token data: {token}")

        # Check for missing tg_key
        if not tg_key:
            await send_message(update, context, "Failed to authenticate. Please try again.")
            return ConversationHandler.END

        # Extract key data from token
        symbol = token.get('symbol', '').strip().upper()
        chain_id = token.get('chain_id')
        decimals = token.get('decimals')

        contract_address = token.get('contract_address')
        logo_url = token.get('logoUrl', PHOTO_TRADE)  # Use fallback if logo is missing

        # Log token data early
        logger.info(f"Token chain_id: {chain_id}")

        # Ensure chain_id and contract_address are available
        if not chain_id or not contract_address:
            await send_message(update, context, "Token data is incomplete. Please try again.")
            return ConversationHandler.END

        # Create a trading link
        trading_link = await create_trading_link(tg_key, chain_id, contract_address, "")
        if not trading_link:
            await send_message(update, context, "Trading link couldn't be created.")
            return ConversationHandler.END

        # Fetch and format the token market data
        token_market_data = await fetch_and_format_token_market_data(contract_address, chain_id, decimals)

        # Prepare the trading card text using the TRADE format
        try:
            trading_card_text = markdown_v2(TRADE.format(
                symbol=symbol,
                price=token_market_data.get('price', 'N/A'),  # Ensure price is included in token_market_data
                change_24h=token_market_data.get('change_24h', 'N/A'),
                mcap=token_market_data.get('mcap', 'N/A'),
                volume_24h=token_market_data.get('volume_24h', 'N/A'),
                circulating_supply=token_market_data.get('circulating_supply', 'N/A'),
                total_supply=token_market_data.get('total_supply', 'N/A')
            ))
        except Exception as e:
            trading_card_text = "Error in formatting trading card text."

        # Prepare inline button
        buttons = [[
            InlineKeyboardButton(f"Trade {symbol}", web_app=WebAppInfo(url=trading_link))
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)

        # Send the trading card with the photo
        await send_photo(update, context, logo_url, trading_card_text, reply_markup)

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


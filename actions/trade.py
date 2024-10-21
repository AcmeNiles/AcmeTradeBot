from config import logger, BOT_USERNAME
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import CallbackContext, ConversationHandler
from utils.createTradingLink import create_trading_link
from utils.getTokenMarketData import fetch_and_format_token_market_data
from utils.reply import send_message, send_photo
from messages_photos import PHOTO_TRADE, markdown_v2

TRADE = (
    "📢 *[{username}](https://t.me/{bot_username}?start)* listed:\n\n"
    "*📊 [{symbol}]({trading_link})*\n"
    " ├ Price: *{price}*  \n"
    " ├ 24H: *{change_24h}*\n"
    " ├ MCap: *${mcap}*\n"
    #"🔄 Circulating Supply: *{circulating_supply}*\n"
    #"📦 Total Supply: *{total_supply}*\n"
)

async def process_trade(update: Update, context: CallbackContext) -> int:
    logger.info("Processing trade request.")

    try:
        # Check in context.user_data['receiver'] for username
        receiver_data = context.user_data.get('receiver', {})
        if receiver_data is not None and 'name' in receiver_data and 'tokens' in receiver_data:
            username = receiver_data['name']
        else:
            username = context.user_data['auth_result']['tg_firstName']

        # If still not found, use the update data for username
        if not username:
            username = BOT_USERNAME
        
        # Retrieve token object from user_data
        token = context.user_data['tokens'][0]

        # Log token data early
        logger.info(f"Token data: {token}")

    
        # Extract key data from token
        symbol = token.get('symbol', '').strip().upper()
        chain_id = token.get('chain_id')
        decimals = token.get('decimals')
        contract_address = token.get('contract_address')
        logo_url = token.get('logoUrl', PHOTO_TRADE)  # Use fallback if logo is missing
        trading_link = token.get('tradingLink')  # Retrieve the trading link early
        
        # Ensure chain_id and contract_address are available
        if not chain_id or not contract_address:
            await send_message(update, context, "Token data is incomplete. Please try again.")
            return ConversationHandler.END

        if not trading_link:
            logger.error(f"Missing trading link for {symbol}.")

      # Fetch and format the token market data
        token_market_data = await fetch_and_format_token_market_data(contract_address, chain_id, decimals)

        # Prepare the trading card text using the TRADE format
        try:
            trading_card_text = markdown_v2(TRADE.format(
                username=username,
                bot_username=BOT_USERNAME,
                user_id=user_id,
                symbol=symbol,
                trading_link=trading_link,
                price=token_market_data.get('price', 'N/A'),  # Ensure price is included in token_market_data
                change_24h=token_market_data.get('change_24h', 'N/A'),
                mcap=token_market_data.get('mcap', 'N/A'),
                #volume_24h=token_market_data.get('volume_24h', 'N/A'),
                circulating_supply=token_market_data.get('circulating_supply', 'N/A'),
                total_supply=token_market_data.get('total_supply', 'N/A')
            ))
        except Exception as e:
            trading_card_text = "Error in formatting trading card text."

        # Prepare inline button
        buttons = [[
            InlineKeyboardButton(f"Buy {symbol}", url=trading_link)
        ]]
        reply_markup = InlineKeyboardMarkup(buttons)

        # Send the trading card with the photo
        await send_photo(update, context, logo_url, trading_card_text, reply_markup)

    except Exception as e:
        logger.error(f"Error in process_trade: {str(e)}")
        await send_message(update, context, "An error occurred. Please try again.")

    return ConversationHandler.END  # End the conversation


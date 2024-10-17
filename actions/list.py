from config import logger
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import CallbackContext, ConversationHandler
from utils.createTradingLink import create_trading_link
from utils.reply import send_message, send_photo
from utils.getTokenMarketData import fetch_and_format_token_market_data
from utils.profiltePhoto import fetch_user_profile_photo
from messages_photos import PHOTO_TRADE, markdown_v2

# Configurable exchange message
EXCHANGE = (
    "*🚀 [@{username}](tg://user?id={user_id}) Exchange! 🚀*\n\n"
    "🔥 *Top {NUMER_OF_TOKENS_IN_LIST} Tokens:*\n\n"
    "{tokens}\n"
    "👉 Click on a token to trade!\n\n"
    "💰 Let’s make some money together!"
)

# Token template for display and trading link
TOKEN_TEMPLATE = (
    "{index}️⃣ *[{symbol}]({trading_link})*  \n"
    "   🪙 *Price:* *{price}*  \n"
    "   📈 *24h Change:* *{change_24h}*\n\n"
)

async def process_list(update: Update, context: CallbackContext) -> int:
    logger.info("Processing list request.")
    try:
        # Retrieve tg_key and tokens from user_data
        tg_key = context.user_data.get('tg_key')
        tokens = context.user_data.get('tokens', [])
        username = "cryptoniles"  # Replace with the actual username
        user_id = update.effective_user.id  # Get user ID for the link

        if not tg_key:
            logger.error("Missing tg_key in user data.")
            await send_message(update, context, "Failed to authenticate. Please try again.")
            return ConversationHandler.END

        if not tokens:
            logger.warning("No tokens found in user data.")
            await send_message(update, context, "No tokens available for processing.")
            return ConversationHandler.END

        # Prepare combined message text and buttons
        combined_text = ""
        buttons = []

        # Limit to a maximum of 3 tokens
        max_tokens_to_process = min(len(tokens), 3)

        # Iterate over the first 3 tokens and process them
        for idx in range(max_tokens_to_process):
            token = tokens[idx]  # Directly access the token by index

            try:
                symbol = token.get('symbol', '').strip().upper()
                chain_id = token.get('chain_id')
                contract_address = token.get('contract_address')
                decimals = token.get('decimals')

                logger.info(f"Processing token {symbol} (Chain ID: {chain_id})")

                if not chain_id or not contract_address:
                    logger.warning(f"Skipping token {symbol} due to missing chain ID or contract address.")
                    continue  # Skip this token

                # Fetch trading link and market data
                trading_link = await create_trading_link(tg_key, chain_id, contract_address, "")
                if not trading_link:
                    logger.error(f"Failed to create trading link for {symbol}.")
                    continue  # Skip this token if trading link isn't created

                token_market_data = await fetch_and_format_token_market_data(
                    contract_address, chain_id, decimals
                )
                logger.debug(f"Market data for {symbol}: {token_market_data}")

                # Format the trading card text with the trading link
                trading_card_text = TOKEN_TEMPLATE.format(
                    index=idx + 1,  # Token number starts from 1
                    symbol=symbol,
                    trading_link=trading_link,  # Pass the trading link to the template
                    price=token_market_data.get('price', 'N/A'),
                    change_24h=token_market_data.get('change_24h', 'N/A'),
                )

                # Append text to combined message
                combined_text += trading_card_text

                # Add a button for the token (this is optional if using links in text)
                buttons.append(
                    InlineKeyboardButton(f"{symbol}", web_app=WebAppInfo(url=trading_link))
                )

            except Exception as e:
                logger.exception(f"Error processing token {symbol}: {e}")
                continue  # Continue to the next token

        # Determine the correct label for number of tokens
        token_count_label = "Token" if max_tokens_to_process == 1 else "Tokens"

        # Create the final message using the EXCHANGE format
        final_message = markdown_v2(EXCHANGE.format(
            tokens=combined_text,
            username=username,
            user_id=user_id,
            NUMER_OF_TOKENS_IN_LIST=max_tokens_to_process,
            TOKEN_OR_TOKENS=token_count_label
        ))

        # Create reply markup with buttons in a single row
        reply_markup = InlineKeyboardMarkup([buttons]) if buttons else None

        # Fetch user's profile photo
        logger.info("Getting photo now.")
        
        # Attempt to fetch the user's profile photo
        profile_photo = await fetch_user_profile_photo(update, context)
        logger.info(f"Photo is {profile_photo}.")
        # If the profile photo fetch fails, use the default PHOTO_TRADE
        if not profile_photo:
            logger.warning(f"No profile photo available for user {user_id}. Using default photo.")
            profile_photo = PHOTO_TRADE  # Use the default photo if fetching fails
        
        # Send the photo with the final message and buttons
        await send_photo(update, context, profile_photo, final_message, reply_markup)
        logger.info("Successfully sent the combined trading message.")

    except Exception as e:
        logger.exception(f"Unexpected error in process_list: {e}")
        await send_message(update, context, "An error occurred while processing tokens. Please try again.")

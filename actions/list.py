from config import logger, BOT_USERNAME, MAX_LISTED_TOKENS
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import CallbackContext, ConversationHandler
from utils.createTradingLink import create_trading_link
from utils.reply import send_message, send_photo
from utils.getTokenMarketData import fetch_and_format_token_market_data
from utils.profilePhoto import fetch_user_profile_photo
from messages_photos import PHOTO_EXCHANGE, markdown_v2

# Configurable exchange message
EXCHANGE = (
    "*🚀 [{username_display} Exchange](https://t.me/{bot_username}?start) 🚀*\n\n"
    "👇 Click to buy my *#Top3* tokens:\n\n"
    "{tokens}"
    "💸 Let’s make some money!"
)

TOKEN_TEMPLATE = (
    "*{index}️⃣ [{symbol}]({trading_link})*\n"
    " ├ Price: *{price}*\n"
    " ├ 24H: *{change_24h}*\n"
    " ├ MCap: *${mcap}*\n\n"
    #"🔄 Circulating Supply: *{circulating_supply}*\n"
)


async def process_list(update: Update, context: CallbackContext) -> int:
    logger.info("Processing list request.")
    try:
        # Initialize tokens safely (default to an empty list if not found)
        tokens = context.user_data.get('tokens', [])

        # Safely fetch receiver data (ensure it's a dictionary)
        receiver_data = context.user_data.get('receiver', {})

        # Check for 'name' and 'tokens' in receiver data
        if receiver_data and 'name' in receiver_data and 'tokens' in receiver_data:
            username = receiver_data['name']
        else:
            # Fallback to 'tg_firstName' from 'auth_result'
            username = context.user_data.get('auth_result', {}).get('tg_firstName', "")

        # If still no username, use the bot's default username
        if not username:
            username = BOT_USERNAME

        # Check for tokens; if not found, send a warning and end conversation
        if not tokens:
            logger.warning("No tokens found in user data.")
            await send_message(update, context, "No tokens available for processing.")
            return ConversationHandler.END

        # Prepare combined message text and buttons
        combined_text = ""
        buttons = []
        max_tokens_to_process = min(len(tokens), MAX_LISTED_TOKENS)  # Limit to a maximum of 3 tokens
        max_buttons_to_process = min(len(tokens), MAX_LISTED_TOKENS)  # Limit to a maximum of 3 buttons

        # Iterate over the first max_tokens_to_process tokens and process them
        for idx in range(max_tokens_to_process):
            token = tokens[idx]  # Directly access the token by index

            try:
                symbol = token.get('symbol', '').strip().upper()
                chain_id = token.get('chain_id')
                contract_address = token.get('contract_address')
                decimals = token.get('decimals')
                trading_link = token.get('tradingLink')  # Retrieve the trading link early

                logger.info(f"Processing token {symbol} (Chain ID: {chain_id})")

                if not chain_id or not contract_address:
                    logger.warning(f"Skipping token {symbol} due to missing chain ID or contract address.")
                    continue  # Skip this token

                if not trading_link:
                    logger.error(f"Missing trading link for {symbol}.")
                    continue  # Skip this token if the trading link is not available

                # Use the trading link and proceed with other logic
                logger.info(f"Trading link for {symbol}: {trading_link}")

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
                    mcap=token_market_data.get('mcap', 'N/A'),
                    #volume_24h=token_market_data.get('volume_24h', 'N/A'),
                )

                # Append text to combined message
                combined_text += trading_card_text

                # Add a button only if the max_buttons_to_process limit is not exceeded
                if len(buttons) < max_buttons_to_process:
                    buttons.append(
                        InlineKeyboardButton(f"{symbol}", url=trading_link)
                    )

            except Exception as e:
                logger.exception(f"Error processing token {symbol}: {e}")
                continue  # Continue to the next token

        # Determine the correct label for number of tokens
        token_count_label = "Token" if max_tokens_to_process == 1 else "Tokens"

        # Logic to determine whether to add 's or just ' based on the username ending
        username_display = f"{username}'" if username.endswith('s') else f"{username}'s"

        # Create the final message using the EXCHANGE format
        final_message = markdown_v2(EXCHANGE.format(
            tokens=combined_text,
            username_display=username_display,  # Use the processed username
            bot_username=BOT_USERNAME,
            TOKEN_OR_TOKENS=token_count_label
        ))
        # Create reply markup with buttons in a single row
        reply_markup = InlineKeyboardMarkup([buttons]) if buttons else None

        # Fetch user's profile photo
        logger.info("Getting photo now.")

        # Attempt to fetch the user's profile photo
        #profile_photo = await fetch_user_profile_photo(update, context)
        profile_photo = PHOTO_EXCHANGE

        logger.info(f"Photo is {profile_photo}.")
        # If the profile photo fetch fails, use the default PHOTO_TRADE
        if not profile_photo:
            logger.warning(f"No profile photo available for user. Using default photo.")
            profile_photo = PHOTO_EXCHANGE  # Use the default photo if fetching fails

        # Send the photo with the final message and buttons
        await send_photo(update, context, profile_photo, final_message, reply_markup)
        logger.info("Successfully sent the combined trading message.")

    except KeyError as e:
        # Log unexpected missing keys and handle the error gracefully
        logger.error(f"Missing key in user data: {e}")
        await send_message(update, context, "An error occurred. Please try again.")
        return ConversationHandler.END
    except Exception as e:
        # Catch any other exceptions to prevent crashes
        logger.exception(f"Unexpected error: {e}")
        await send_message(update, context, "An unexpected error occurred.")
        return ConversationHandler.END

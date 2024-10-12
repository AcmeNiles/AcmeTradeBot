import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackContext
from config import SELECT_TOKEN, FEATURED_TOKENS, logger
from messages_photos import MESSAGE_NOT_LISTED, MESSAGE_ASK_TOKEN

# Ensure MESSAGE_ASK_TOKEN is defined correctly in messages_tokens
# MESSAGE_ASK_TOKEN = "You didn't provide a token. Please select one from the list below:"

async def handle_token(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    from .action_handler import execute_action

    """
    Handles the user's token input, validation, and proceeds with recipient/amount selection and execution.
    """
    # Log the incoming message or callback query
    if update.callback_query:
        logger.debug(f"Received callback query: {update.callback_query.data}")
        token_text = update.callback_query.data.split()[1]  # Extract token from callback data
    else:
        logger.debug(f"Received message: {update.message.text}")
        token_text = update.message.text.strip()  # Strip whitespace from the input

    logger.debug(f"Stripped token input: '{token_text}'")  # Log stripped token input
    token = parse_token(token_text)

    # Define featured tokens array
    featured_token_options = [
        InlineKeyboardButton(token_name, callback_data=f'/trade {token_name}')
        for token_name in FEATURED_TOKENS
    ]

    # Check if the context user data token is blank
    if not token_text or not context.user_data.get('token'):
        logger.info("No token provided.")
        reply_markup = InlineKeyboardMarkup([featured_token_options])
        await update.message.reply_text(
            MESSAGE_ASK_TOKEN, 
            reply_markup=reply_markup,
            parse_mode='MarkdownV2'  # Ensure MarkdownV2 is used
        )
        context.user_data['state'] = SELECT_TOKEN
        logger.debug("Prompted user to select a token due to blank input.")
        return SELECT_TOKEN

    logger.debug(f"Parsed token: {token}")  # Log the parsed token
    token_data = await validate_token(token, update, context)

    # Store the token in user_data if it's valid
    if token_data and "error" not in token_data:
        logger.info(f"Token validated: {token}")
        context.user_data['token'] = token_data
        logger.debug(f"Stored token in user data: {context.user_data['token']}")

        intent = context.user_data.get('intent')
        logger.debug(f"Current intent: {intent}")  # Log current intent
        if intent in {'pay', 'request'}:
            if 'recipient' not in context.user_data:
                logger.debug("Recipient not found in user data; proceeding to handle recipient.")
                return await handle_recipient(update, context)
            if 'amount' not in context.user_data:
                logger.debug("Amount not found in user data; proceeding to handle amount.")
                return await handle_amount(update, context)

        logger.info("Proceeding with action using token.")
        return await execute_action(update, context)

    # If token is invalid or not found
    logger.warning(f"Token not found or invalid: {token_text}")

    # Only send the "not listed" message if the token text is not blank
    if token_text:
        logger.debug(f"Token not listed. Showing request listing option for token: {token_text}")
        keyboard = [[InlineKeyboardButton("Request Listing", url="https://t.me/acmeonetap")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            MESSAGE_NOT_LISTED,
            reply_markup=reply_markup,
            parse_mode='MarkdownV2'  # Ensure MarkdownV2 is used
        )

    # Prompt user to select a valid token from the list
    reply_markup = InlineKeyboardMarkup([featured_token_options])
    await update.message.reply_text(
        f"TYPE or select a token to {context.user_data['intent']}", 
        reply_markup=reply_markup,
        parse_mode='MarkdownV2'
    )

    context.user_data['state'] = SELECT_TOKEN
    logger.debug("Prompted user to select a valid token due to invalid input.")
    return SELECT_TOKEN


# Fetch token data from external API
async def get_token(token_identifier: str):
    """
    Fetch token data from CoinGecko API based on the given token symbol or smart contract address.

    Args:
        token_identifier (str): The token symbol or smart contract address.

    Returns:
        dict: A dictionary containing token data including symbol, chainId, and contract_address.
              Returns an error message if the token is not found.
    """
    try:
        # Fetch token data from the specific CoinGecko endpoint
        url = f"https://api.coingecko.com/api/v3/coins/{token_identifier.lower()}"
        response = requests.get(url)

        # Log the request for debugging
        logger.debug(f"Fetching token data from CoinGecko: {url}")

        if response.status_code == 200:
            token_data = response.json()
            logger.debug(f"Token data from CoinGecko: {response.json()}")

            # Extract the required fields
            symbol = token_data.get("symbol")
            chain_id = token_data.get("blockchain_specific", {}).get("chain_id")  # Chain ID may be nested
            contract_address = token_data.get("contract_address")  # Contract address can also be nested

            # Ensure we have all necessary fields
            if symbol and chain_id and contract_address:
                return {
                    "symbol": symbol,
                    "chainId": chain_id,
                    "contract_address": contract_address
                }
            else:
                logger.warning("Token data missing required fields.")
                return {"error": "Token data is incomplete."}

        else:
            logger.error(f"Failed to fetch token data: {response.status_code}, {response.text}")
            return {"error": "Token not found."}

    except Exception as e:
        logger.exception(f"An error occurred while fetching token data: {str(e)}")
        return {"error": f"An error occurred: {str(e)}"}


def parse_token(token_text: str) -> str:
    """
    Parse and validate the token from user input.
    """
    token = token_text.strip().lower()
    return token if token else None

async def validate_token(token_identifier: str, update: Update, context: CallbackContext):
    """
    Validate the token identifier (symbol or address) by fetching its data.
    """
    token_data = await get_token(token_identifier)
    if isinstance(token_data, list):
        options = [InlineKeyboardButton(token['name'], callback_data=token['id']) for token in token_data]
        reply_markup = InlineKeyboardMarkup([options])
        await update.message.reply_text("Multiple tokens found. Please select one:", reply_markup=reply_markup)
        context.user_data['state'] = SELECT_TOKEN
        return None
    if "error" in token_data:
        return None
    return token_data
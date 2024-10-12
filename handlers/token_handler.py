import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, InputFile
from telegram.error import TelegramError
from telegram.ext import ContextTypes, CallbackContext
from config import SELECT_TOKEN

# Setup logging
logger = logging.getLogger(__name__)

TRADE_TOKENS = {
    "BRETT": {"chainId": "8453", "symbol":"BRETT", "tokenAddress": "0x532f27101965dd16442e59d40670faf5ebb142e4"},
    "PONKE": {"chainId": "solana", "symbol":"PONKE", "tokenAddress": "5z3EqYQo9HiCEs3R84RCDMu2n7anpDMxRhdK8PSWmrRC"},
    # Add more trade tokens as needed
}

# Mapping of tickers to chainId and token_address for payments
PAY_TOKENS = {
    "USDC": {"chainId": "42161", "symbol":"USDC", "tokenAddress": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831", "decimals":6},
    # Add more pay tokens as needed
}

# Define featured tokens as a list of strings
featured_tokens = ["PONKE", "POPCAT", "BRETT"]

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
        for token_name in featured_tokens
    ]

    # Check if the context user data token is blank
    if not token_text or not context.user_data.get('token'):
        logger.info("No token provided.")
        reply_markup = InlineKeyboardMarkup([featured_token_options])
        await update.message.reply_text(
            "You didn't provide a token. Please select one from the list below:", 
            reply_markup=reply_markup
        )
        context.user_data['state'] = SELECT_TOKEN
        logger.debug("Prompted user to select a token due to blank input.")
        return SELECT_TOKEN

    logger.debug(f"Parsed token: {token}")  # Log the parsed token
    token_data = await validate_token(token, update, context)

    if token_data and "error" not in token_data:  # If token is valid
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
    logger.warning("Token not found or invalid.")

    # Only send the "not listed" message if the token text is not blank
    if token_text:
        keyboard = [[InlineKeyboardButton("Request Listing", url="https://t.me/acmeonetap")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("🚫 This token is not listed. Please contact us to request listing:", reply_markup=reply_markup)

    # Prompt user to select a valid token from the list
    reply_markup = InlineKeyboardMarkup([featured_token_options])
    await update.message.reply_text(
        f"TYPE or select a token to {context.user_data['intent']}", 
        reply_markup=reply_markup
    )

    context.user_data['state'] = SELECT_TOKEN
    logger.debug("Prompted user to select a valid token due to invalid input.")
    return SELECT_TOKEN



# Fetch token data from external API
async def get_token(token_identifier: str):
    """
    Fetch token data from an external API based on the given token symbol or smart contract address.
    """
    url = f"https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids={token_identifier}"
    response = requests.get(url)
    token_data = response.json()
    if isinstance(token_data, list) and len(token_data) == 1:
        return token_data[0]
    elif isinstance(token_data, list) and len(token_data) > 1:
        return token_data
    else:
        return {"error": "Token not found."}


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
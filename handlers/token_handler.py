from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler
import requests
from config import logger, SELECT_TOKEN, SELECT_AMOUNT, SELECT_RECIPIENT, FEATURED_TOKENS, COINGECKO_API_URL
from messages_photos import MESSAGE_ASK_TOKEN, MESSAGE_NOT_LISTED

# EVM Chain ID Mapping
EVM_CHAIN_IDS = {
    "ethereum": 1,
    "polygon-pos": 137,
    "binance-smart-chain": 56,
    "base": 8453,
    "arbitrum-one": 42161,
    "optimistic-ethereum": 10,
}

async def handle_token(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    from handlers.input_handler import input_to_action
    from handlers.action_handler import execute_action

    """Main handler to process the token input and route based on intent."""
    intent = context.user_data.get('intent')

    # If intent is missing, fallback to menu (without a state)
    if not intent:
        return await input_to_action(update, context)

    # Get token input from the user
    token_text = await get_token_from_input(update, context)
    if not token_text:
        return await prompt_for_token(update, context)

    # Validate and store the token
    token_data = await validate_and_store_token(token_text, update, context)
    if not token_data:
        return await prompt_for_token(update, context, invalid=True)

    # Route based on intent
    if intent in {'pay', 'request'}:
        return await handle_intent_flow(update, context)

    # Execute trade directly
    return await execute_action(update, context)

async def get_token_from_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str | None:
    """Extract token from message or callback query."""
    if update.callback_query:
        data = update.callback_query.data.split()
        return data[1] if len(data) > 1 else None
    elif update.message and update.message.text.startswith(f'/{context.user_data.get("intent", "")}'):
        parts = update.message.text.split(maxsplit=1)
        return parts[1].strip() if len(parts) > 1 else None
    elif update.message:
        return update.message.text.strip()
    return None

async def validate_and_store_token(token_identifier: str, update: Update, context: ContextTypes.DEFAULT_TYPE) -> dict | None:
    """Validate the token and store it in context if valid."""
    token_data = await fetch_token_data(token_identifier)
    if token_data and "error" not in token_data:
        context.user_data['token'] = token_data  # Store token data
        logger.info(f"Stored token: {token_data}")
        return token_data
    return None

async def fetch_token_data(token_identifier: str) -> dict:
    """Fetch token data from CoinGecko API."""
    url = COINGECKO_API_URL.format(token_id=token_identifier.lower())
    try:
        response = requests.get(url)
        logger.debug(f"Fetching token data from: {url}")

        if response.status_code != 200:
            logger.error(f"Token fetch failed: {response.status_code}, {response.text}")
            return {"error": "Token not found."}

        token_data = response.json()
        return extract_token_data(token_data)

    except requests.exceptions.RequestException as e:
        logger.exception(f"Network error: {str(e)}")
        return {"error": f"Network error: {str(e)}"}

def extract_token_data(token_data: dict) -> dict | None:
    """Extract and validate token fields, including the largest logo."""
    try:
        # Common fields
        symbol = token_data.get('symbol')
        name = token_data.get('name')

        # Get the largest available logo
        logo_url = token_data['image'].get('large') or token_data['image'].get('small')

        asset_platform = token_data.get('asset_platform_id')
        detail_platforms = token_data.get('detail_platforms', {})
        platforms = token_data.get('platforms', {})

        # Get platform-specific data
        platform_key, platform_data = next(iter(detail_platforms.items()), (None, {}))
        if not platform_key or not platform_data:
            logger.warning(f"Platform data missing for token: {token_data}")
            return {"error": "Platform data missing."}

        decimals = platform_data.get('decimal_place')
        contract_address = platform_data.get('contract_address') or platforms.get(platform_key)

        # Handle EVM chain IDs or non-EVM platforms
        if asset_platform in EVM_CHAIN_IDS:
            chain_id = EVM_CHAIN_IDS[asset_platform]
        else:
            chain_id = asset_platform  # Non-EVM platforms retain the original string

        # Validate extracted data
        if all([symbol, name, logo_url, chain_id, decimals, contract_address]):
            return {
                "symbol": symbol,
                "name": name,
                "logoUrl": logo_url,
                "chain_id": chain_id,
                "decimals": decimals,
                "contract_address": contract_address,
                "platform": platform_key,
            }

        logger.warning(f"Incomplete token data: {token_data}")
        return {"error": "Incomplete token data."}

    except KeyError as e:
        logger.exception(f"Missing field: {str(e)}")
        return {"error": "Incomplete token data."}

async def prompt_for_token(update: Update, context: ContextTypes.DEFAULT_TYPE, invalid=False) -> int:
    """Prompt user to enter or select a token."""

    logger.info("Entered prompt_for_token function.")

    # Determine the message to send based on whether the token is invalid
    message = MESSAGE_NOT_LISTED if invalid else MESSAGE_ASK_TOKEN

    # Check the user context for the current intent
    user_intent = context.user_data.get("intent", "trade")  # Default to 'trade'
    logger.debug(f"User intent for token selection: {user_intent}")

    # Prepare buttons for token selection
    buttons = [
        InlineKeyboardButton(token_name, callback_data=f'/{user_intent} {token_name}')
        for token_name in FEATURED_TOKENS
    ]

    # Create the reply markup
    reply_markup = InlineKeyboardMarkup([buttons])

    # Handle both callback query and message text scenarios
    if update.callback_query:
        # If it's a callback query, acknowledge the button click
        await update.callback_query.answer()

        # Send the message with the token selection options
        try:
            await update.callback_query.message.reply_text(
                message, reply_markup=reply_markup, parse_mode='MarkdownV2'
            )
            logger.info("Token selection prompt sent successfully in response to button click.")
        except Exception as e:
            logger.error(f"Failed to send token selection prompt in callback: {str(e)}")
            await update.callback_query.message.reply_text("An error occurred while prompting for a token. Please try again.")

    else:
        # If it's a message text, simply send the prompt
        try:
            await update.message.reply_text(
                message, reply_markup=reply_markup, parse_mode='MarkdownV2'
            )
            logger.info("Token selection prompt sent successfully in response to message text.")
        except Exception as e:
            logger.error(f"Failed to send token selection prompt in message: {str(e)}")
            await update.message.reply_text("An error occurred while prompting for a token. Please try again.")

    return SELECT_TOKEN


async def handle_intent_flow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle flow for pay/request intents."""
    if 'recipient' not in context.user_data:
        return await handle_recipient(update, context)
    if 'amount' not in context.user_data:
        return await handle_amount(update, context)
    return await execute_action(update, context)

async def handle_recipient(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Prompt user for recipient details."""
    await update.message.reply_text("Please enter the recipient address:")
    return SELECT_RECIPIENT

async def handle_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Prompt user for amount."""
    await update.message.reply_text("Enter the amount:")
    return SELECT_AMOUNT
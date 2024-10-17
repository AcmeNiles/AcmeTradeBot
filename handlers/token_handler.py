from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler
import requests
from utils.reply import send_photo
from config import logger, SELECT_TOKEN, SELECT_AMOUNT, SELECT_RECIPIENT, FEATURED_TOKENS_PAY,FEATURED_TOKENS_TRADE, LIFI_API_URL, SUPPORTED_CHAIN_IDS
from messages_photos import ASK_TOKEN, NOT_LISTED, PHOTO_TRADE, markdown_v2

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
    """Main handler to process the token input and route based on intent."""

    logger.debug("Handling token input for user: %s with intent: %s", update.effective_user.id, context.user_data.get("intent") )

    # Get requested tokens from user context data
    requested_tokens = context.user_data.get("token", [])
    logger.debug("Requested tokens from user context: %s", requested_tokens)

    # If no token is provided, prompt for input
    if not requested_tokens:
        logger.warning("No token input provided by user: %s", update.effective_user.id)
        return await prompt_for_token(update, context)

    # Validate tokens and store the valid ones
    invalid_tokens = await validate_and_store_tokens(requested_tokens, update, context)
    logger.debug("Validation result - Invalid tokens: %s", invalid_tokens)

    # If invalid tokens found, notify the user
    if invalid_tokens:
        logger.warning("User provided invalid tokens: %s", invalid_tokens)
        return await prompt_for_token(update, context, invalid_tokens=invalid_tokens)

    # Log valid tokens before proceeding
    logger.info("Valid tokens for user %s: %s", update.effective_user.id, requested_tokens)

    # Proceed with further actions (like executing intent) after token validation
    logger.info("Proceeding with valid tokens for user: %s", update.effective_user.id)
    return True

async def prompt_for_token(update: Update, context: ContextTypes.DEFAULT_TYPE, invalid_tokens=None) -> int:
    """Prompt the user to enter or select a token."""
    user_intent = context.user_data.get("intent", "trade")  # Default intent is 'trade'

    if invalid_tokens:
        # Create a formatted message for invalid tokens
        invalid_tokens_text = ", ".join(invalid_tokens)
        verb = "is" if len(invalid_tokens) == 1 else "are"
        caption = markdown_v2(NOT_LISTED.format(tokens_text=invalid_tokens_text, verb=verb))
        photo_url = PHOTO_TRADE  # Replace with your actual image URL

        logger.warning(f"Invalid token(s) entered: {invalid_tokens_text}")

        # Prepare buttons
        buttons = [
            InlineKeyboardButton(
                "👋 Request Listing", 
                url=context.user_data.get('invite_link', 'https://t.me/acmeonetap')
            ),
            InlineKeyboardButton("❌ Cancel", callback_data='cancel')
        ]
    else:
        # Determine the token count message based on intent
        token_count = "a token" if user_intent != 'list' else "one or more tokens"
        caption = ASK_TOKEN.format(token_count=token_count, intent_type=user_intent)
        photo_url = PHOTO_TRADE  # Replace with your actual image URL

        logger.debug(f"Prompting user to select {token_count} for {user_intent}.")

        # Choose the featured tokens based on the intent
        if user_intent == 'pay':
            featured_tokens = FEATURED_TOKENS_PAY
        else:
            featured_tokens = FEATURED_TOKENS_TRADE

        # Prepare buttons for token selection
        buttons = [
            InlineKeyboardButton(token_name, callback_data=f'/{user_intent} {token_name}')
            for token_name in featured_tokens
        ]

    # Send the photo to the user with the caption and buttons
    await send_photo(
        update,
        context,
        photo_url=photo_url,
        caption=caption,
        reply_markup=InlineKeyboardMarkup([buttons])
    )

    return SELECT_TOKEN


async def validate_and_store_tokens(requested_tokens: list, update: Update, context: ContextTypes.DEFAULT_TYPE) -> tuple:
    """Validate requested tokens against the LiFi API and store valid tokens in user context."""

    valid_tokens = []
    invalid_tokens = []

    # Iterate through each requested token
    for token in requested_tokens:
        logger.debug(f"Starting validation for token: {token}")

        # Fetch token data from LiFi API across all supported chains
        token_data = await fetch_token_data(token)  # Function to fetch token data

        if token_data and "error" not in token_data:
            valid_tokens.append(token_data)  # Store valid token data
            logger.info(f"Valid token found: {token_data}")
        else:
            invalid_tokens.append(token)  # Store the invalid token
            logger.warning(f"Token data fetch failed or token is invalid: {token_data}")

    # Store only valid tokens in user context
    context.user_data['tokens'] = valid_tokens  # Retain original data structure
    logger.debug(f"Final valid tokens stored in context: {context.user_data['tokens']}")
    logger.info(f"Validation complete. Valid tokens: {valid_tokens}, Invalid tokens: {invalid_tokens}")

    return invalid_tokens


async def fetch_token_data(token: str) -> dict:
    """Fetch token data from LiFi API across supported chains."""

    url = f"{LIFI_API_URL}/token"  # Updated URL to include /token
    logger.debug(f"Preparing to fetch token data for token: '{token}' from URL: {url}")

    for chain_id, platform_name in SUPPORTED_CHAIN_IDS.items():
        logger.debug(f"Fetching token data for '{token}' on chain ID '{chain_id}' ({platform_name})")

        try:
            response = requests.get(url, params={"chain": chain_id, "token": token})
            logger.debug(f"Received response status code: {response.status_code}")

            if response.status_code != 200:
                logger.warning(f"Token fetch failed for '{token}' on chain '{chain_id}' with status code: {response.status_code}")
                continue  # Move to the next chain if the request fails

            token_data = response.json()
            logger.debug(f"Token data fetched for '{token}' on chain '{chain_id}': {token_data}")

            extracted_data = extract_token_data(token_data)  # Ensure you define this function
            logger.debug(f"Extracted token data: {extracted_data}")

            # Check if price is valid
            price_str = extracted_data.get('price', '0')  # Fetch from extracted_data
            decimals= extracted_data.get('decimals', 2)  # Fetch from extracted_data or use default

            # Clean and convert price string
            price_str_clean = price_str.replace('$', '').replace(',', '')

            try:
                # Convert to float and check if the price is greater than 0
                price = float(price_str_clean)
                # Format the float to have the number of decimal places specified by 'decimals'
                price = round(price, decimals)
                logger.debug(f"Extracted token priceeee: {price>0}")

                if price > 0:
                    # Format the price based on the number of decimals
                    formatted_price = f"{price:.{decimals}f}"
                    logger.info(f"Valid token found for '{token}' on chain '{chain_id}': {formatted_price}")
                    return extracted_data  # Return immediately if valid token data is found
                else:
                    logger.warning(f"Token '{token}' on chain '{chain_id}' has invalid price: {price}")
                    continue  # Move to the next chain if price is not greater than 0

            except ValueError as e:
                logger.error(f"Error converting price to float: {e}")
                continue  # Skip to the next chain if there's a conversion error

        except requests.exceptions.RequestException as e:
            logger.exception(f"Network error while fetching token data for '{token}' on chain '{chain_id}': {str(e)}")
            continue  # Continue to the next chain on network errors

    logger.warning(f"Token '{token}' is invalid across all supported chains.")
    return {"error": "Token not found or price is invalid."}

def extract_token_data(token_data: dict) -> dict | None:
    """Extract and validate token fields from LiFi API response."""
    logger.debug(f"Extracting token data from response: {token_data}")

    try:
        symbol = token_data.get('symbol')
        name = token_data.get('name')
        logo_url = token_data.get('logoURI')
        chain_id = token_data.get('chainId')
        decimals = token_data.get('decimals')
        contract_address = token_data.get('address')
        price = token_data.get('priceUSD')

        logger.debug(f"Extracted fields - Symbol: {symbol}, Name: {name}, Logo URL: {logo_url}, "
                     f"Chain ID: {chain_id}, Decimals: {decimals}, "
                     f"Contract Address: {contract_address}, Price: {price}")

        # Validate that the necessary fields are present
        if all([symbol, name, logo_url, chain_id, decimals, contract_address]):
            formatted_price = f"${float(price):,.{decimals}f}" if price else "N/A"
            logger.debug(f"All necessary fields are present. Formatted price: {formatted_price}")
            return {
                "symbol": symbol,
                "name": name,
                "logoUrl": logo_url,
                "chain_id": chain_id,
                "decimals": decimals,
                "contract_address": contract_address,
                "price": formatted_price
            }

        logger.warning(f"Incomplete token data: {token_data}")
        return {"error": "Incomplete token data."}

    except KeyError as e:
        logger.exception(f"Missing field in token data: {str(e)}")
        return {"error": "Incomplete token data."}
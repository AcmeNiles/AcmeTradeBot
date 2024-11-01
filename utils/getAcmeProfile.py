import aiohttp
from config import logger
from config import ACME_URL
from telegram import Update
from telegram.ext import ContextTypes
from utils.tokenValidator import validate_tokens
from config import logger, MAX_LISTED_TOKENS

ACME_API_URL_PROFILE = f"{ACME_URL}/checkout/user/get-public-profile"
ACME_API_URL_TOKENS = f"{ACME_URL}/checkout/intent/get-user-listed-tokens"

async def get_acme_public_profile(username: str) -> dict:
    """Fetch Acme public profile for a given username."""
    if username.startswith('@'):
        username = username[1:]

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{ACME_API_URL_PROFILE}?userName={username}") as response:
                logger.info(f"{ACME_API_URL_PROFILE}?userName={username}")
                if response.status == 200:
                    acme_user_data = await response.json()
                    logger.info(f"Successfully retrieved Acme profile for username: {username}")
                    return acme_user_data.get('data')  # Return only the 'data' field
                else:
                    logger.error(f"Failed to retrieve Acme profile for username: {username}. Status code: {response.status}")
                    return None
    except aiohttp.ClientError as e:
        logger.error(f"Error fetching Acme profile for username: {username}. Exception: {e}")
        return None


async def get_user_listed_tokens(user_id: str) -> list:
    """Fetch the list of tokens listed by a given user."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{ACME_API_URL_TOKENS}?userId={user_id}") as response:
                if response.status == 200:
                    token_data = await response.json()
                    logger.info(f"Successfully retrieved tokens for user ID: {user_id}")
                    return token_data.get('data', [])
                else:
                    logger.error(f"Failed to retrieve tokens for user ID: {user_id}. Status code: {response.status}")
                    return []
    except aiohttp.ClientError as e:
        logger.error(f"Error fetching tokens for user ID: {user_id}. Exception: {e}")
        return []
        
async def validate_user_and_tokens(receiver_username: str, update: Update, context: ContextTypes.DEFAULT_TYPE) -> tuple:
    """Validate the user and their tokens, and return the valid ones."""
    from handlers.auth_handler import get_user_top3
    logger.debug("Validating receiver username: %s", receiver_username)

    # Fetch the user's public profile from Acme
    
    acme_user_data = await get_acme_public_profile(receiver_username)
    if not acme_user_data or not acme_user_data.get('id'):
        error_message = "User is not on Acme yet." if not acme_user_data else "Invalid user data."
        logger.error("Receiver validation failed: %s", error_message)
        return None, None, error_message

    # Check if top3 tokens are already stored
    valid_tokens = await get_user_top3(update, context, receiver_username)
    if valid_tokens:
        logger.info("Top3 tokens already exist for user: %s", update.effective_user.id)
        return acme_user_data, valid_tokens, None  # Early return if tokens are present

    # List tokens for the user
    user_id = acme_user_data['id']
    logger.debug("Fetched user ID: %s, Username: %s", user_id, receiver_username)
    listed_tokens = await get_user_listed_tokens(user_id)
    logger.debug("Listed tokens for user ID %s: %s", user_id, listed_tokens)

    if not listed_tokens:
        logger.warning("No tokens listed for user ID: %s", user_id)
        return None, None, "No tokens found for the user."

    # Validate tokens and separate valid and invalid tokens
    valid_tokens, invalid_tokens = await validate_tokens(listed_tokens[:MAX_LISTED_TOKENS], update, context)
    if invalid_tokens:
        logger.warning("Invalid tokens found for user ID %s: %s", user_id, invalid_tokens)
        return None, None, "Invalid tokens found."

    logger.info("Receiver and tokens successfully validated for username: %s", receiver_username)
    return acme_user_data, valid_tokens, None


async def process_user_top3(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Validate the user and store their top3 in bot_data."""
    from handlers.auth_handler import get_auth_result, get_user_top3, store_user_top3

    # Retrieve the auth result using the function
    auth_result = await get_auth_result(update, context)
    if not auth_result or auth_result.get('url') == 'url':
        logger.warning("User is not authenticated: %s", update.effective_user.id)
        return None, None, "User is not authenticated."

    # Check if top3 tokens are already stored
    user_tg_username = update.effective_user.username
    top3_tokens = await get_user_top3(update, context)
    if top3_tokens:
        logger.info("Top3 tokens already exist for user: %s", update.effective_user.id)
        return True  # Early return if tokens are present

    # Retrieve the Acme ID and listed tokens for validation
    acme_id = auth_result.get('acme_id')
    listed_tokens = await get_user_listed_tokens(acme_id)
    if not listed_tokens:
        logger.warning("No tokens listed for user ID: %s", acme_id)
        return None, None, "No tokens found for the user."

    # Validate the listed tokens and store only the valid ones
    valid_tokens, invalid_tokens = await validate_tokens(listed_tokens[:MAX_LISTED_TOKENS], update, context)
    if invalid_tokens:
        logger.warning("Invalid tokens found: %s", invalid_tokens)

    # Store the valid tokens in top3 for the user
    await store_user_top3(update, context, valid_tokens)

    logger.info("Top3 tokens successfully processed and stored for user: %s", update.effective_user.id)
    return True

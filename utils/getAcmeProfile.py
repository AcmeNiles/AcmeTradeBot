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
    logger.debug("Validating receiver username: %s", receiver_username)

    acme_user_data = await get_acme_public_profile(receiver_username)
    if not acme_user_data or not acme_user_data.get('id'):
        error_message = "User is not on Acme yet." if not acme_user_data else "Invalid user data."
        logger.error("Receiver validation failed: %s", error_message)
        return None, None, error_message

    user_id = acme_user_data['id']
    listed_tokens = await get_user_listed_tokens(user_id)

    if not listed_tokens:
        logger.warning("No tokens listed for user ID: %s", user_id)
        return None, None, "No tokens found for the user."

    valid_tokens, invalid_tokens = await validate_tokens(listed_tokens[:MAX_LISTED_TOKENS], update, context)
    if invalid_tokens:
        logger.warning("Invalid tokens found: %s", invalid_tokens)
        return None, None, "Invalid tokens found."

    logger.info("Receiver and tokens successfully validated for username: %s", receiver_username)
    return acme_user_data, valid_tokens, None

async def process_user_tokens(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Validate the user and store their auth_result in context.user_data."""

    # Check if auth_result exists and is valid
    auth_result = context.user_data.get('auth_result')
    if not auth_result or auth_result.get('url') == 'url':
        logger.warning("User is not authenticated: %s", update.effective_user.id)
        return None, None, "User is not authenticated."

    # Check if tokens are already stored
    tokens = auth_result.get('tokens')
    if tokens:
        logger.info("Tokens already exist for user: %s", update.effective_user.id)
        return True  # Early return if tokens are present

    acme_id = auth_result.get('acme_id')
    listed_tokens = await get_user_listed_tokens(acme_id)

    if not listed_tokens:
        logger.warning("No tokens listed for user ID: %s", acme_id)
        return None, None, "No tokens found for the user."

    # Validate and store tokens
    valid_tokens, invalid_tokens = await validate_tokens(listed_tokens[:MAX_LISTED_TOKENS], update, context)
    if invalid_tokens:
        logger.warning("Invalid tokens found: %s", invalid_tokens)

    # Update user data with valid tokens
    auth_result['tokens'] = valid_tokens
    context.user_data['auth_result'] = auth_result  # Update the context

    logger.info("Auth result with user data and tokens successfully processed for user: %s", update.effective_user.id)

    return True
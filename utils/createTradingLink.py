import aiohttp
import asyncio

from telegram import Update
from telegram.ext import ContextTypes

from config import logger, DEFAULT_ACME_API_KEY, ACME_URL, DEFAULT_TIMEOUT, RETRY_COUNT
from utils.reply import send_error_message  # Ensure you import the necessary utility functions


async def create_trading_link(update: Update,
    context: ContextTypes.DEFAULT_TYPE, chain_id: str, token_address: str, redirect_url: str
) -> str:
    """
    Create a trading link using the provided parameters and Telegram key.
    Sends a failure message if the operation fails or times out.

    Args:
        context (ContextTypes.DEFAULT_TYPE): Telegram context containing user data.
        chain_id (str): Blockchain ID for the token.
        token_address (str): Contract address of the token.
        redirect_url (str): URL to redirect after the trading action.

    Returns:
        str: The minting link returned from the API.

    Raises:
        ValueError: If any required argument is missing or if the API request fails.
    """
    from handlers.auth_handler import get_auth_result

    # Get API key from user data or fallback to default
    auth_result = await get_auth_result(update, context)
    acme_api_key = auth_result.get('api_key') if auth_result and 'api_key' in auth_result else DEFAULT_ACME_API_KEY

    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "X-API-KEY": acme_api_key,
    }

    # Adjust chain ID if necessary
    chain_id = 'solana' if str(chain_id) == "1151111081099710" else str(chain_id)

    acme_api = f"{ACME_URL}/dev/intent/create-buy-purchase-link-intent"

    # Prepare the payload
    payload = {
        "chainId": chain_id,
        "tokenAddress": token_address,
        "redirectUrl": redirect_url,
    }

    #logger.debug(f"Calling Trade: {acme_api} {headers} {payload}")
    
    for attempt in range(RETRY_COUNT):
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=DEFAULT_TIMEOUT)) as session:
            try:
                async with session.post(acme_api, json=payload, headers=headers) as response:
                    logger.debug(f"Response: {response.status}, Content: {await response.text()}")
    
                    if response.status == 200:
                        data = await response.json()
                        return data.get('data')
    
                    logger.error(f"Failed on attempt {attempt + 1}. Status: {response.status}")
                    response.raise_for_status()
    
            except asyncio.TimeoutError:
                logger.error(f"Attempt {attempt + 1}: Request to create trading link timed out.")
            except aiohttp.ClientError as e:
                logger.exception(f"Attempt {attempt + 1}: Request failed: {str(e)}")
            except Exception as e:
                logger.error(f"Unexpected error on attempt {attempt + 1}: {str(e)}")
    
    # Raise a ValueError to indicate failure after retries
    raise ValueError("Failed to create trading link after multiple attempts.")
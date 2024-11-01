import asyncio
import aiohttp

# Import constants from config
from config import logger, RETRY_COUNT, DEFAULT_TIMEOUT, ACME_URL, ACME_API_KEY

async def store_tokens_to_acme(dex_aggregator_id: str, currencies: list) -> dict:
    """
    Store tokens to the Acme API for the specified DEX aggregator.

    Args:
        dex_aggregator_id (str): DEX aggregator identifier (e.g., "LiFi").
        currencies (list): List of currency dictionaries with required token details.

    Returns:
        dict: Response data from the API containing token objects, or error details.

    Raises:
        ValueError: If all retry attempts fail or if there's an unexpected error.
    """
    url = f"{ACME_URL}/telegram/currency/create-or-update-for-dex-aggregator"

    headers = {
        "X-API-KEY": ACME_API_KEY,
        "Content-Type": "application/json"
    }

    payload = {
        "dexAggregatorId": dex_aggregator_id,
        "currencies": currencies
    }

    for attempt in range(RETRY_COUNT):
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=DEFAULT_TIMEOUT)) as session:
            try:
                async with session.post(url, json=payload, headers=headers) as response:
                    logger.debug(f"Attempt {attempt + 1}: Storing tokens to {url}")

                    if response.status == 200:
                        data = await response.json()
                        logger.debug(f"Response: {data}")
                        return data

                    logger.error(f"Attempt {attempt + 1} failed with status: {response.status}")
                    response.raise_for_status()

            except asyncio.TimeoutError:
                logger.error(f"Attempt {attempt + 1}: Request to store tokens timed out.")
            except aiohttp.ClientError as e:
                logger.exception(f"Attempt {attempt + 1}: Client error occurred: {str(e)}")
            except Exception as e:
                logger.error(f"Unexpected error on attempt {attempt + 1}: {str(e)}")

    # Raise an exception if all attempts fail
    raise ValueError("Failed to store tokens to Acme after multiple attempts.")


async def get_all_currencies(chain_id=None) -> list:
    """
    Fetch all currencies available for a specified chain ID.

    Args:
        chain_id (str, optional): Blockchain ID, 'solana' or '8453' or None to fetch all.

    Returns:
        list: A list of token objects if successful.

    Raises:
        ValueError: If the request fails after retries or times out.
    """
    url = f"{ACME_URL}/currencies"
    if chain_id in ["solana", "8453"]:
        url += f"&chainId={chain_id}"

    for attempt in range(RETRY_COUNT):
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=DEFAULT_TIMEOUT)) as session:
            try:
                async with session.get(url) as response:
                    logger.debug(f"Attempt {attempt + 1}: Fetching currencies from {url}")

                    if response.status == 200:
                        data = await response.json()
                        logger.debug(f"Response: {data}")
                        return data

                    logger.error(f"Attempt {attempt + 1} failed with status: {response.status}")
                    response.raise_for_status()

            except asyncio.TimeoutError:
                logger.error(f"Attempt {attempt + 1}: Request timed out.")
            except aiohttp.ClientError as e:
                logger.exception(f"Attempt {attempt + 1}: Client error occurred: {str(e)}")
            except Exception as e:
                logger.error(f"Unexpected error on attempt {attempt + 1}: {str(e)}")

    # Raise an exception if all attempts fail
    raise ValueError("Failed to fetch currencies after multiple attempts.")

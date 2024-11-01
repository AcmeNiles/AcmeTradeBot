import aiohttp
import asyncio
from config import logger, DEFAULT_TIMEOUT, RETRY_COUNT, DEFAULT_ACME_API_KEY

async def get_acme_api_key(update, context):
    from handlers.auth_handler import get_auth_result
    """Retrieve the API key from user data, falling back to default if unavailable."""
    user_data = await get_auth_result(update, context)
    return user_data.get("api_key", DEFAULT_ACME_API_KEY)


async def api_post_with_retries(url, headers, payload):
    """Helper function to perform a POST request with retries."""
    for attempt in range(RETRY_COUNT):
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=DEFAULT_TIMEOUT)) as session:
            try:
                logger.debug(f"POST Request to {url} | Attempt {attempt + 1} | Headers: {headers} | Payload: {payload}")
                async with session.post(url, json=payload, headers=headers) as response:
                    logger.debug(f"Response: {response.status}, Content: {await response.text()}")

                    if response.status == 200:
                        data = await response.json()
                        return data.get('data')

                    logger.error(f"Failed on attempt {attempt + 1}. Status: {response.status}")
                    response.raise_for_status()

            except asyncio.TimeoutError:
                logger.error(f"Attempt {attempt + 1}: Request to {url} timed out.")
            except aiohttp.ClientError as e:
                logger.exception(f"Attempt {attempt + 1}: POST request failed: {str(e)}")
            except Exception as e:
                logger.error(f"Unexpected error on attempt {attempt + 1}: {str(e)}")

    raise ValueError("POST request failed after multiple attempts.")


async def api_get_with_retries(url, headers):
    """Helper function to perform a GET request with retries."""
    for attempt in range(RETRY_COUNT):
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=DEFAULT_TIMEOUT)) as session:
            try:
                logger.debug(f"GET Request to {url} | Attempt {attempt + 1} | Headers: {headers}")
                async with session.get(url, headers=headers) as response:
                    logger.debug(f"Response: {response.status}, Content: {await response.text()}")

                    if response.status == 200:
                        data = await response.json()
                        return data.get('data')

                    logger.error(f"Failed on attempt {attempt + 1}. Status: {response.status}")
                    response.raise_for_status()

            except asyncio.TimeoutError:
                logger.error(f"Attempt {attempt + 1}: Request to {url} timed out.")
            except aiohttp.ClientError as e:
                logger.exception(f"Attempt {attempt + 1}: GET request failed: {str(e)}")
            except Exception as e:
                logger.error(f"Unexpected error on attempt {attempt + 1}: {str(e)}")

    raise ValueError("GET request failed after multiple attempts.")
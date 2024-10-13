import requests
from config import ACME_API_KEY, ACME_URL, logger

async def create_trading_link(tg_key: str, chain_id: str, token_address: str, redirect_url: str) -> str:
    """
    Create a trading link using the provided parameters and Telegram key.

    Args:
        tg_key (str): The Telegram key to be included in the request headers.
        chain_id (str): The blockchain ID for the token.
        token_address (str): The contract address of the token.
        redirect_url (str): The URL to redirect after the trading action.

    Returns:
        str: The minting link returned from the API.

    Raises:
        ValueError: If any required argument is missing or if the API request fails.
    """
    # Prepare the headers with API key and tg_key
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "X-API-KEY": ACME_API_KEY,
        'X-Secure-TG-User-Info': tg_key  # Include tg_key in headers
    }

    # Prepare the payload using function arguments
    payload = {
        "chainId": chain_id,
        "tokenAddress": token_address,
        "redirectUrl": redirect_url
    }

    # Construct the request URL
    url_to_post = f"{ACME_URL}/intent/create-buy-purchase-link-intent"

    try:
        # Send POST request
        response = requests.post(url_to_post, json=payload, headers=headers)

        # Log the response for debugging purposes
        logger.debug(f"POST request sent to: {url_to_post}, Response: {response.status_code}, Content: {response.content}")

        # Check if the response status is OK (200)
        if response.status_code == 200:
            # Parse the response to get the minting link
            response_data = response.json()
            return response_data.get('data')
        else:
            logger.error(f"Failed to create trading link from Acme. Status code: {response.status_code}, Content: {response.content}")
            response.raise_for_status()  # Raise an HTTPError for bad responses

    except requests.exceptions.RequestException as e:
        logger.exception(f"Request to Acme API failed: {str(e)}")
        raise ValueError(f"Failed to create trading link due to a request error: {str(e)}")

    except ValueError as ve:
        logger.exception(f"Value error while creating trading link: {str(ve)}")
        raise ve  # Re-raise the ValueError for further handling if necessary

    except Exception as e:
        logger.exception(f"An unexpected error occurred while obtaining the trading link from Acme: {str(e)}")
        raise ValueError(f"An unexpected error occurred while obtaining the trading link from Acme: {str(e)}")

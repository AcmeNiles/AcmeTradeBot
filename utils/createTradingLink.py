import requests
from config import ACME_API_KEY, ACME_URL, logger
from telegram.ext import ContextTypes

async def create_trading_link(context: ContextTypes.DEFAULT_TYPE, chain_id: str, token_address: str, redirect_url: str) -> str:
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
    
    # Construct the request URL
    url = f"{ACME_URL}/dev/intent/create-buy-purchase-link-intent"
    #url = "https://acme-prod.fly.dev/operations/dev/intent/create-buy-purchase-link-intent"
    #ACME_API_KEY = "PRCAEUY-LA6UTNQ-XYL5DEI-ZNUEMDA"
    # Prepare the headers with API key and tg_key
    acme_api_key = context.user_data.get("auth_result", {}).get("api_key", ACME_API_KEY)

    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "X-API-KEY": acme_api_key,
    }

    chain_id = str(chain_id)
    # Modify the chain ID if it matches the specific value (string comparison)
    if chain_id == "1151111081099710":
        chain_id = 'solana'

    # Prepare the payload using function arguments
    payload = {
        "chainId": f"{chain_id}",  # Use f-string for chainId
        "tokenAddress": f"{token_address}",  # Use f-string for tokenAddress
        "redirectUrl": f"{redirect_url}"  # Use f-string for redirectUrl
    }
    
    try:
        logger.debug(f"Calling Trade: {url} {headers} {payload}")

        # Send POST request
        response = requests.post(url, json=payload, headers=headers)

        # Log the response for debugging purposes
        logger.debug(f"POST request sent to: {url}, Response: {response.status_code}, Content: {response.content}")

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

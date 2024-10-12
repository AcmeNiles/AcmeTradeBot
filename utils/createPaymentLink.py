import requests
from config import ACME_API_KEY, ACME_URL, logger

def create_pay_link(tg_key: str, chain_id: str, token_address: str, amount: float, to: str, redirect_url: str) -> str:
    """
    Create a payment link using the provided parameters and Telegram key.

    Args:
        tg_key (str): The Telegram key to be included in the request headers.
        chain_id (str): The blockchain ID for the token.
        token_address (str): The contract address of the token.
        amount (float): The amount to be paid.
        to (str): The recipient address for the payment.
        redirect_url (str): The URL to redirect after the payment.

    Returns:
        str: The payment link returned from the API.

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
        "contractAddress": token_address,
        "to": to,  # Use the provided recipient address
        "amount": str(amount),  # Convert amount to string
        "intentLimit": 1,
        "redirectUrl": redirect_url
    }

    # Construct the request URL
    url_to_post = f"{ACME_URL}/intent/create-pay-intent"

    try:
        # Send POST request
        response = requests.post(url_to_post, json=payload, headers=headers)

        # Log the response for debugging purposes
        logger.debug(f"POST request sent to: {url_to_post}, Response: {response.status_code}, Content: {response.content}")

        # Check if the response status is OK (200)
        if response.status_code == 200:
            # Parse the response to get the payment link
            response_data = response.json()
            return response_data.get('data')
        else:
            logger.error(f"Failed to create payment link from Acme. Status code: {response.status_code}, Content: {response.content}")
            response.raise_for_status()  # Raise an HTTPError for bad responses

    except requests.exceptions.RequestException as e:
        logger.exception(f"Request to Acme API failed while creating payment link: {str(e)}")
        raise ValueError(f"Failed to create payment link due to a request error: {str(e)}")

    except ValueError as ve:
        logger.exception(f"Value error while creating payment link: {str(ve)}")
        raise ve  # Re-raise the ValueError for further handling if necessary

    except Exception as e:
        logger.exception(f"An unexpected error occurred while obtaining the payment link from Acme: {str(e)}")
        raise ValueError(f"An unexpected error occurred while obtaining the payment link from Acme: {str(e)}")

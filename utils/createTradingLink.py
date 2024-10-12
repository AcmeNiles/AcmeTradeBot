import os
import requests
from utils.createJWT import create_jwt  # Import hashing function
from config import ACME_API_KEY, ACME_URL

def create_trading_link(user_data, chain_id, token_address, redirect_url):
    # Fetch Acme URL and API key from environment variables
    acme_url = ACME_URL
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "X-API-KEY": ACME_API_KEY
    }

    # Hash the user data for the "memo" field
    user_data_jwt = create_jwt(user_data)

    # Prepare the payload using function arguments
    payload = {
        "chainId": chain_id,
        "tokenAddress": token_address,
        "redirectUrl": redirect_url,
        "memo": user_data_jwt
    }

    # Send the POST request with the updated payload
    response = requests.post(acme_url + "intent/create-buy-purchase-link-intent", json=payload, headers=headers)

    if response.status_code == 200:
        # Parse the response to get the minting link
        response_data = response.json()
        return response_data.get('data')
    else:
        response.raise_for_status()
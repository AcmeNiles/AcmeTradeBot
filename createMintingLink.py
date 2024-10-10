import os
import requests
from utils.createJWT import create_jwt  # Import hashing function
from config import ACME_API_KEY, ACME_URL

mint_payload = {
    "chainId": "42161",
    "contractAddress": "0xA3090C10b2dD4B69A594CA4dF7b1F574a8D0B476",
    "name": "Coyote Early Pass",
    "description": "The Coyote Early Pass unlocks exclusive perks for early bird users of Acme. Thank you for supporting us! 😊.",
    "imageUri": "https://imagedelivery.net/P5lw0bNFpEj9CWud4zMJgQ/feecc12a-109f-417d-ed17-b5cee8fd1a00/public",
    "websiteUrl": "https://www.acme.am",
    "intentLimit": 1
}

def create_minting_link(user_data):
    # Fetch Acme URL and API key from environment variables
    acme_url = ACME_URL
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "X-API-KEY": ACME_API_KEY
    }

    # Hash the user data for the "memo" field
    user_data_jwt = create_jwt(user_data)
    # Add the hashed user data to the payload's "memo" field
    mint_payload_with_memo = mint_payload.copy()  # Copy the original payload to avoid modifying the global one
    mint_payload_with_memo["memo"] = user_data_jwt

    # Send the POST request with the updated payload
    response = requests.post(acme_url + "intent/create-claim-loyalty-card-intent", json=mint_payload_with_memo, headers=headers)

    if response.status_code == 200:
        # Parse the response to get the minting link
        response_data = response.json()
        return response_data.get('data')
    else:
        response.raise_for_status()
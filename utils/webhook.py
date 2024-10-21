import aiohttp
import asyncio
import base64
from dataclasses import dataclass
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from cryptography.exceptions import InvalidSignature
from handlers.auth_handler import decrypt_data, decrypt_auth_result
from config import URL, ACME_URL, ACME_API_KEY, logger

@dataclass
class AcmeWebhookUpdate:
    """Dataclass to represent the structure of incoming Acme order updates."""
    id: str
    createdAt: str
    blockchainTransactionHash: str
    executionMessage: str
    status: str
    userId: str
    userEmail: str
    userWalletAddress: str
    intentId: str
    intentMemo: str
    auth_result: dict[str, any]  # Changed to a dictionary type


async def set_acme_webhook():
    # ACME webhook setup URL and headers
    acme_api = f"{ACME_URL}/dev/user/set-web-hook"
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "X-API-KEY": ACME_API_KEY
    }

    # Data payload with the Replit URL as the webhook target
    data = {
        "webHookUrl": f"{URL}/acme"  # Using f-string for better readability
    }

    try:
        async with aiohttp.ClientSession() as session:
            # Make the POST request to set the webhook
            logger.debug("Sending request to set webhook...")
            try:
                async with asyncio.timeout(10):  # Set a timeout of 10 seconds
                    async with session.post(acme_api, json=data, headers=headers) as response:
                        # Print the response in the logs
                        if response.status == 200:
                            logger.info(f"ACME webhook set successfully! Status code: {response.status}")
                            logger.debug(f"Response Text: {await response.text()}")
                            logger.debug(f"Payload Sent: {data}")
                        else:
                            logger.warning(f"Failed to set ACME webhook. Status code: {response.status}")
                            logger.warning(f"Response: {await response.text()}")
            except asyncio.TimeoutError:
                logger.error("Request to set ACME webhook timed out")

    except aiohttp.ClientError as e:
        logger.error(f"An error occurred while setting the ACME webhook: {str(e)}", exc_info=True)
    except Exception as e:
        logger.error(f"An unexpected error occurred: {str(e)}", exc_info=True)

def validate_signature(public_key_pem, message, signature_b64):
    # Load the public key from the PEM format
    public_key = load_pem_public_key(public_key_pem.encode())
    logger.debug("Public Key: %s", public_key)

    try:
        # Decode the Base64 encoded signature
        signature = base64.b64decode(signature_b64)
        logger.debug("Decoded Signature: %s", signature)

        # Create a SHA-512 hash of the message
        hashed_message = hashes.Hash(hashes.SHA512())
        hashed_message.update(message.encode('utf-8'))  # Ensure proper encoding
        digest = hashed_message.finalize()
        logger.debug("Hashed Message: %s", digest)

        # Verify the signature
        public_key.verify(
            signature,
            digest,
            padding.PKCS1v15(),
            hashes.SHA512()
        )
        return True  # Signature is valid
    except InvalidSignature:
        return False  # Signature is invalid

def process_acme_payload(data, signature):
    logger.debug("Processing Acme payload")

    order = data.get('order')  # Safely access 'order' to avoid KeyError

    logger.debug(f"Processing ACME ORDER: {order}")

    if not order:
        logger.error("No order found in the payload.")
        return None  # Handle the case where order is missing

    encrypted_user_data = order.get('encryptedUserData', '')
    logger.debug(f"Encrypted data in ACME ORDER: {encrypted_user_data}")

    # Decrypt the user data if it exists
    decrypted_user_data = decrypt_data(encrypted_user_data) if encrypted_user_data else {}
    logger.debug(f"Decrypted data in ACME ORDER: {decrypted_user_data}")

    auth_result = decrypt_auth_result(decrypted_user_data)
    logger.debug(f"AUTH RESULT IN ACME ORDER: {decrypted_user_data}")

    update = AcmeWebhookUpdate(
        id=order['id'],  # Required
        status=order['status'],  # Required
        createdAt=order['createdAt'],  # Required
        blockchainTransactionHash=order.get('blockchainTransactionHash', ''),  # Optional
        executionMessage= order.get('executionMessage', ''),  # Optional
        intentId= order['intentId'],  # Required
        intentMemo= order.get('intentMemo', ''),  # Optional
        userId= order.get('userId'),  # Required
        userEmail=order.get('userEmail', ''),  # Optional
        userWalletAddress=order.get('userWalletAddress', ''),  # Optional
        auth_result=auth_result,  # Pass auth result
    )

    logger.debug(f"Processed Acme payload: {update}")
    return update


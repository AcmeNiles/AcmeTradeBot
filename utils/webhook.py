import aiohttp
import asyncio
import base64
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ExtBot, ContextTypes, CallbackContext
from dataclasses import dataclass
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from cryptography.exceptions import InvalidSignature
from handlers.auth_handler import decrypt_data, decrypt_auth_result, store_auth_result

from config import logger, ACME_API_KEY, ACME_URL, DEFAULT_TIMEOUT, RETRY_COUNT, URL

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
    user_tg_id: int
    user_tg_userName: str
    user_tg_firstName: str
    auth_updated: bool=False

class AcmeContext(CallbackContext[ExtBot, dict, dict, dict]):
    """
    Custom CallbackContext class that makes `user_data` available for updates of type
    `AcmeWebhookUpdate`.
    """

    @classmethod
    def from_update(
        cls,
        update: object,
        application: "Application",
    ) -> "AcmeContext":
        if isinstance(update, AcmeWebhookUpdate):
            return cls(application=application, user_id=update.user_tg_id)
        return super().from_update(update, application)



async def set_acme_webhook():
    """
    Sets the webhook for ACME using the provided API and headers.
    Retries the request if it fails due to a timeout or network error.
    """

    # ACME webhook setup URL and headers
    acme_api = f"{ACME_URL}/dev/user/set-web-hook"
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "X-API-KEY": ACME_API_KEY,
    }

    # Data payload with the Replit URL as the webhook target
    data = {
        "webHookUrl": f"{URL}/acme",
    }

    logger.debug("Sending request to set webhook...")

    # Retry logic with `RETRY_COUNT`
    for attempt in range(RETRY_COUNT):
        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=DEFAULT_TIMEOUT)
            ) as session:
                async with session.post(acme_api, json=data, headers=headers) as response:
                    response.raise_for_status()  # Raise an error for HTTP error responses

                    # Log success and exit
                    logger.info(f"ACME webhook set successfully! Status: {response.status}")
                    logger.debug(f"Response Text: {await response.text()}")
                    logger.debug(f"Payload Sent: {data}")
                    return

        except asyncio.TimeoutError:
            logger.error(f"Attempt {attempt + 1}: Request timed out.")
        except aiohttp.ClientError as e:
            logger.error(f"Attempt {attempt + 1}: Network error: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"Unexpected error on attempt {attempt + 1}: {str(e)}", exc_info=True)

    # Log final failure after exhausting retries
    logger.error("Failed to set ACME webhook after multiple attempts.")
    
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

async def process_acme_payload(data, signature, application):
    logger.debug("Processing Acme payload")

    order = data.get('order')  # Safely access 'order' to avoid KeyError

    if not order:
        logger.error("No order found in the payload.")
        return None  # Handle the case where order is missing

    encrypted_user_data = order.get('encryptedUserData', '')

    # Decrypt the user data if it exists
    decrypted_user_data = decrypt_data(encrypted_user_data) if encrypted_user_data else {}

    auth_result = decrypt_auth_result(decrypted_user_data)

    # Check if auth_result is None or empty
    if not auth_result or 'tg_id' not in auth_result:
        logger.error("Auth result is empty or invalid.")
        return None  # Return early if auth_result is not valid

    # Get user Telegram ID and username from the auth result
    user_tg_id = int(auth_result.get('tg_id'))  # Assuming userId is the Telegram ID
    user_tg_userName = auth_result.get('tg_userName')  # Assuming tg_userName is the Telegram username

    # Store the auth result in bot_data and check if it was updated
    if user_tg_id:
        auth_updated = await store_auth_result(application, user_tg_userName, auth_result)
        if auth_updated:
            logger.info(f"Stored auth result for user {user_tg_userName} in bot_data.")
        else:
            logger.warning(f"Failed to store auth result for user {user_tg_id}.")

    update = AcmeWebhookUpdate(
        id=order['id'],  # Required
        status=order['status'],  # Required
        createdAt=order['createdAt'],  # Required
        blockchainTransactionHash=order.get('blockchainTransactionHash', ''),  # Optional
        executionMessage=order.get('executionMessage', ''),  # Optional
        intentId=order['intentId'],  # Required
        intentMemo=order.get('intentMemo', ''),  # Optional
        userId=order.get('userId', ''),  # Optional
        userEmail=order.get('userEmail', ''),  # Optional
        userWalletAddress=order.get('userWalletAddress', ''),  # Optional
        user_tg_id=user_tg_id,  # Assuming userId is the Telegram ID
        user_tg_userName=user_tg_userName,  # Assuming tg_userName is the Telegram username
        user_tg_firstName=auth_result.get('tg_firstName'),  # Assuming 
        auth_updated=bool(auth_updated)  # Indicate if auth was updated
    )
    return update  # Return only the update

async def webhook_handler(update: AcmeWebhookUpdate, context: AcmeContext) -> None:
    """Handle Acme webhook updates."""
    chat_id = update.user_tg_id  # Set chat_id to user_tg_id from the update
    logger.info(f"Processing Acme update from user_id: {chat_id}")

    try:
        if update.auth_updated:
            # Verify the user is a valid chat member
            chat_member = await context.bot.get_chat_member(chat_id=chat_id, user_id=chat_id)
            username = chat_member.user.first_name

            logger.info(f"User {username} ({chat_id}) is a valid chat member.")

            # Configurable exchange message
            
            CLAIM_SUCCESS = """"
                You claimed your pass! 🎉

                *Let's start {username_display} Exchange 🚀*
    
                *🤑 Share → Earn*
                Fees:    *0.5% USDC*
                Points: *10 XP*
            """
            
            message_text = CLAIM_SUCCESS.format(
                username_display = f"{username}'" if username.endswith('s') else f"{username}'s",
            )

            # Create an inline keyboard button
            buttons = [
                [
                    InlineKeyboardButton("🤑 Share Token", callback_data='/share'),
                    InlineKeyboardButton("🤑 Share #Top3", callback_data='/top3')
                ]
            ]
            reply_markup = InlineKeyboardMarkup(buttons)

            # Send the message with the button
            await context.bot.send_message(chat_id=chat_id, text=message_text, reply_markup=reply_markup)
        else:
            logger.info("No auth update detected, no message sent.")

    except Exception as e:
        logger.error(f"Failed to process Acme webhook update: {str(e)}")
        await context.bot.send_message(chat_id=chat_id, text="An error occurred while processing the webhook.")

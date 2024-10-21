import os
import json
import aiohttp
import asyncio
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, WebAppInfo, Bot
from telegram.ext import ContextTypes, CallbackContext
from config import WAITING_FOR_AUTH, ACME_URL, ACME_API_KEY, ACME_ENCRYPTION_KEY,BOT_USERNAME, logger
from messages_photos import markdown_v2
from utils.reply import send_message, send_photo
from utils.profilePhoto import fetch_user_profile_photo
from utils.getAcmeProfile import get_user_listed_tokens

PHOTO_LOGIN = "https://imagedelivery.net/P5lw0bNFpEj9CWud4zMJgQ/455f9727-a972-495d-162e-150f67c3e500/public"

LOGIN =  "You need an Early Coyote Pass to start your exchange.\n\nClaim yours now in #OneTap to proceed."
async def login_card(update: Update, context: ContextTypes.DEFAULT_TYPE, auth_result=None):
    """
    If the user is not authenticated, show the minting link and extra message.
    """
    # Log the inputs for debugging
    logger.debug(f"Received login_card call with the Auth Result: {auth_result}")

    # Get minting link
    minting_link = auth_result.get('url', "https://bit.ly/iamcoyote")  

    # Prepare the message and photo outside the function
    intent = context.user_data.get('intent', 'perform this action')
    tokens = context.user_data.get('tokens', [])
    # Extract token names from the dictionaries and join them
    tokens_text = ', '.join(token.get('name', '').upper() for token in tokens if isinstance(token, dict))  
    menu_message = LOGIN.format(intent=intent, tokens=tokens_text)
    # Log the minting link and menu message
    logger.debug(f"Minting Link: {minting_link}")
    logger.debug(f"Menu Message: {menu_message}")

    photo_url = PHOTO_LOGIN
    buttons = [
        [InlineKeyboardButton("👑 Claim Early Pass", web_app=WebAppInfo(url=minting_link))],
        [InlineKeyboardButton("👋 Say Hi!  ", url="https://t.me/acmeonetap")]
    ]

    reply_markup = InlineKeyboardMarkup(buttons)

    try:
        # Send the photo using send_photo function
        await send_photo(update, context, photo_url, markdown_v2(menu_message), reply_markup)
    except AttributeError as e:
        # Log the error if sending the photo fails
        logger.error(f"Failed to send reply photo: {e}")
    context.user_data.get('tokens', [])

    return WAITING_FOR_AUTH


async def is_authenticated(update: Update, context: ContextTypes.DEFAULT_TYPE) -> dict:
    """
    Check if the user is authenticated based on data from create_auth_link.
    Returns user_acme_id, user_api_key, and user_tg_id in the auth_result.
    """

    # Check if auth_result is already cached
    auth_result = context.user_data.get('auth_result')

    if auth_result:
        logger.info("Using cached authentication result. All good!")
        return auth_result  # Return cached auth result if available

    try:
        # Generate a new Telegram key
        logger.info("Creating a new tg_key...")
        tg_key = await create_tg_key(update, context)
        if not tg_key:
            raise ValueError("Failed to generate a valid Telegram key.")

        # Call Acme's create_auth_link API using the tg_key
        logger.debug("Calling Acme API for auth link...")
        auth_data = await create_auth_link(tg_key)

        if 'data' not in auth_data:
            raise ValueError("Acme server issue. Please try again later.")

        data = auth_data['data']
        
        # Handle authenticated and non-authenticated scenarios
        if 'encryptedUserData' in data:
            logger.info("User is authenticated, decrypting data now...")
            decrypted_data = decrypt_data(data['encryptedUserData'])

            # Store the user details in auth_result
            auth_result =  decrypt_auth_result(decrypted_data)
            #logger.info(f"User authenticated successfully: {auth_result}")

            # Cache the auth_result to avoid redundant calls
            context.user_data['auth_result'] = auth_result
            return auth_result

        elif isinstance(data, str) and data.startswith("http"):
            logger.info("User needs to log in. Redirecting them to login URL.")
            auth_result = {"url": data}
            context.user_data['auth_result'] = auth_result
            return auth_result

        else:
            raise ValueError("Unexpected response. No URL or user data found 😕")

    except Exception as e:
        logger.exception("Authentication failed. Something broke 😓")
        raise ValueError(f"An error occurred during authentication: {str(e)}")

async def create_tg_key(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    """
    Extract and encrypt Telegram user data.
    """
    try:
        tg_user_data = await get_tg_user(update, context)
        encrypted_data = encrypt_data(tg_user_data)
        logger.info("Telegram user data encrypted successfully.")

        return encrypted_data

    except Exception as e:
        logger.error(f"Failed to create Telegram key: {str(e)}")
        raise

async def get_tg_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> dict:
    """
    Extract Telegram user data from the update object.
    """
    user = update.effective_user
    chat_id = (
        update.message.chat.id if update.message else
        update.callback_query.message.chat.id if update.callback_query else
        update.edited_message.chat.id if update.edited_message else None
    )

    if not chat_id:
        logger.warning("No chat ID found.")

    #bot = telegram.Bot(BOT_TOKEN)
    #profile_photo_url = await get_profile_photo_url(bot, user.id)
   # logger.warning("profile photo %s",profile_photo_url)

    return {
        "id": user.id,
        "userName": user.username,
        "firstName": user.first_name,
        "lastName": user.last_name,
        "languageCode": user.language_code,
        "isBot": user.is_bot,
        "chatId": chat_id,
        "profilePhotoUrl": await fetch_user_profile_photo(update, context)
    }

async def create_auth_link(tg_key: str) -> dict:
    """
    Call the authentication API to create a claim intent asynchronously.
    """
    url = f"{ACME_URL}/telegram/intent/create-claim-loyalty-card-intent"

    headers = {
        'X-API-KEY': ACME_API_KEY,
        'X-Secure-TG-User-Info': tg_key,
        'Content-Type': 'application/json'
    }

    payload = {
        "chainId": "11155111",
        "contractAddress": "0x3c9DAbD254A3fF45fC0EF46be097E2c7Bedd8a4b",
        "name": "Coyote Early Pass",
        "description": (
            "The Coyote Early Pass unlocks exclusive perks for early bird users of Acme. "
            "Thank you for supporting us! 😊."
        ),
        "imageUri": PHOTO_LOGIN,
        "websiteUrl": "https://www.acme.am",
        "redirectUrl": f"https://t.me/{BOT_USERNAME}"
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, headers=headers, json=payload, timeout=5) as response:
                response.raise_for_status()  # Raise an error for HTTP error responses
                return await response.json()  # Return the response as JSON
        except asyncio.TimeoutError:
            logger.error("Request to authentication API timed out")
            raise
        except aiohttp.ClientError as e:
            logger.error(f"Failed to call authentication API: {e}")
            raise


async def get_invite_link(update: Update, context: ContextTypes.DEFAULT_TYPE, group_id: str) -> str:
    """
    Get a group's invite link based on membership status.
    """
    try:
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        member_status = await context.bot.get_chat_member(chat_id, user_id)

        if member_status.status in ['member', 'administrator', 'creator']:
            return f"https://t.me/{group_id.lstrip('@')}"
        else:
            return await context.bot.exportChatInviteLink(chat_id)

    except Exception as e:
        logger.error(f"Failed to generate invite link: {str(e)}")
        return "An error occurred while generating the invite link."


def encrypt_data(data: dict) -> str:
    """
    Encrypts the given data using AES-256-GCM.

    Args:
        data (dict): The data to encrypt.

    Returns:
        str: The encrypted data in the format IV:AuthTag:CipherText (hex-encoded).
    """
    # Convert the data to a JSON string
    json_data = json.dumps(data)

    # Generate a random initialization vector (IV)
    iv = os.urandom(12)  # AES-GCM uses a 12-byte IV

    # Create a cipher object using AES-256-GCM
    cipher = Cipher(
        algorithms.AES(ACME_ENCRYPTION_KEY),#
        modes.GCM(iv),
        backend=default_backend()
    )

    # Encryptor object
    encryptor = cipher.encryptor()

    # Encrypt the data
    ciphertext = encryptor.update(json_data.encode('utf-8')) + encryptor.finalize()

    # Get the authentication tag
    auth_tag = encryptor.tag

    # Convert IV, auth tag, and ciphertext to hex strings
    iv_hex = iv.hex()
    auth_tag_hex = auth_tag.hex()
    ciphertext_hex = ciphertext.hex()

    # Combine IV, auth tag, and encrypted data into a single string
    encrypted_data = f"{iv_hex}:{auth_tag_hex}:{ciphertext_hex}"

    return encrypted_data

def decrypt_data(encrypted_data: str) -> dict:
    """
    Decrypts the given encrypted data using AES-256-GCM.

    Args:
        encrypted_data (str): The encrypted data in the format IV:AuthTag:CipherText (hex-encoded).

    Returns:
        dict: The decrypted data as a dictionary.
    """
    try:
        # Split the encrypted data into IV, auth tag, and ciphertext
        iv_hex, auth_tag_hex, ciphertext_hex = encrypted_data.split(':')

        # Convert hex strings back to bytes
        iv = bytes.fromhex(iv_hex)
        auth_tag = bytes.fromhex(auth_tag_hex)
        ciphertext = bytes.fromhex(ciphertext_hex)

        # Create a cipher object using AES-256-GCM
        cipher = Cipher(
            algorithms.AES(ACME_ENCRYPTION_KEY),  # Ensure this key is securely stored and used
            modes.GCM(iv, auth_tag),
            backend=default_backend()
        )

        # Decryptor object
        decryptor = cipher.decryptor()

        # Decrypt the data
        decrypted_data = decryptor.update(ciphertext) + decryptor.finalize()

        # Convert the decrypted bytes to a JSON string
        json_data = decrypted_data.decode('utf-8')

        # Parse the JSON string into a dictionary
        data = json.loads(json_data)
        #logger.debug(f"Decrypted user data: {data}")
        return data
    except Exception as e:
        logger.error(f"Failed to decrypt data: {e}")
        return {}

def decrypt_auth_result(decrypted_data: dict) -> dict:
    """
    Convert decrypted data into an authentication result.

    Returns a dictionary containing user details.
    Raises ValueError if essential user data is missing.
    """
    user_acme_id = decrypted_data.get('userId')
    user_api_key = decrypted_data.get('userApiKey')
    user_tg_id = decrypted_data.get('telegramAccount', {}).get('id')
    user_tg_userName = decrypted_data.get('telegramAccount', {}).get('userName')
    user_tg_firstName = decrypted_data.get('telegramAccount', {}).get('firstName')
    user_tg_lastName = decrypted_data.get('telegramAccount', {}).get('lastName')
    user_tg_photo = decrypted_data.get('telegramAccount', {}).get('profilePhotoUrl')
    user_tg_language_code = decrypted_data.get('telegramAccount', {}).get('languageCode')
    user_tg_chat_id = decrypted_data.get('telegramAccount', {}).get('chatId')

    if not (user_acme_id and user_api_key and user_tg_id):
        raise ValueError("Missing user data despite valid telegramAccount. Something’s off 🤔")

    # Store the user details in auth_result
    return {
        "acme_id": user_acme_id,
        "api_key": user_api_key,
        "tg_id": user_tg_id,
        "tg_photo": user_tg_photo,
        "tg_userName": user_tg_userName,
        "tg_firstName": user_tg_firstName,
        "tg_lastName": user_tg_lastName,
        "tg_languageCode": user_tg_language_code,
        "tg_chatId": user_tg_chat_id,

    }

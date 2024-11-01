import os
import json
import aiohttp
import asyncio
from datetime import datetime, timedelta
from typing import Optional
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, WebAppInfo, Bot
from telegram.ext import ContextTypes, ConversationHandler
from config import CLAIM_PASS, START_EXCHANGE, logger, URL, AUTH_EXPIRATION, ACME_URL, ACME_API_KEY, ACME_ENCRYPTION_KEY, FEATURES, DEFAULT_TIMEOUT, RETRY_COUNT, PHOTO_COYOTE_START, PHOTO_COYOTE_COOK
from messages_photos import markdown_v2
from utils.apiHelpers import get_acme_api_key, api_get_with_retries, api_post_with_retries
from utils.reply import send_message, send_animation, send_error_message, delete_loading_message
from utils.profilePhoto import fetch_user_profile_photo

LOGIN = START_EXCHANGE + FEATURES + CLAIM_PASS

async def login_card(update: Update, context: ContextTypes.DEFAULT_TYPE, auth_result=None):
    """
    If the user is not authenticated, show the minting link and extra message.
    """
    # Log the inputs for debugging
    logger.debug(f"Received login_card call with the Auth Result: {auth_result}")

    # Get minting link
    minting_link = auth_result.get('url', None)  # Changed to None for checking

    if not minting_link:
        # If minting link is not created, send error message and end the conversation
        await send_error_message(update, context)
        return ConversationHandler.END  # End the conversation

    # Prepare the message and photo outside the function
    intent = context.user_data.get('intent', None)
    tokens = context.user_data.get('tokens', [])
    # Extract token names from the dictionaries and join them
    tokens_text = ', '.join(token.get('name', '').upper() for token in tokens if isinstance(token, dict))  
    menu_message = LOGIN.format(intent=intent, tokens=tokens_text)

    photo_url = PHOTO_COYOTE_START
    buttons = [
        [InlineKeyboardButton("👑 Claim Early Pass", web_app=WebAppInfo(url=minting_link))],
        [InlineKeyboardButton("👋 Say Hi!  ", url="https://t.me/acmeonetap")]
    ]

    reply_markup = InlineKeyboardMarkup(buttons)

    try:
        await delete_loading_message(update, context)
        # Send the photo using send_photo function
        await send_animation(
            update, 
            context, 
            photo_url, 
            markdown_v2(menu_message),
            reply_markup
        )
    except AttributeError as e:
        # Log the error if sending the photo fails
        logger.error(f"Failed to send reply photo: {e}")

    return ConversationHandler.END
    
async def is_authenticated(update: Update, context: ContextTypes.DEFAULT_TYPE) -> dict:
    """
    Check if the user is authenticated based on data from create_auth_link.
    Returns user_acme_id, user_api_key, and user_tg_id in the auth_result.
    """

    user_tg_id = str(update.effective_chat.id)  # Use the user's Telegram ID as key

    # 1. Check if auth_result is cached and valid
    auth_result = await get_auth_result(update, context)
    if auth_result:
        logger.info("Using cached authentication result from bot_data. All good!")
        return auth_result

    try:
        # 2. Create a new tg_key if no valid cached result is found
        logger.info("Creating a new tg_key...")
        tg_key = await create_tg_key(update, context)
        if not tg_key:
            raise ValueError("Failed to generate a valid Telegram key.")

        # 3. Call Acme's create_auth_link API using the tg_key
        logger.debug("Calling Acme API for auth link...")
        auth_data = await create_auth_link(context, tg_key)

        if 'data' not in auth_data:
            raise ValueError("Acme server issue. Please try again later.")

        data = auth_data['data']

        # 4. Handle authenticated and non-authenticated scenarios
        if 'encryptedUserData' in data:
            logger.info("User is authenticated, decrypting data now...")
            decrypted_data = decrypt_data(data['encryptedUserData'])
            auth_result = decrypt_auth_result(decrypted_data)

            # Store the auth result with expiration
            if await store_auth_result(context.application, user_tg_id, auth_result):
                logger.info(f"User authenticated successfully.")
            return auth_result

        elif isinstance(data, str) and data.startswith("http"):
            logger.info("User needs to log in. Redirecting them to login URL.")
            auth_result = {"url": data}
            await store_auth_result(context.application, user_tg_id, auth_result)
            return auth_result

        else:
            raise ValueError("Unexpected response. No URL or user data found 😕")

    except Exception as e:
        logger.error("Authentication failed. Something broke 😓")
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
        "webHookUrl": f"{URL}/acme",
        "referrerTgId": context.user_data.get('referrer_tg_id', None),
        "profileImageUrl": await fetch_user_profile_photo(update, context)
    }


async def create_auth_link(context, tg_key: str) -> dict:
    """
    Call the authentication API to create a claim intent asynchronously.
    Retries the request if it fails due to a timeout or network error.
    Returns None if all attempts fail and sends a message to the user.
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
        "imageUri": PHOTO_COYOTE_COOK,
        "websiteUrl": "https://www.acme.am",
    }

    #logger.debug(f"AUTH REQUEST: {url}, {headers}, {payload}")

    # Retry logic with `RETRY_COUNT`
    for attempt in range(RETRY_COUNT):
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=DEFAULT_TIMEOUT)) as session:
            try:
                async with session.post(url, headers=headers, json=payload) as response:
                    response.raise_for_status()  # Raise an error for HTTP error responses
                    return await response.json()  # Return the response as JSON

            except asyncio.TimeoutError:
                logger.error(f"Attempt {attempt + 1}: Request to authentication API timed out.")
            except aiohttp.ClientError as e:
                logger.error(f"Attempt {attempt + 1}: Failed to call authentication API: {e}")
            except Exception as e:
                logger.error(f"Unexpected error on attempt {attempt + 1}: {str(e)}")

    # Log final failure after exhausting retries
    logger.error("Failed to create auth link after multiple attempts.")

    # Send a message to the user about the failure using the utility function
    await send_message(
        context.update,  # Ensure you pass the update from the context
        context,
        text= markdown_v2("⚠️ We're facing issues with the service. Please try again later.")
    )

    return None  # Return None if all attempts fail

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
    user_tg_referrerTgId = decrypted_data.get('telegramAccount', {}).get('referrerTgId')
    user_tg_photo = decrypted_data.get('telegramAccount', {}).get('userProfileImage')
    user_tg_language_code = decrypted_data.get('telegramAccount', {}).get('languageCode')
    user_tg_chat_id = decrypted_data.get('telegramAccount', {}).get('chatId')
    user_webHookUrl = decrypted_data.get('telegramAccount', {}).get('webHookUrl')


    if not (user_acme_id and user_api_key and user_tg_id):
        logger.debug("Missing user data despite valid telegramAccount. Something’s off 🤔")
        return None

    # Store the user details in auth_result
    return {
        "acme_id": user_acme_id,
        "api_key": user_api_key,
        "webhook_url": user_webHookUrl,
        "tg_id": user_tg_id,
        "tg_photo": user_tg_photo,
        "tg_userName": user_tg_userName,
        "tg_firstName": user_tg_firstName,
        "tg_lastName": user_tg_lastName,
        "tg_languageCode": user_tg_language_code,
        "tg_chatId": user_tg_chat_id,
        "tg_referrerTgId": user_tg_referrerTgId
    }

async def store_auth_result(application, user_tg_id: str, auth_result: dict) -> bool:
    """Store the auth result with an expiration and return success status."""
    bot_data = application.bot_data

    if not isinstance(auth_result, dict) or not auth_result:
        logger.error("Invalid auth_result provided. Must be a non-empty dictionary.")
        return False

    # Retrieve or create user entry
    user_data = bot_data.get(user_tg_id, {})
    current_auth = user_data.get("auth", {})

    logger.debug(f"Current auth: {current_auth} & user_data: {user_data}")
    # Check if the current auth is expired or has a "url"
    if "auth" in user_data and user_data["expires_at"] > datetime.now():
        if "url" in current_auth:
            logger.debug(f"Current auth has 'url', overwriting with new auth_result for user {user_tg_id}.")
            user_data["auth"] = auth_result  # Overwrite the entire auth
            logger.debug(f"Updated auth_result for user {user_tg_id}: {auth_result}")
        else:
            logger.debug(f"Auth result: {user_data}\nNot overwriting.")
            return False
    else:
        # Store auth result with expiration
        user_data["auth"] = auth_result
        user_data["expires_at"] = datetime.now() + timedelta(minutes=AUTH_EXPIRATION)

    bot_data[user_tg_id] = user_data

    logger.debug(f"Stored auth result for user {user_tg_id}.")
    return True


async def get_auth_result(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Retrieve and validate the stored auth result for the user."""
    user_tg_id = update.effective_user.id
    data = context.bot_data.get(user_tg_id)
    logger.debug(f"Retrieved auth result for user {user_tg_id}: {data and "auth" in data and data["expires_at"] > datetime.now()}")
    if data and "auth" in data and data["expires_at"] > datetime.now():
        return data["auth"]

    # Cleanup expired data
    context.bot_data.pop(user_tg_id, None)
    return None

async def get_featured_tokens(update, context):
    """Fetch featured tokens from the Acme API."""
    api_key = await get_acme_api_key(update, context)
    url = f"{ACME_URL}/dev/intent/get-featured-tg-purchase-links"
    headers = {'X-API-KEY': api_key}

    return await api_get_with_retries(url, headers)

async def set_featured_tokens(update, context, intent_ids, reset_featured=False):
    """Set featured tokens in the Acme API."""
    api_key = await get_acme_api_key(update, context)
    url = f"{ACME_URL}/dev/intent/set-featured-tg-purchase-links"
    headers = {'X-API-KEY': api_key}
    payload = {"intentIds": intent_ids, "resetFeatured": reset_featured}

    response = await api_post_with_retries(url, headers, payload)
    return response.get("data",None)

async def get_user_top3(update, context):
    """Retrieve the top 3 tokens for the user, either from bot_data or the API."""
    user_id = update.effective_user.id
    user_data = context.bot_data.get(user_id, {})

    # Check if top3 exists and is valid
    if "top3" in user_data and user_data["expires_at"] > datetime.now():
        logger.info("Retrieved top 3 tokens from context for user %s", user_id)
        return user_data["top3"]

    # Fetch from API if not available or expired
    return await get_featured_tokens(update, context)

async def store_user_top3(update: Update, context: ContextTypes.DEFAULT_TYPE, top3_tokens: list) -> bool:
    """Store the top 3 tokens in context.bot_data and set them as featured."""
    user_id = update.effective_user.id

    # Check if user data already exists
    user_data = context.bot_data.get(user_id, {})

    # Determine if we need to reset featured tokens
    reset_featured = len(top3_tokens) == 3

    # If top3_tokens length is less than 2, fetch existing top 3 tokens
    if len(top3_tokens) < 2:
        existing_top3 = await get_user_top3(update, context)
        combined_top3 = list(set(existing_top3 + top3_tokens))  # Deduplicate the tokens
        logger.debug(f"Combined top3 tokens: {combined_top3}")
        user_data["top3"] = combined_top3[-3:]  # Keep only the last 3 tokens
    else:
        user_data["top3"] = top3_tokens  # Set the new top 3 tokens

    # Set expiration time
    user_data["expires_at"] = datetime.now() + timedelta(minutes=AUTH_EXPIRATION)

    # Store the updated user_data back in bot_data
    context.bot_data[user_id] = user_data
    # Use the set-featured API to update Acme's records
    intent_ids = [token["tradingLink"].split('/')[-1] for token in user_data["top3"] if "tradingLink" in token]
    api_response = await set_featured_tokens(update, context, intent_ids, reset_featured=reset_featured)

    logger.debug(f"API REPONSE: {api_response}")
    # Log the result and update bot data if successful
    if api_response:
        logger.info("Top 3 tokens stored and set as featured for user %s", user_id)
        return True
    else:
        logger.error("Failed to set featured tokens for user %s", user_id)
        return False

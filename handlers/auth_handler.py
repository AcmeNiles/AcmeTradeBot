import os
import json
import requests
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, WebAppInfo, Bot
from telegram.ext import ContextTypes, CallbackContext
from config import WAITING_FOR_AUTH, ACME_AUTH_URL, ACME_API_KEY, BOT_TOKEN, ACME_ENCRYPTION_KEY,logger
from messages_photos import MESSAGE_LOGIN, PHOTO_MENU

async def login_card(update: Update, context: ContextTypes.DEFAULT_TYPE, auth_result=None):
    """
    If the user is not authenticated, show the minting link and extra message.
    """
    # Log the inputs for debugging
    logger.debug("Received login_card call with the following inputs:")
    logger.debug(f"Update: {update}")
    logger.debug(f"Context: {context}")
    logger.debug(f"Auth Result: {auth_result}")

    # Get minting link and menu message
    minting_link = auth_result.get('url', "https://bit.ly/iamcoyote")  
    menu_message = MESSAGE_LOGIN

    # Log the minting link and menu message
    logger.debug(f"Minting Link: {minting_link}")
    logger.debug(f"Menu Message: {menu_message}")
    logger.debug(f"PHOTO_MENU: {PHOTO_MENU}")

    buttons = [
        [InlineKeyboardButton("Claim Your Access Pass", web_app=WebAppInfo(url=minting_link))],
        [InlineKeyboardButton("Say Hi! 👋 ", url="https://t.me/acmeonetap")]
    ]

    reply_markup = InlineKeyboardMarkup(buttons)

    try:
        # Attempt to send the reply photo if update.message is valid
        if update.message:  # Ensure update.message is not None
            await update.message.reply_photo(
                photo=PHOTO_MENU,
                caption=markdown_v2(menu_message),  # Use markdown_v2 here
                reply_markup=reply_markup
            )
        else:
            # Attempt to use callback_query if update.message is None
            await update.callback_query.message.reply_photo(
                photo=PHOTO_MENU,
                caption=markdown_v2(menu_message),  # Use markdown_v2 here
                reply_markup=reply_markup
            )
    except AttributeError as e:
        # Log the error if reply_photo fails
        logger.error(f"Failed to send reply photo: {e}")

    return WAITING_FOR_AUTH
    
async def is_authenticated(update: Update, context: CallbackContext) -> dict:
    """
    Check if the user is authenticated based on data from create_auth_link.
    """

    # Check if auth_result and tg_key are already cached
    auth_result = context.user_data.get('auth_result')
    tg_key = context.user_data.get('tg_key')

    if auth_result and tg_key:
        logger.info("Using cached tg_key and authentication result.")
        return auth_result  # Return cached auth result if available

    try:
        # Generate a new Telegram key if not already cached
        if not tg_key:
            tg_key = await create_tg_key(update)
            if not tg_key:
                raise ValueError("Failed to generate a valid Telegram key.")
            context.user_data['tg_key'] = tg_key  # Cache tg_key
            logger.info(f"Generated and cached new tg_key: {tg_key}")

        # Call Acme's create_auth_link API using the tg_key
        auth_data = await create_auth_link(tg_key)

        if 'data' not in auth_data:
            raise ValueError("Acme server issue. Please try again later.")

        data = auth_data['data']

        # Handle authenticated and non-authenticated scenarios
        if 'telegramAccount' in data:
            user_id = data.get('userid')
            if not user_id:
                raise ValueError("Missing user ID despite valid telegramAccount.")
            auth_result = {"id": user_id}  # Store user ID if authenticated
        elif isinstance(data, str) and data.startswith("http"):
            auth_result = {"url": data}  # Store login URL if authentication needed
        else:
            raise ValueError("Unexpected authentication response: no URL or user ID found.")

        # Cache the auth_result to avoid redundant calls
        context.user_data['auth_result'] = auth_result
        logger.info(f"Cached authentication result: {auth_result}")

        return auth_result

    except Exception as e:
        logger.exception(f"Authentication failed: {str(e)}")
        raise ValueError(f"An error occurred during authentication: {str(e)}")

async def create_tg_key(update: Update) -> str:
    """
    Extract and encrypt Telegram user data.
    """
    try:
        tg_user_data = await get_tg_user(update)
        encrypted_data = encrypt_data(tg_user_data)
        logger.info("Telegram user data encrypted successfully.")

        return encrypted_data

    except Exception as e:
        logger.error(f"Failed to create Telegram key: {str(e)}")
        raise

async def get_profile_photo_url(bot: Bot, user_id: int) -> str:
    """
    Get the profile photo URL of the Telegram user.
    """
    # Fetch user profile photos using the bot instance
    photos = await bot.get_user_profile_photos(user_id)

    if photos.total_count > 0:
        file_id = photos.photos[0][0].file_id  # Get the first photo's file ID
        file = await bot.get_file(file_id)  # Retrieve the file object
        return file.file_path  # Return the file path of the photo
    return None  # Return None if no photos are found

async def get_tg_user(update: Update) -> dict:
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
        #"profilePhotoUrl": profile_photo_url
    }


async def create_auth_link(tg_key: str) -> dict:
    """
    Call the authentication API to create a claim intent.
    """
    url = f"{ACME_AUTH_URL}/intent/create-claim-loyalty-card-intent"
    #url = 'https://acme-prod.fly.dev/operations/dev/intent/create-claim-loyalty-card-intent'

    headers = {
        'X-API-KEY': ACME_API_KEY,
        #'X-API-KEY' : 'PRCAEUY-LA6UTNQ-XYL5DEI-ZNUEMDA',
        'X-Secure-TG-User-Info': tg_key,
        'Content-Type': 'application/json'
    }

    payload = {
        #"chainId": "42161",
        #"contractAddress": "0xA3090C10b2dD4B69A594CA4dF7b1F574a8D0B476",
        "chainId": "11155111",
        "contractAddress": "0x3c9DAbD254A3fF45fC0EF46be097E2c7Bedd8a4b",
        "name": "Coyote Early Pass",
        "description": (
            "The Coyote Early Pass unlocks exclusive perks for early bird users of Acme. "
            "Thank you for supporting us! 😊."
        ),
        "imageUri": PHOTO_MENU,
        "websiteUrl": "https://www.acme.am",
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        logger.debug(f"Auth Response: {response.json()}")

        return response.json()
    except requests.exceptions.RequestException as e:
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
        logger.debug(f"Decrypted user data: {data}")
        return data
    except Exception as e:
        logger.error(f"Failed to decrypt data: {e}")
        return {}
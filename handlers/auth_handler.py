import os
import json
import requests
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, WebAppInfo
from telegram.ext import ContextTypes, CallbackContext
from config import WAITING_FOR_AUTH, ACME_URL, ACME_API_KEY, ENCRYPTION_KEY,logger
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
    try:
        tg_key = await create_tg_key(update)
        if not tg_key:
            raise ValueError("Failed to generate a valid Telegram key.")

        logger.info(f"Authenticating with tg_key: {tg_key}")
        
        # Store tg_key in context.user_data
        context.user_data['tg_key'] = tg_key  
        
        auth_data = await create_auth_link(tg_key)

        if 'data' not in auth_data:
            raise ValueError("Acme server issue. Please try again later.")

        data = auth_data['data']

        if 'telegramAccount' in data:
            user_id = data.get('userid')
            if not user_id:
                raise ValueError("Missing user ID despite valid telegramAccount.")
            return {"id": user_id}

        if isinstance(data, str) and data.startswith("http"):
            return {"url": data}

        raise ValueError("Unexpected authentication response: no URL or user ID found.")

    except Exception as e:
        logger.exception(f"Authentication failed: {str(e)}")
        raise ValueError(f"An error occurred during authentication: {str(e)}")

async def create_tg_key(update: Update) -> str:
    """
    Extract and encrypt Telegram user data.
    """
    try:
        tg_user_data = get_tg_user(update)
        logger.debug(f"Extracted Telegram user data: {tg_user_data}")

        encrypted_data = encrypt_data(tg_user_data)
        logger.info("Telegram user data encrypted successfully.")

        return encrypted_data

    except Exception as e:
        logger.error(f"Failed to create Telegram key: {str(e)}")
        raise

def get_tg_user(update: Update) -> dict:
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

    return {
        "user_id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "language_code": user.language_code,
        "is_bot": user.is_bot,
        "chat_id": chat_id
    }

async def create_auth_link(tg_key: str) -> dict:
    """
    Call the authentication API to create a claim intent.
    """
    url = f"{ACME_URL}/intent/create-claim-loyalty-card-intent"
    headers = {
        'X-API-KEY': ACME_API_KEY,
        'X-Secure-TG-User-Info': tg_key,
        'Content-Type': 'application/json'
    }
    payload = {
        "chainId": "42161",
        "contractAddress": "0xA3090C10b2dD4B69A594CA4dF7b1F574a8D0B476",
        "name": "Coyote Early Pass",
        "description": (
            "The Coyote Early Pass unlocks exclusive perks for early bird users of Acme. "
            "Thank you for supporting us! 😊."
        ),
        "imageUri": "https://imagedelivery.net/P5lw0bNFpEj9CWud4zMJgQ/feecc12a-109f-417d-ed17-b5cee8fd1a00/public",
        "websiteUrl": "https://www.acme.am",
        "intentLimit": 1
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
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
    Encrypt the given data using AES-256-GCM.
    """
    iv = os.urandom(12)
    salt = os.urandom(16)

    data_with_salt = {**data, "salt": salt.hex()}
    json_data = json.dumps(data_with_salt).encode('utf-8')

    encryptor = Cipher(
        algorithms.AES(ENCRYPTION_KEY), modes.GCM(iv), backend=default_backend()
    ).encryptor()

    encrypted_data = encryptor.update(json_data) + encryptor.finalize()

    return f"{iv.hex()}:{encryptor.tag.hex()}:{encrypted_data.hex()}:{salt.hex()}"

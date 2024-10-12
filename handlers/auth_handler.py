import logging
import requests
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import os
import json
from config import WAITING_FOR_AUTH
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, WebAppInfo
from telegram.ext import ContextTypes, CallbackContext
from typing import Union

# Initialize logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# AES-256 key (32 bytes)
ENCRYPTION_KEY = bytes.fromhex("e4d3638ac94cf85b55f86d52ff72591651fe6bc9f0dbae563d99043adbd0e32f")


async def login_card(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str = None):
    """
    If the user is not authenticated, show the minting link and extra message.

    Args:
        update: The Telegram update object.
        context: The context object containing user data.
        url: The minting URL to be displayed (if any).
    """
    minting_link = url or "https://example.com/mint"  # Replace with actual minting link
    menu_message = "Get your access pass and start making some money! 💸 \n"

    # Web App Button for "Claim Your Access Pass"
    buttons = [
        [InlineKeyboardButton("Claim Your Access Pass", web_app=WebAppInfo(url=minting_link))],
        [InlineKeyboardButton("Say Hi! 👋", url="https://t.me/acmeonetap")],  # Adjust the invite_link as needed
    ]

    # Create a reply markup with the buttons
    reply_markup = InlineKeyboardMarkup(buttons)

    # Using MENU_PHOTO for the photo
    await update.message.reply_photo(photo=MENU_PHOTO, caption=menu_message, reply_markup=reply_markup)
    return WAITING_FOR_AUTH

async def is_authenticated(context: CallbackContext) -> Union[bool, str]:
    """
    Check if the user is authenticated based on the data returned from create_auth_link.
    Returns a URL if the user is not authenticated, 
    otherwise returns the data object.
    Raises a generic Exception if the server is facing issues.
    """
    tg_key = context.user_data.get('tg_key')  # Assuming tg_key is stored in user_data
    auth_data = await create_auth_link(tg_key)

    # Check if the response contains data
    if 'data' in auth_data:
        if 'url' in auth_data['data']:
            return auth_data['data']['url']  # Not authenticated, return the URL
        else:
            return True  # Authenticated, return the data object
    else:
        # Raise a standard Exception if neither URL nor data is present
        raise Exception("Acme server is facing issues. Please try again later.")

def encrypt_data(data: dict) -> str:
    iv = os.urandom(12)  # GCM uses a 12-byte IV
    salt = os.urandom(16)  # Adding a 16-byte random salt

    # Add the salt to the data
    data_with_salt = {**data, "salt": salt.hex()}

    json_data = json.dumps(data_with_salt).encode('utf-8')

    # Create AES-256-GCM cipher
    encryptor = Cipher(
        algorithms.AES(ENCRYPTION_KEY),
        modes.GCM(iv),
        backend=default_backend()
    ).encryptor()

    # Encrypt the data
    encrypted_data = encryptor.update(json_data) + encryptor.finalize()

    # Return the encrypted data as a string, including IV, auth_tag, and the encrypted data
    return f"{iv.hex()}:{encryptor.tag.hex()}:{encrypted_data.hex()}:{salt.hex()}"

def get_tg_user(update: Update) -> dict:
    """Extract user data from the update object."""
    user = update.effective_user
    chat_id = update.effective_chat.id  # Get the chat ID

    return {
        "user_id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "language_code": user.language_code,  # Added language code
        "is_bot": user.is_bot,                # Added is_bot status
        "chat_id": chat_id                    # Added chat ID
    }

def create_auth_link(tg_key: str) -> dict:
    """Calls the authentication API to create an intent for trading."""
    url = f"{BASE_URL}/operations/telegram/intent/create-claim-loyalty-card-intent"

    headers = {
        'X-API-KEY': API_KEY,
        'X-Secure-TG-User-Info': tg_key,
        'Content-Type': 'application/json'
    }

    payload = {
        "contractAddress": "0xC4F7f435F9cECA0c844f3dDA46EeC00c4F7E34FC",  # Example address
        "chainId": "137",
        "name": "Telegram User",
        "imageUri": "https://static-00.iconduck.com/assets.00/telegram-icon-2048x2048-30xu965w.png",
        "description": "Telegram User Claim",
        "websiteUrl": "https://acme.am/"
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()  # Raise an error for bad responses
        response_data = response.json()
        return response_data.get('data', {})

    except requests.exceptions.RequestException as e:
        logger.error(f"Authentication API error: {e}")
        return {"error": "API request failed"}

def auth_tg_user(update: Update):
    """Extract Telegram user data, encrypt it, and authenticate the user."""
    # Step 1: Get Telegram user data
    tg_user_data = get_tg_user(update)

    # Step 2: Encrypt the Telegram user data
    encrypted_tg_data = encrypt_data(tg_user_data)

    # Step 3: Create the authentication link with the encrypted data
    auth_response = create_auth_link(encrypted_tg_data)

    return auth_response

async def get_invite_link(update: Update, context: ContextTypes.DEFAULT_TYPE, group_id: str) -> str:
    user_id = update.effective_user.id  # Extract user ID from update
    chat_id = update.effective_chat.id    # Extract chat ID from update

    try:
        member_status = await context.bot.get_chat_member(chat_id, user_id)

        if member_status.status in ['member', 'administrator', 'creator']:
            group_link = f"https://t.me/{group_id.lstrip('@')}"
            return group_link
        else:
            group_invite_link = await context.bot.exportChatInviteLink(chat_id)
            return group_invite_link

    except Exception as e:
        logger.error("Failed to check membership or generate invite link: %s", str(e))
        return "An error occurred while checking your membership status."

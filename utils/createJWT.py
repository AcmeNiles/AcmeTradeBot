import json
import os
from telegram import Update
import jwt
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError

from config import ACME_API_KEY

HASH_KEY = ACME_API_KEY

def get_user_data(update: Update) -> dict:
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
        "chat_id": chat_id                     # Added chat ID
    }
    
def create_jwt(user_data: dict) -> str:
    """Create a JWT from user data."""
    # Sort the user data to ensure consistent ordering
    data_string = json.dumps(user_data, sort_keys=True)

    # Create a JWT token with the bot token as the secret
    token = jwt.encode({"data": data_string}, HASH_KEY, algorithm="HS256")
    return token

def decode_jwt(token: str) -> dict:
    """Decode a JWT and return the user data."""
    try:
        # Decode the token using the bot token as the secret
        decoded = jwt.decode(token, HASH_KEY, algorithms=["HS256"])
        return json.loads(decoded["data"])  # Return the original user data as a dict
    except ExpiredSignatureError:
        print("Token has expired.")
        return {}
    except InvalidTokenError:
        print("Invalid token.")
        return {}


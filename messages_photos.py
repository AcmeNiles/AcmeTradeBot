import requests
from config import logger

# Markdown V2 special characters
MARKDOWN_V2_SPECIAL_CHARS = ['~', '>', '#', '+', '-', '=', '|', '.', '!']

# Define common menu messages with unescaped characters
MENU = (
    "\n🏦 *👋 Welcome to Acme!* \n\n"
    "🤑 *Share to Earn*\n"
    "Share trading links and earn 50% fees + airdrops.\n\n"
    "💳 *Tap.* *Trade.* *Done*.\n"
    "Easily buy any token with your bank card.\n\n"
    "🔒 *Own your Tokens*\n"
    "Tokens are secured in a safe. Only you have the keys.\n\n"
)
LOGIN = "💸 Claim access pass and start your exchange! 💸 \n"
LOGGED_IN = "💸 Let's start making some money! 💸 \n"
# Trading card text template without Markdown V2 formatting
TRADE = (
    "📢 *TRADE {symbol}!*\n\n"
    "🔗 Chain ID: {chain_id}\n"
    "🏷️ Contract Address: {contract_address}\n"
)
# Define the message outside the function
NOT_LISTED = "🚫 *{symbol.upper()}* is not listed. Message us to request listing:"
ASK_TOKEN = "*TYPE* or select the token symbol you want to trade:"

# Photo URLs
PHOTO_MENU = "https://imagedelivery.net/P5lw0bNFpEj9CWud4zMJgQ/feecc12a-109f-417d-ed17-b5cee8fd1a00/public"
PHOTO_TRADE = "https://imagedelivery.net/P5lw0bNFpEj9CWud4zMJgQ/feecc12a-109f-417d-ed17-b5cee8fd1a00/public"

PHOTO_URLS_TO_CHECK = [PHOTO_MENU, PHOTO_TRADE]

def markdown_v2(message: str) -> str:
    """Escape special characters for Markdown V2 and ensure the first character is escaped if necessary."""

    # Handle empty messages first
    if not message:
        return message  # Return empty string as is

    # Escape the first character if it's a special character
    if message[0] in MARKDOWN_V2_SPECIAL_CHARS:
        message = f'\\{message[0]}' + message[1:]

    # Escape Markdown V2 special characters for the rest of the message
    for char in MARKDOWN_V2_SPECIAL_CHARS:
        message = message.replace(char, f'\\{char}')

    return message

def verify_photos():
    """Check the status of photo URLs (this can be extended as needed)."""
    for url in PHOTO_URLS_TO_CHECK:
        try:
            response = requests.head(url)  # Check if the URL is accessible
            if response.status_code == 200:
                logger.info(f"Photo URL is accessible: {url}")
            else:
                logger.error(f"Photo URL not accessible: {url} (Status Code: {response.status_code})")
        except Exception as e:
            logger.error(f"Error checking photo URL {url}: {e}")

# Call the function to get the processed messages
MESSAGE_MENU = markdown_v2(MENU)
MESSAGE_LOGIN = markdown_v2(LOGIN)
MESSAGE_LOGGED_IN = markdown_v2(LOGGED_IN)
MESSAGE_TRADE = markdown_v2(TRADE)
MESSAGE_NOT_LISTED = markdown_v2(NOT_LISTED)
MESSAGE_ASK_TOKEN = markdown_v2(ASK_TOKEN)

# Process the photos
verify_photos()
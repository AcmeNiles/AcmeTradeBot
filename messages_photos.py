import requests
from config import logger

# Markdown V2 special characters
MARKDOWN_V2_SPECIAL_CHARS = ['~', '>', '#', '+', '-', '=', '|', '.', '!']

EXCHANGE = (
    "📢 Trade *{symbol}*\n\n"
    "🪙 Price: *{price}*\n"
    "📈 24h Change: *``{change_24h}*\n\n"
    "💰 Market Cap: *${mcap}*\n"
    "📊 24h Volume: *${volume_24h}*\n\n"
    #"🔄 Circulating Supply: *{circulating_supply}*\n"
    #"📦 Total Supply: *{total_supply}*\n"
)

# Photo URLs
#PHOTO_MENU = "https://imagedelivery.net/P5lw0bNFpEj9CWud4zMJgQ/c8896fab-49d6-48ec-f5c6-e46510dd0a00/public"
PHOTO_TRADE = "https://imagedelivery.net/P5lw0bNFpEj9CWud4zMJgQ/432c3594-2f7f-4672-a276-cd11c0dfe900/public"
PHOTO_EXCHANGE = "https://imagedelivery.net/P5lw0bNFpEj9CWud4zMJgQ/d8f8035d-5dee-4a70-d53c-f8e654536a00/public"
PHOTO_TOP3 = "https://imagedelivery.net/P5lw0bNFpEj9CWud4zMJgQ/d8f8035d-5dee-4a70-d53c-f8e654536a00/public"


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




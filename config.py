import os

# Define configuration constants
PORT = os.getenv("PORT")
ACME_API_KEY = os.getenv("ACME_API_KEY")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")


# Dev
URL = os.getenv("DEV_URL")
BOT_TOKEN = os.getenv("DEV_TOKEN")
ACME_GROUP = os.getenv("DEV_ACME_GROUP")  # Replace with your group's chat ID or username
ACME_URL = os.getenv("ACME_DEV_URL")

# Production
#URL = os.getenv("URL")
#BOT_TOKEN = os.getenv("BOT_TOKEN")
#ACME_GROUP = os.getenv("ACME_GROUP")  # Replace with your group's chat ID or username
#ACME_URL = os.getenv("ACME_PROD_URL")

# Define conversation states
SELECT_TOKEN, SELECT_AMOUNT, SELECT_RECIPIENT, WAITING_FOR_AUTH = range(4)

# Global variables for valid and authenticated commands
VALID_COMMANDS = {'trade', 'pay', 'request', 'token', 'share', 'vault', 'start','menu'}
AUTHENTICATED_COMMANDS = {'trade', 'pay', 'request', 'vault'}

#Bot Card Image Paths
MENU_PHOTO = "https://imagedelivery.net/P5lw0bNFpEj9CWud4zMJgQ/feecc12a-109f-417d-ed17-b5cee8fd1a00/public"


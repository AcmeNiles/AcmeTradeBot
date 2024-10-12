import os

# Define configuration constants
PORT = 8000
ACME_API_KEY = os.getenv("ACME_API_KEY")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
ACME_URL = "https://acme-prod.fly.dev/operations/dev/"

# Dev
URL = "https://b15a212e-ca66-4c21-ad34-76d56d3dc709-00-2jytsqhog1kqq.spock.replit.dev"
TOKEN = "6790358488:AAHg1Ml3Dqvco4IT7RfGjMaG4vCvPmSSUwA"

# Production
#URL = "https://acmeonetap.replit.app"
#TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
#CHAT_GROUP = "@acmeonetap"  # Replace with your group's chat ID or username

# Define conversation states
SELECT_TOKEN, SELECT_AMOUNT, SELECT_RECIPIENT, WAITING_FOR_AUTH = range(4)
ACME_GROUP = "@acmetest"

# Global variables for valid and authenticated commands
VALID_COMMANDS = {'trade', 'pay', 'request', 'token', 'share', 'vault', 'start','menu'}
AUTHENTICATED_COMMANDS = {'trade', 'pay', 'request', 'vault'}

#Bot Card Image Paths
MENU_PHOTO = "https://imagedelivery.net/P5lw0bNFpEj9CWud4zMJgQ/feecc12a-109f-417d-ed17-b5cee8fd1a00/public"


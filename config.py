import os
import logging
import sys

# Initialize logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Add console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)
logger.propagate = False  # Prevent duplicate logs


# Helper function to fetch environment variables
def get_env_var(var_name: str, required: bool = True) -> str:
    """Fetch an environment variable with optional error handling."""
    value = os.getenv(var_name)
    if required and value is None:
        logger.critical(f"Missing required environment variable: {var_name}")
        raise ValueError(f"Environment variable '{var_name}' is not set.")
    if value:
        logger.info(f"Loaded {var_name}.")
    return value


try:
    # General Configuration
    PORT = get_env_var("PORT")
    ADMIN_CHAT_ID = get_env_var("ADMIN_CHAT_ID")

    # Detect environment: defaults to 'DEV'
    env = os.getenv('ENV', 'DEV').upper()
    if env not in ['DEV', 'PROD']:
        logger.critical(f"Invalid ENV value: {env}")
        raise ValueError(f"Invalid ENV value: {env}. Expected 'DEV' or 'PROD'.")

    # Load environment-specific configurations
    if env == 'PROD':
        logger.info("Running in PRODUCTION environment.")
        URL = get_env_var("PROD_URL")
        BOT_TOKEN = get_env_var("PROD_BOT_TOKEN")
        ACME_GROUP = get_env_var("PROD_ACME_GROUP")
        ACME_URL = get_env_var("DEV_ACME_URL")
        ACME_APP_URL = os.getenv("DEV_ACME_APP_URL", "https://app.acme.am")
        ACME_API_KEY = get_env_var("DEV_ACME_API_KEY")
        ACME_ENCRYPTION_KEY = bytes.fromhex(os.getenv("PROD_ACME_ENCRYPTION_KEY", ""))
        ACME_AUTH_URL = os.getenv("DEV_ACME_AUTH_URL", "")
        ACME_WEBHOOK_PEM = os.getenv("PROD_ACME_WEBHOOK_PEM", "")
        # Fetching secrets from environment variables
        CLOUDFLARE_API_TOKEN = os.getenv('CLOUDFLARE_API_TOKEN')  # Fetch Cloudflare API token
        CLOUDFLARE_ACCOUNT_ID = os.getenv('CLOUDFLARE_ACCOUNT_ID')  # Fetch Cloudflare account ID
        CLOUDFLARE_HASH = os.getenv('CLOUDFLARE_HASH')  # Fetch Cloudflare API token
        BOT_USERNAME = os.getenv('PROD_BOT_USERNAME')  # Fetch bot username


    else:  # DEV environment
        logger.info("Running in DEVELOPMENT environment.")
        URL = get_env_var("DEV_URL")
        BOT_TOKEN = get_env_var("DEV_BOT_TOKEN")
        ACME_GROUP = get_env_var("DEV_ACME_GROUP")
        # Optional DEV values – won't raise errors if not present
        ACME_URL = os.getenv("DEV_ACME_URL", "https://acme-qa.fly.dev/operations/dev")
        ACME_APP_URL = os.getenv("DEV_ACME_APP_URL", "https://dev.app.acme.am")
        ACME_API_KEY = os.getenv("DEV_ACME_API_KEY", "")
        ACME_ENCRYPTION_KEY = bytes.fromhex(os.getenv("DEV_ACME_ENCRYPTION_KEY", ""))
        ACME_AUTH_URL = os.getenv("DEV_ACME_AUTH_URL", "")
        ACME_WEBHOOK_PEM = os.getenv("PROD_ACME_WEBHOOK_PEM", "")
        CLOUDFLARE_API_TOKEN = os.getenv('CLOUDFLARE_API_TOKEN')  # Fetch Cloudflare API token
        CLOUDFLARE_ACCOUNT_ID = os.getenv('CLOUDFLARE_ACCOUNT_ID')  # Fetch Cloudflare account ID
        CLOUDFLARE_HASH = os.getenv('CLOUDFLARE_HASH')  # Fetch Cloudflare API token
        BOT_USERNAME = os.getenv('DEV_BOT_USERNAME')  # Fetch bot username

except ValueError as e:
    logger.critical(f"Startup aborted due to configuration error: {e}")
    sys.exit(1)  # Exit if any critical configuration is missing

# Define conversation states
SELECT_TOKEN, SELECT_AMOUNT, SELECT_RECEIVER, WAITING_FOR_AUTH = range(4)

# Global variables for valid and authenticated commands
VALID_COMMANDS = {'trade', 'pay', 'request', 'share', 'list','delist', 'vault', 'start', 'menu','logout','cancel'}
AUTHENTICATED_COMMANDS = {'pay', 'request', 'vault', 'list'}
# Define featured tokens for different intents
FEATURED_TOKENS_TRADE = [
    {"PONKE":"PONKE"},
    {"POPCAT":"POPCAT"},
    {"TOSHI":"TOSHI"}
]
# Tokens for trading
FEATURED_TOKENS_LIST = [
    {"MEMES":"PONKE POPCAT TOSHI"},
    {"AI":"PONKE POPCAT TOSHI"},
    {"GAMES":"PONKE POPCAT TOSHI"}
]  # Tokens for trading

FEATURED_TOKENS_PAY = [
    {"USDC":"USDC"},
    {"DAI":"DAI"},
    {"USDT":"USDT"}
]
# List of supported chain IDs
SUPPORTED_CHAIN_IDS = {
    '1151111081099710': 'solana',   # Solana
    '8453': 'base',                 # Base
    '42161': 'arbitrum-one',        # Arbitrum One
    '137': 'polygon-pos'            # Polygon (PoS)
}
MAX_LISTED_TOKENS = 3  # Configurable value for maximum listed tokens

LIFI_API_URL = "https://li.quest/v1"
COINGECKO_API_URL = "https://api.coingecko.com/api/v3/coins/{token_id}"
logger.info("Configuration successfully loaded and validated.")

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
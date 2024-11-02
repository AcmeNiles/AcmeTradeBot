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
    AUTH_EXPIRATION = 60 * 60 * 24 * 7  # 7 days in seconds
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
        DEFAULT_ACME_API_KEY = os.getenv("DEV_DEFAULT_ACME_API_KEY", "")
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
        DEFAULT_ACME_API_KEY = os.getenv("DEV_DEFAULT_ACME_API_KEY", "")
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


DEFAULT_TIMEOUT = 3  # Timeout for the API request in seconds
RETRY_COUNT = 2  # Number of retries on failure

# Define conversation states
SELECT_TOKEN, SELECT_AMOUNT, SELECT_RECEIVER = range(3)

# Global variables for valid and authenticated commands
VALID_COMMANDS = {'trade', 'pay', 'request', 'share', 'top3', 'list', 'delist', 'vault', 'start', 'menu','logout','cancel','why_list','why_trade'}
AUTHENTICATED_COMMANDS = {'pay', 'request', 'vault', 'list','top3','share','start','menu','trade'}
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
    '8453': 'base',                 # Base
    '42161': 'arbitrum-one',        # Arbitrum One
    '1151111081099710': 'solana'   # Solana
}
MAX_LISTED_TOKENS = 3  # Configurable value for maximum listed tokens

LIFI_API_URL = "https://li.quest/v1"
COINGECKO_API_URL = "https://api.coingecko.com/api/v3/coins/{token_id}"
logger.info("Configuration successfully loaded and validated.")

PHOTO_COYOTE_BANANA = "https://imagedelivery.net/P5lw0bNFpEj9CWud4zMJgQ/895a84b1-67b5-42e5-6fb1-b937d1151600/public"
PHOTO_COYOTE_COOK = "https://imagedelivery.net/P5lw0bNFpEj9CWud4zMJgQ/07774565-aab0-4471-068d-422e5c702700/public"
PHOTO_COYOTE_CHAMPAGNE = "https://imagedelivery.net/P5lw0bNFpEj9CWud4zMJgQ/6df6cab5-27cc-4eda-ebbd-ea67821be000/public"
PHOTO_COYOTE_CHEST = "https://imagedelivery.net/P5lw0bNFpEj9CWud4zMJgQ/28c4155d-873c-4a54-52c3-a4a02e6eba00/public"
PHOTO_COYOTE_MIC = "https://imagedelivery.net/P5lw0bNFpEj9CWud4zMJgQ/00e0ad8a-c96d-4b5e-034f-21d9dcd4bd00/public"
PHOTO_COYOTE_TABLE = "https://imagedelivery.net/P5lw0bNFpEj9CWud4zMJgQ/8ab1aa39-4155-42a5-d6bc-d0127c871c00/public"
PHOTO_COYOTE_START = "https://imagedelivery.net/P5lw0bNFpEj9CWud4zMJgQ/08d9d99f-98e5-41f0-f5f1-331d3e4b5c00/public"


WHY_TRADE = """
☝️ *Tap. Trade. Done.*  
_Trade any token in #OneTap_\n

1️⃣ *Super Easy*
Trade any token with bank cards — fast & easy.  

2️⃣ *Best Prices* 
Get top rates from DEXs and on-ramp providers.  

3️⃣ *Full Control*
Hold tokens in Safes securing *$100B+*. Only *you* have the keys.
"""

WHY_LIST = """
\n*🔥 Start Your Exchange. Today.*  

1️⃣ *List → Share*
Simply type _/share_ to list your token.

2️⃣ *Share → Buy*
Share to help others easily buy the token.

3️⃣ *Buy → Earn*
Earn up to 1% fees & rewards on each trade — instantly.
"""
LOGGED_IN = "*🚀 [{username_display} Exchange](https://t.me/{bot_username}?start) 🚀*\n"

START_EXCHANGE = """
*🔥 Start Your Exchange. Today.\n*
"""

FEATURES = """
💳 *Tap. Trade. Done*.
Buy any token with your bank card.
_Earn 30% fees & prizes!_

🤑 *List. Share. Earn.*
Help others buy tokens you love.
_Earn 50% fees & prizes!_

🔐 *Own Your Tokens*
Stored in Safes securing $100B+.
_Only you have the keys._
"""

CLAIM_PASS = """
\n*👑 Claim Early Pass to get started!* 
"""
LETS_GO = "\n💸 Let's make some money!"

MAKE_MONEY = "💸 Buy & win up to $1,000!"
PASS_CLAIMED = "You claimed your pass! 🎉"

FAQ = """
\n﹒﹒﹒\n
🌐 _Chains:_
Solana, Base, Polygon, Arbitrum, BSC  

💳 _Payments:_
VISA, MasterCard 🌍
\n﹒﹒﹒
"""
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
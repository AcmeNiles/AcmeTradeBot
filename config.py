import os
import logging
import sys

# Initialize logger
logger = logging.getLogger(__name__)

# Add console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)
logger.setLevel(logging.DEBUG)
logger.propagate = False  # Ensure no duplicate logs

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

    # AES-256 Encryption Key (32 bytes)
    encryption_key_hex = get_env_var("ENCRYPTION_KEY")
    try:
        ENCRYPTION_KEY = bytes.fromhex(encryption_key_hex)
        logger.info("Successfully converted ENCRYPTION_KEY from hex.")
    except ValueError as e:
        logger.critical("Failed to convert ENCRYPTION_KEY from hex.")
        raise ValueError("Invalid ENCRYPTION_KEY value.") from e

    # Load environment-specific configurations
    if env == 'PROD':
        logger.info("Running in PRODUCTION environment.")
        URL = get_env_var("PROD_URL")
        BOT_TOKEN = get_env_var("PROD_BOT_TOKEN")
        ACME_GROUP = get_env_var("PROD_ACME_GROUP")
        ACME_URL = get_env_var("PROD_ACME_URL")
        ACME_API_KEY = get_env_var("PROD_ACME_KEY")
    else:  # DEV environment
        logger.info("Running in DEVELOPMENT environment.")
        URL = get_env_var("DEV_URL")
        BOT_TOKEN = get_env_var("DEV_BOT_TOKEN")
        ACME_GROUP = get_env_var("DEV_ACME_GROUP")
        # Optional DEV values – won't raise errors if not present
        ACME_URL = os.getenv("DEV_ACME_URL", "https://acme-qa.fly.dev/operations/dev")
        ACME_API_KEY = os.getenv("DEV_ACME_API_KEY", "")
    
except ValueError as e:
    logger.critical(f"Startup aborted due to configuration error: {e}")
    sys.exit(1)  # Exit if any critical configuration is missing

# Define conversation states
SELECT_TOKEN, SELECT_AMOUNT, SELECT_RECIPIENT, WAITING_FOR_AUTH = range(4)

# Global variables for valid and authenticated commands
VALID_COMMANDS = {'trade', 'pay', 'request', 'token', 'share', 'vault', 'start', 'menu'}
AUTHENTICATED_COMMANDS = {'pay', 'request', 'vault'}
FEATURED_TOKENS = ["PONKE", "POPCAT", "TOSHI"]  # Define featured tokens as a list of strings
COINGECKO_API_URL = "https://api.coingecko.com/api/v3/coins/{token_id}"
logger.info("Configuration successfully loaded and validated.")

import logging
from telegram import Update, Bot
from telegram.error import TelegramError
from telegram.ext import ContextTypes

# Setup logging
logger = logging.getLogger(__name__)




async def handle_recipient(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handles the input and validation of the recipient.
    Checks if the recipient is a valid EVM address, Solana address, or Telegram username.
    If valid, stores the recipient; otherwise, prompts the user to provide a valid recipient.

    Args:
        update (Update): The Telegram update object.
        context (ContextTypes.DEFAULT_TYPE): The context of the callback.

    Returns:
        int: The next state in the conversation flow.
    """
    recipient = update.message.text.strip()  # Get the recipient from user input
    bot = context.bot  # Get the bot instance from the context

    # Validate the recipient: check EVM address first
    if is_valid_evm_address(recipient):
        logger.info(f"EVM address provided: {recipient}")
        context.user_data['recipient'] = recipient  # Store the recipient

    # If not an EVM address, check for a Solana address
    elif is_valid_solana_address(recipient):
        logger.info(f"Solana address provided: {recipient}")
        context.user_data['recipient'] = recipient  # Store the recipient

    # If not an EVM or Solana address, check for a Telegram username
    elif await is_valid_telegram_username(bot, recipient):
        logger.info(f"Telegram username provided: {recipient}")
        context.user_data['recipient'] = recipient  # Store the recipient

    else:
        # If the recipient is invalid, log a warning and prompt the user
        logger.warning("Invalid recipient provided. User input: %s", recipient)
        await update.message.reply_text("🚫 Please provide a valid recipient (EVM address, Solana address, or existing Telegram username):")
        return SELECT_RECIPIENT  # Prompt for recipient again

    # Check if amount is already provided in user_data
    if 'amount' in context.user_data:
        logger.info("Recipient and amount provided, proceeding to execute action.")
        return await execute_action(update, context)  # Proceed to execute action
    else:
        logger.info("Amount not provided. Asking user for the amount.")
        await update.message.reply_text("💰 Please provide the amount:")
        return SELECT_AMOUNT  # Prompt for amount


def is_valid_evm_address(address: str) -> bool:
    """
    Validate an EVM (Ethereum Virtual Machine) address.

    Args:
        address (str): The EVM address to validate.

    Returns:
        bool: True if valid, False otherwise.
    """
    # Check if the address matches the Ethereum address format (0x followed by 40 hexadecimal characters)
    pattern = r'^0x[a-fA-F0-9]{40}$'
    is_valid = bool(re.match(pattern, address))
    logger.debug(f"EVM address validation for {address}: {is_valid}")
    return is_valid

def is_valid_solana_address(address: str) -> bool:
    """
    Validate a Solana address.

    Args:
        address (str): The Solana address to validate.

    Returns:
        bool: True if valid, False otherwise.
    """
    # Check if the address matches the Solana address format (44 characters long)
    pattern = r'^[1-9A-HJ-NP-Za-km-z]{32,44}$'
    is_valid = bool(re.match(pattern, address))
    logger.debug(f"Solana address validation for {address}: {is_valid}")
    return is_valid

async def is_valid_telegram_username(bot: Bot, username: str) -> bool:
    """
    Check if a Telegram username exists and is not a bot.

    Args:
        bot (Bot): The Telegram bot instance.
        username (str): The Telegram username to check.

    Returns:
        bool: True if the username exists and is not a bot, False otherwise.
    """
    try:
        user = await bot.get_chat(username)
        # Check if the user is not a bot
        return not user.is_bot
    except TelegramError:
        # If an error occurs (e.g., username does not exist), return False
        return False

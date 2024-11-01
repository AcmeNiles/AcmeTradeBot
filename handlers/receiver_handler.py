from config import logger, SELECT_RECEIVER
from telegram import Update
from telegram.ext import ContextTypes
from utils.getAcmeProfile import validate_user_and_tokens
from utils.tokenValidator import validate_tokens
from utils.reply import delete_loading_message


async def handle_receiver(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Main handler to process the receiver input and route based on validation."""

    receiver_username = context.user_data.get("receiver")
    logger.debug("Handling receiver function for receiver: %s", receiver_username)

    if not receiver_username:
        return await prompt_for_receiver(update, context)

    return await process_receiver(update, context, receiver_username)


async def process_receiver(update: Update, context: ContextTypes.DEFAULT_TYPE, receiver_username: str) -> int:
    """Validate the user and tokens, and proceed based on the result."""
    acme_user_data, valid_tokens, error_message = await validate_user_and_tokens(receiver_username, update, context)

    if error_message:
        return await prompt_for_receiver(update, context, error_message)

    # Store the receiver data and tokens in context after validation
    context.user_data['receiver'] = acme_user_data
    context.user_data['receiver']['tokens'] = valid_tokens
    logger.info("Proceeding with valid receiver and tokens for user: %s", update.effective_user.id)
    return True


async def prompt_for_receiver(update: Update, context: ContextTypes.DEFAULT_TYPE, error_message=None) -> int:
    """Prompt the user to enter a receiver username."""
    message = "Please enter the receiver's username."
    if error_message:
        message += f"\nError: {error_message}"
        
    await delete_loading_message(update, context)
    await update.message.reply_text(message)
    return SELECT_RECEIVER

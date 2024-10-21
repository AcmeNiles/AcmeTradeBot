from telegram import Update
from telegram.ext import ContextTypes
from utils.getAcmeProfile import get_acme_public_profile, get_user_listed_tokens, validate_user_and_tokens
from utils.tokenValidator import validate_tokens

async def handle_receiver(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Main handler to process the receiver input and route based on validation."""

    receiver_username = context.user_data.get("receiver")
    logger.debug("Handling receiver function for receiver: %s", receiver_username)

    if not receiver_username:
        return await prompt_for_receiver(update, context)

    return await process_receiver(receiver_username, update, context)


async def process_receiver(receiver_username: str, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
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

    await update.message.reply_text(message)
    return SELECT_RECEIVER

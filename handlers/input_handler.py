from config import logger
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, InputFile

from telegram.ext import ConversationHandler, ContextTypes
from config import *

# Main Handler: Routes commands to route_action or menu
async def input_to_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    from handlers.action_handler import route_action
    """
    Main handler that routes user input to the appropriate action or menu.
    """
    logger.debug("Starting input_to_action...")

    # Clear intent, token, amount, and receiver at the start
    logger.debug("Clearing user_data: intent, token, amount, receiver")
    context.user_data.pop('intent', None)
    context.user_data.pop('token', None)
    context.user_data.pop('amount', None)
    context.user_data.pop('receiver', None)

    # Get the chat type (private, group, supergroup)
    chat_type = update.message.chat.type if update.message else None
    logger.debug(f"Chat type: {chat_type}")

    # Handle group/supergroup messages
    if chat_type in ['group', 'supergroup']:
        # Check if the bot is mentioned in the group chat
        if update.message.reply_to_message and update.message.reply_to_message.from_user.id == context.bot.id:
            logger.debug("Bot mentioned in a group/supergroup. Proceeding with input handling.")
        else:
            logger.debug("Bot not mentioned in the group/supergroup. Ignoring the message.")
            return ConversationHandler.END
    
    # Get the input from the update
    input_data = await extract_input(update, context)
    logger.debug(f"Received input_data: {input_data}")

    logger.info("Routing action based on intent.")
    return await route_action(update, context)

async def extract_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Extract tokens, receiver, amount, and intent, storing them in context.user_data."""

    # Determine the relevant input text
    input_text = await get_input_text(update)
    logger.debug(f"Received input text: {input_text}")

    # Initialize extraction variables
    intent, new_tokens, receiver, amount = None, [], None, None

    # Process input text by splitting into parts
    for part in input_text.split():
        if part.startswith('/'):
            intent = part[1:]  # Remove '/' from the intent
            logger.debug(f"Intent detected: {intent}")
        elif part.startswith('@'):
            receiver = part[1:]  # Remove '/' from the intent
            logger.debug(f"Receiver detected: {receiver}")
        elif is_valid_float(part):
            amount = part
            logger.debug(f"Amount detected: {amount}")
        else:
            new_tokens.append(part.lower())
            logger.debug(f"Token detected: {part.lower()}")

    # Update context.user_data
    await update_user_data(context, new_tokens, receiver, amount, intent)

async def get_input_text(update: Update) -> str:
    """Extract relevant input text from the update with detailed logging."""
    logger.debug("Entering get_input_text function.")

    if update.callback_query:

        query = update.callback_query
        await query.answer()  # Acknowledge the callback query
        callback_data = query.data.strip()  # Strip whitespace from the callback data
        # Log the callback data
        logger.debug(f"Callback data received: {callback_data}")
        return callback_data
        
    elif update.message:
        logger.debug("Received a regular message.")
        message_text = update.message.text.strip()
        logger.debug(f"Extracted message text from regular message: '{message_text}'")
        return message_text

    logger.debug("No valid message found in the update; returning an empty string.")
    return ''


async def update_user_data(context: ContextTypes.DEFAULT_TYPE, new_tokens: list, receiver: str, amount: str, intent: str) -> None:
    """Update user context with new tokens, receiver, amount, and intent."""
    existing_tokens = set(context.user_data.get("token", []))
    combined_tokens = list(existing_tokens | set(new_tokens))  # Union to avoid duplicates
    logger.debug(f"Combined tokens: {combined_tokens}")

    # Only set the intent if it doesn't already exist in context
    if "intent" not in context.user_data:
        context.user_data["intent"] = intent
        logger.debug(f"Intent stored: {intent}")

    context.user_data.update({
        "token": combined_tokens,
        "receiver": receiver or context.user_data.get("receiver"),
        "amount": amount or context.user_data.get("amount"),
    })
    logger.debug(f"Updated context.user_data: {context.user_data}")

def is_valid_float(value: str) -> bool:
    """Check if the provided value is a valid float or integer."""
    try:
        float(value)
        return True
    except ValueError:
        return False

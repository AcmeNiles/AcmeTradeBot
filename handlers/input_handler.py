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
    input_data = await get_input(update, context)
    logger.debug(f"Received input_data: {input_data}")

    if not input_data:
        logger.error("No valid input received (neither callback nor message).")
        return await handle_message(update, context)

    # Split the input into parts
    parts = input_data.split()
    logger.debug(f"Input split into parts: {parts}")

    # Handle callback queries that might not start with '/'
    if update.callback_query:
        command = parts[0].lstrip('/')
        logger.debug(f"Callback query detected. Command: {command}")
    else:
        command = parts[0].lstrip('/')
        logger.debug(f"Regular message detected. Command: {command}")


    # Check if the command is a valid one
    if command in VALID_COMMANDS:
        logger.info(f"Command recognized: {command}")
        # Store intent without leading '/'
        context.user_data['intent'] = command  

        # Handle additional parameters as before...
        if len(parts) >= 2:
            context.user_data['token'] = parts[1]
            logger.debug(f"Token set: {context.user_data['token']}")

        if len(parts) >= 3:
            if parts[2].isdigit():
                context.user_data['amount'] = parts[2]
                logger.debug(f"Amount set: {context.user_data['amount']}")
            else:
                context.user_data['receiver'] = parts[2]
                logger.debug(f"Receiver set: {context.user_data['receiver']}")

        if len(parts) >= 4:
            context.user_data['receiver'] = parts[3]
            logger.debug(f"Receiver updated: {context.user_data['receiver']}")

        logger.info("Routing action based on intent.")
        return await route_action(update, context)

    else:
        # Redirect to menu for unrecognized commands
        logger.warning(f"Unrecognized command in input: {command}. Redirecting to menu.")
        context.user_data['intent'] = 'menu'
        logger.info("Setting intent to 'menu' and executing menu action.")
        return await route_action(update, context)  # Ensure this calls the correct function for the menu.

# Function to extract input from callback or message
async def get_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    """
    Extract input from either a callback query or a message.
    """
    if update.callback_query:
        logger.debug("Callback query received.")
        query = update.callback_query
        await query.answer()  # Acknowledge button press
        input_data = query.data.strip().lower()
        logger.debug(f"Callback data: {input_data}")
        return input_data
    elif update.message:
        logger.debug("Message received.")
        input_data = update.message.text.strip().lower()
        logger.debug(f"User input: {input_data}")
        return input_data
    return None


def parse_amount(amount_text: str) -> float:
    """
    Parse and validate the amount from user input.
    Replace with actual amount parsing logic.
    """
    try:
        amount = float(amount_text.strip())
        return amount
    except ValueError:
        return None

# Handler for collecting amount
async def handle_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handles the user's amount input and proceeds to execute the action.
    """
    amount_text = update.message.text
    amount = parse_amount(amount_text)
    if amount is not None:
        context.user_data['amount'] = amount
        logger.debug(f"Amount received: {amount}")
        return await execute_action(update, context)
    else:
        logger.debug("Invalid amount entered.")
        await update.message.reply_text("Please enter a valid amount:")
        return SELECT_AMOUNT

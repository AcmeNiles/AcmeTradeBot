import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ConversationHandler, ContextTypes
from config import AUTHENTICATED_COMMANDS
from actions.menu import process_menu
from handlers.auth_handler import is_authenticated, login_card
from handlers.token_handler import handle_token

# Setup logging
logger = logging.getLogger(__name__)

# Route Action: Handles each command's routing and intent management
async def route_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Routes the action based on the user's intent.
    Delegates execution to execute_action and clears data for start/menu/cancel.
    """
    intent = context.user_data.get('intent')
    logger.info(f"Processing action for intent: {intent}")

    if intent == 'cancel':
        logger.info(f"User initiated {intent} action, clearing user data.")
        context.user_data.clear()  # Clear user data
        await update.message.reply_text("Action cancelled. Returning to main menu.")

        # Set the intent to 'menu' and route to execute_action
        context.user_data['intent'] = 'menu'
        return await execute_action(update, context)

    elif intent in {'start', 'menu'}:
        logger.info(f"User initiated {intent} action, clearing user data.")
        context.user_data.clear()  # Clear user data

        # Set the intent to 'menu' and route to execute_action
        context.user_data['intent'] = 'menu'
        return await execute_action(update, context)


    # Route to handle_token if it's related to token actions
    if intent in {'trade', 'pay', 'request', 'share', 'token'}:
        return await handle_token(update, context)

    # If the intent is not recognized, redirect to menu
    logger.warning(f"Intent not recognized: {intent}, redirecting to menu.")
    context.user_data['intent'] = 'menu'
    return await execute_action(update, context)


# Execute the action after collecting all required data
async def execute_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Executes the action based on the user's intent, token, amount and receiver.
    """
    intent = context.user_data.get('intent')

    # Check if the intent is 'start' or 'menu'
    if intent in ['start', 'menu']:
        return await process_menu(update, context)

    token = context.user_data.get('token')
    amount = context.user_data.get('amount', None)  # Amount is optional
    receiver = context.user_data.get('receiver', None)  # Receiver is optional

    logger.info(f"Executing action: {intent}, Token: {token}, Amount: {amount}")


    # Authentication check if required
    if intent in AUTHENTICATED_COMMANDS:
        auth_link_response = await is_authenticated(context)
        if auth_link_response is not True:
            logger.info(f"User not authenticated for {intent}.")
            return await login_card(update, context, auth_link_response)  # Call login_prompt with the URL


    # Execute the corresponding action based on intent
    if intent == 'trade':
        actions.process_trade(update, token)
    elif intent == 'pay':
        actions.process_pay(update, token, amount, receiver)
    elif intent == 'request':
        actions.process_request(update, token, amount, receiver)
    else:
        logger.error(f"Unknown intent: {intent}")
        await update.message.reply_text("An error occurred. Please try again.")
        return ConversationHandler.END

    # Clear user data after processing
    logger.info(f"Action {intent} completed successfully. Clearing user data.")
    context.user_data.clear()
    return ConversationHandler.END


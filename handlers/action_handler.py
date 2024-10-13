from config import logger
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ConversationHandler, ContextTypes
from config import AUTHENTICATED_COMMANDS
from actions.menu import process_menu
from actions.trade import process_trade
from handlers.auth_handler import is_authenticated, login_card
from handlers.token_handler import handle_token

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

async def execute_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Executes the action based on the user's intent, token, amount, and receiver.
    """
    intent = context.user_data.get('intent')

    # Retrieve tg_key and auth_result from user context
    tg_key = context.user_data.get('tg_key')
    auth_result = context.user_data.get('auth_result')

    # Authenticate if not already cached
    if not auth_result or not tg_key:
        auth_result = await is_authenticated(update, context)

        # Log the newly authenticated result
        logger.info(f"New authentication result: {auth_result}")

    # Log the retrieved or newly fetched auth result and tg_key
    logger.info(f"Authentication result for {intent}: {auth_result}")
    logger.info(f"Using tg_key: {tg_key}")

    # Handle 'start' or 'menu' intents
    if intent in ['start', 'menu']:
        return await process_menu(update, context, auth_result)

    # Retrieve other necessary data from user context
    token = context.user_data.get('token')
    amount = context.user_data.get('amount')  # Optional
    receiver = context.user_data.get('receiver')  # Optional

    logger.info(f"Executing action: {intent}, Token: {token}, Amount: {amount}, Receiver: {receiver}")

    # Check if the user needs to log in for certain intents
    if intent in AUTHENTICATED_COMMANDS and 'url' in auth_result:
        # User not authenticated; redirect to login
        logger.info(f"User not authenticated for {intent}. Redirecting to login.")
        return await login_card(update, context, auth_result)

    # Execute the appropriate action based on the user's intent
    if intent == 'trade':
        await process_trade(update, context)
    elif intent == 'pay':
        await process_pay(update, context)
    elif intent == 'request':
        await process_request(update, context)
    else:
        logger.error(f"Unknown intent: {intent}")
        await update.message.reply_text("An error occurred. Please try again.")
        return ConversationHandler.END

    # Retain tg_key and auth_result while clearing other user data
    logger.info(f"Action {intent} completed successfully. Clearing user data except auth_result and tg_key.")

    # Store the necessary data before clearing
    auth_result = context.user_data.get('auth_result')
    tg_key = context.user_data.get('tg_key')

    # Clear the user_data and retain only the required keys
    context.user_data.clear()  # Clear all existing data
    context.user_data.update({
        'auth_result': auth_result,
        'tg_key': tg_key
    })

    return ConversationHandler.END

from config import logger
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ConversationHandler, ContextTypes
from config import AUTHENTICATED_COMMANDS
from actions.menu import process_menu
from actions.trade import process_trade
from actions.list import process_list
from utils.getAcmeProfile import process_user_tokens
from handlers.auth_handler import is_authenticated, login_card
from handlers.token_handler import handle_token
from handlers.receiver_handler import handle_receiver
import time
from config import SELECT_TOKEN, SELECT_RECEIVER, SELECT_AMOUNT, WAITING_FOR_AUTH

async def route_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Routes the action based on the user's intent.
    Delegates execution to `execute_action` and manages states for menus and unrecognized intents.
    """
    intent = context.user_data.get('intent')
    logger.info(f"Processing action for intent: {intent}")

    # Retrieve tg_key and auth_result from user context
    auth_result = context.user_data.get('auth_result')

    # Authenticate if not already cached
    if not auth_result:
        start_time = time.time()  # Start timing authentication
        auth_result = await is_authenticated(update, context)
        logger.info(f"is_authenticated took {time.time() - start_time:.2f} seconds.")
        #logger.info(f"New authentication result: {auth_result}")

    # Log the retrieved or newly fetched auth result and tg_key
    #logger.info(f"Authentication result for {intent}: {auth_result}")
    
    # Helper function to handle state transitions
    async def check_state(state):
        if state in {SELECT_TOKEN, SELECT_RECEIVER, SELECT_AMOUNT}:
            return state  # Pause and wait for input
        return await execute_action(update, context)  # Proceed to action execution

    # Early return for basic intents (logout, menu, start, or cancel)
    if intent in {'logout', 'start', 'menu', 'cancel'}:
        logger.info(f"User initiated {intent} action, clearing data and routing to menu.")
        if intent == 'logout':
            context.user_data.clear()  # Clear all data on logout
        context.user_data['intent'] = 'menu'
        return await execute_action(update, context)

    # Handle vault intent separately
    if intent == 'vault':
        logger.info("Vault action detected, executing vault intent.")
        return await execute_action(update, context)

    # Handle trade, share, and buy intents with token and receiver checks
    if intent in {'trade', 'share', 'buy'}:
        receiver = context.user_data.get('receiver', None)
        tokens = context.user_data.get('tokens', [])
        # Case 1: Handle receiver only (when receiver exists and token is missing or empty)
        if receiver is not None and (tokens is None or tokens == []):
            logger.info("Handling receiver only; executing action.")
            state = await handle_receiver(update, context)
            context.user_data['intent'] = 'list'  # Set intent to 'list'
            return await execute_action(update, context) if state != SELECT_RECEIVER else state

        # Case 2: Handle token only (when token exists and receiver is missing or None)
        elif tokens is not None and tokens != [] and receiver is None:
            logger.info("Handling token only; executing action.")
            state = await handle_token(update, context)
            return await execute_action(update, context) if state != SELECT_TOKEN else state

        # Case 3: Handle both token and receiver (when both exist)
        elif tokens is not None and tokens != [] and receiver is not None:
            logger.info("Handling both token and receiver.")
            receiver_state = await handle_receiver(update, context)
            token_state = await handle_token(update, context)

            if token_state != SELECT_TOKEN or receiver_state != SELECT_RECEIVER:
                return await execute_action(update, context)

            # If both are invalid, validate token and wait for input if needed
            return await handle_token(update, context)

        # Case 4: Handle neither token nor receiver for 'share' (if no token and intent is 'share')
        elif intent == "share" and (tokens is None or tokens == []):
            logger.info("Handling 'share' with no token, proceeding to execute action.")
            return await execute_action(update, context)

        # Case 5: Handle neither token nor receiver (default case when both are missing)
        else:
            state = await handle_token(update, context)
            if state == SELECT_TOKEN:
                return state
            return await execute_action(update, context)

    # Handle pay and request intents with sequential validation
    if intent in {'pay', 'request'}:
        if 'token' in context.user_data:
            logger.info("Validating token first in pay/request intent.")
            state = await handle_token(update, context)
            if state == SELECT_TOKEN:
                return state  # Wait for token input

        if 'receiver' in context.user_data:
            logger.info("Validating receiver in pay/request intent.")
            state = await handle_receiver(update, context)
            if state == SELECT_RECEIVER:
                return state  # Wait for receiver input

        if 'amount' not in context.user_data:
            logger.info("Requesting amount input.")
            state = await handle_amount(update, context)
            if state == SELECT_AMOUNT:
                return state  # Wait for amount input

        # All required inputs are validated, execute the action
        return await execute_action(update, context)

    # Handle list intents separately (use first token by default)
    if intent == 'list':
        logger.info("Handling list intent, routing to token handler.")
        # Check if the user needs to log in for certain intents
        if 'url' in auth_result:
            # User not authenticated; redirect to login
            logger.info(f"User not authenticated for {intent}. Redirecting to login.")
            start_time = time.time()  # Start timing login_card
            result = await login_card(update, context, auth_result)
            logger.info(f"login_card took {time.time() - start_time:.2f} seconds.")
            return result
        else:
            await process_user_tokens(update, context)
            state = await handle_token(update, context)
            if state == SELECT_TOKEN:
                return state  # Wait for token input
            return await execute_action(update, context)

    # Handle unrecognized intents by routing to menu
    logger.warning(f"Unrecognized intent: {intent}, redirecting to menu.")
    context.user_data['intent'] = 'menu'
    return await execute_action(update, context)


async def execute_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Executes the action based on the user's intent, token, amount, and receiver.
    """

    intent = context.user_data.get('intent')
    auth_result = context.user_data.get('auth_result')
    tokens = context.user_data.get('tokens') or None

    # Handle 'start' or 'menu' intents
    if intent in ['start', 'menu']:
        start_time = time.time()  # Start timing process_menu
        result = await process_menu(update, context)
        logger.info(f"process_menu took {time.time() - start_time:.2f} seconds.")
        return result

    # Check if the user needs to log in for certain intents
    if intent in AUTHENTICATED_COMMANDS and 'url' in auth_result:
        # User not authenticated; redirect to login
        logger.info(f"User not authenticated for {intent}. Redirecting to login.")
        start_time = time.time()  # Start timing login_card
        result = await login_card(update, context, auth_result)
        logger.info(f"login_card took {time.time() - start_time:.2f} seconds.")
        return result

    logger.info(f"Executing action: {intent}")

    # Execute the appropriate action based on the user's intent
    if intent == 'list':
        # If intent is 'list', return all tokens as an array
        start_time = time.time()  # Start timing process_trade
        await process_list(update, context)
        logger.info(f"process_list took {time.time() - start_time:.2f} seconds.")
        return ConversationHandler.END

    if intent in ['trade', 'buy','share']:
        if intent == 'share' and (tokens is None or tokens == []):
            start_time = time.time()  # Start timing process_pay
            await process_user_tokens(update, context)
            context.user_data['tokens'] = context.user_data['auth_result']['tokens']
            await process_list(update, context)
            logger.info(f"process_share took {time.time() - start_time:.2f} seconds.")
            return ConversationHandler.END
        else:
            start_time = time.time()  # Start timing process_trade
            await process_trade(update, context)
            logger.info(f"process_trade took {time.time() - start_time:.2f} seconds.")
            return ConversationHandler.END
    
    # Check if intent is 'share', if yes, process user and list

        # Otherwise, just prompt for token
    elif intent == 'pay':
        start_time = time.time()  # Start timing process_pay
        await process_pay(update, context)
        logger.info(f"process_pay took {time.time() - start_time:.2f} seconds.")
    elif intent == 'request':
        start_time = time.time()  # Start timing process_request
        await process_request(update, context)
        logger.info(f"process_request took {time.time() - start_time:.2f} seconds.")
    else:
        logger.error(f"Unknown intent: {intent}")
        await update.message.reply_text("An error occurred. Please try again.")
        return ConversationHandler.END

    # Retain tg_key and auth_result while clearing other user data
    logger.info(f"Action {intent} completed successfully. Clearing user data except auth_result and tg_key.")

    # Store the necessary data before clearing
    auth_result = context.user_data.get('auth_result')
    invite_link = context.user_data.get('invite_link')

    # Clear the user_data and retain only the required keys
    context.user_data.clear()  # Clear all existing data
    context.user_data.update({
        'auth_result': auth_result,
        'invite_link': invite_link
    })

    return ConversationHandler.END

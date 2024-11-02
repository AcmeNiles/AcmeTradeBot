from config import logger
from telegram import Update
from telegram.ext import ConversationHandler, ContextTypes
from config import AUTHENTICATED_COMMANDS
from actions.menu import process_menu
from actions.trade import process_trade
from actions.list import process_list
from utils.reply import send_why_trade, send_why_list, send_loading_message

from utils.getAcmeProfile import process_user_top3
from handlers.auth_handler import is_authenticated, login_card, store_auth_result, get_auth_result, get_user_top3
from handlers.token_handler import handle_token
from handlers.receiver_handler import handle_receiver
import time
from config import SELECT_TOKEN, SELECT_RECEIVER, SELECT_AMOUNT

async def route_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Routes the action based on the user's intent, handling authentication,
    token, receiver, and amount validation, then executing the action.
    """
    intent = context.user_data.get('intent')
    tokens = context.user_data.get('tokens')
    # Get chat type (private, group, supergroup)
    chat_type = update.message.chat.type if update.message else None
    logger.debug(f"Chat type: {chat_type}")

    # Early exit if in group/supergroup and intent is None or not a valid command
    if chat_type in ['group', 'supergroup']:
        if not tokens or intent not in AUTHENTICATED_COMMANDS:
            return ConversationHandler.END

    logger.info(f"User {update.effective_user.id} - Processing action for intent: {intent}")
    await send_loading_message(update, context)
    # Fetch authentication result only if necessary after initial checks
    auth_result = await get_auth_result(update, context) or await authenticate_user(update, context)

    # Handle intents that don't require authentication
    if intent == 'why_trade':
        return await send_why_trade(update, context)
    elif intent == 'why_list':
        return await send_why_list(update, context)
    elif intent in {'logout', 'start', 'menu', 'cancel'}:
        return await handle_special_intents(update, context, intent)

    # Redirect if authentication is required
    if intent in AUTHENTICATED_COMMANDS and (not auth_result or 'url' in auth_result):
        return await handle_login_redirect(update, context, auth_result, intent)

    # Handle trade-related intents
    if intent in {'trade', 'top3', 'share', 'buy'}:
        return await handle_trade_related(update, context, tokens)

    # Handle 'list' intent
    if intent == 'list':
        return await handle_list_intent(update, context)

    # Handle 'pay' and 'request' intents
    if intent in {'pay', 'request'}:
        return await handle_payment_intents(update, context, intent)

    # Unrecognized intent, redirect to menu
    logger.warning(f"User {update.effective_user.id} - Unrecognized intent: {intent}, redirecting to menu.")
    context.user_data['intent'] = 'menu'
    return await process_menu(update, context)


async def authenticate_user(update, context):
    """Authenticate the user if auth_result is not available.

    Returns:
        dict: The authentication result if successful, or None if authentication fails.
    """
    start_time = time.time()
    user_tg_id = update.effective_user.id

    try:
        auth_result = await is_authenticated(update, context)
        logger.info(f"User {update.effective_user.id} - Authentication took {time.time() - start_time:.2f} seconds.")

        # Store the authentication result using the store_auth_result function
        if auth_result:
            success = await store_auth_result(context.application, user_tg_id, auth_result)
            if success:
                logger.info(f"Successfully stored auth result for user: {user_tg_id}")
            else:
                logger.warning(f"Failed to store auth result for user: {user_tg_id}")

        return auth_result if auth_result else None
    except aiohttp.ClientError as e:
        logger.error(f"User {update.effective_user.id} - Network error during authentication: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"User {update.effective_user.id} - Authentication failed: {str(e)}")
        return None

async def handle_special_intents(update, context, intent):
    """Handles 'logout', 'start', 'menu', or 'cancel' intents."""
    logger.info(f"User {update.effective_user.id} - Initiated {intent} action, clearing data and routing to menu.")
    if intent == 'logout':
        context.user_data.clear()  # Clear all data on logout
    context.user_data['intent'] = 'menu'
    return await process_menu(update, context)


async def handle_login_redirect(update, context, auth_result, intent):
    """Handles login redirection for unauthenticated users."""
    logger.info(f"User {update.effective_user.id} - Not authenticated for {intent}. Redirecting to login.")
    start_time = time.time()  # Start timing login_card
    result = await login_card(update, context, auth_result)
    logger.info(f"User {update.effective_user.id} - login_card took {time.time() - start_time:.2f} seconds.")
    return ConversationHandler.END

async def handle_trade_related(update: Update, context: ContextTypes.DEFAULT_TYPE, tokens):
    """Handles intents like 'trade', 'top3', 'share', and 'buy'."""
    receiver = context.user_data.get('receiver')
    logger.debug(f"User {update.effective_user.id} - Handling trade-related intent. Tokens: {tokens}, Receiver: {receiver}")

    # Case 1: Both tokens and receiver are None
    if not tokens and not receiver:
        # Check for 'top3' intent
        if context.user_data.get('intent') == "top3":
            logger.info(f"User {update.effective_user.id} - Special 'top3' intent. Fetching user tokens.")

            # Retrieve top3 tokens for the user via helper function
            top3_tokens = await get_user_top3(update, context)
            
            # If we have tokens, proceed with the `process_list`
            if top3_tokens:
                context.user_data['tokens'] = top3_tokens
                return await process_list(update, context)
            else:
                logger.info(f"User {update.effective_user.id} - 'top3' tokens incomplete or missing, redirecting to token selection.")
                context.user_data["intent"] = "list"
                state = await handle_token(update, context)
                return state if state == SELECT_TOKEN else ConversationHandler.END

        # If 'top3' intent is not set, redirect to token selection as usual
        logger.info(f"User {update.effective_user.id} - Both tokens and receiver are missing. Redirecting to token selection.")
        state = await handle_token(update, context)
        return state if state == SELECT_TOKEN else ConversationHandler.END

    # Case 2: Receiver exists, but tokens are None
    if receiver and not tokens:
        state = await handle_receiver(update, context)
        context.user_data['intent'] = 'list'
        context.user_data['tokens'] = (
            context.user_data['receiver']['tokens'] if isinstance(context.user_data.get('receiver'), dict) else []
        )
        if state != SELECT_RECEIVER:
            return await process_list(update, context)
        return state if state == SELECT_RECEIVER else ConversationHandler.END

    # Case 3: Tokens exist, but receiver is None
    if tokens and not receiver:
        state = await handle_token(update, context)
        if state not in [SELECT_TOKEN, ConversationHandler.END]:
            return await process_trade(update, context)
        return state if state == SELECT_TOKEN else ConversationHandler.END

    # Case 4: Both tokens and receiver exist
    if tokens and receiver:
        receiver_state = await handle_receiver(update, context)
        token_state = await handle_token(update, context)

        # Proceed to `process_trade` if neither state is `SELECT_TOKEN` or `SELECT_RECEIVER`
        if token_state != [SELECT_TOKEN, ConversationHandler.END] and receiver_state != SELECT_RECEIVER and len(context.user_data.get('tokens', [])) == 0:
            return await process_trade(update, context)

        # If the states require further interaction, end the conversation
        return ConversationHandler.END

async def handle_list_intent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles 'list' intent by guiding users to select or update their top3 tokens before listing."""
    user_id = update.effective_user.id
    logger.info(f"User {user_id} - Handling 'list' intent. Initiating token selection if required.")

    # Redirect to token selection for updating or confirming top3 tokens
    state = await handle_token(update, context)

    # Only proceed if token selection is complete (state is not SELECT_TOKEN)
    if state != SELECT_TOKEN:
        # Update top3 tokens after token selection is complete
        top3_tokens = await get_user_top3(update, context)
        context.user_data['tokens'] = top3_tokens

        # Proceed to process the list with updated tokens
        return await process_list(update, context)

    # If further token selection interaction is needed, return the current state
    return state if state == SELECT_TOKEN else ConversationHandler.END

async def handle_payment_intents(update, context, intent):
    """Handles 'pay' and 'request' intents with validation."""
    logger.info(f"User {update.effective_user.id} - Handling {intent} intent.")

    # Token validation
    if 'token' in context.user_data:
        state = await handle_token(update, context)
        if state == SELECT_TOKEN:
            return state

    # Receiver validation
    if 'receiver' in context.user_data:
        state = await handle_receiver(update, context)
        if state == SELECT_RECEIVER:
            return state

    # Amount validation
    if 'amount' not in context.user_data:
        state = await handle_amount(update, context)
        if state == SELECT_AMOUNT:
            return state

    await process_pay(update, context) if intent == 'pay' else await process_request(update, context)
    return ConversationHandler.END
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import CallbackContext, ConversationHandler
from utils.checkTicker import check_ticker
from utils.createJWT import get_user_data
from utils.reply import reply, reply_photo
from createTradingLink import create_trading_link
from config import SELECT_TOKEN, TRADE_CARD, MENU

logger = logging.getLogger(__name__)

### State 1: SELECT_TOKEN ###
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from helpers import validate_ticker, create_trade_card, reply

# State Constants
SELECT_TOKEN = 1  # Represents the state where the user selects a token
TRADE_CARD = 2    # Represents the state for displaying the trade card
MENU = 3          # Represents the main menu state

----

async def trade(update: Update, token: str) -> dict:
    """
    Handles the trading action by processing the provided token and amount.
    Returns user data and relevant trading information.
    """
    logger.debug(f"Starting trade with token: {token} and amount: {amount}")

    # Get Telegram account information using the new function
    telegram_account = get_tg_user(update)
    logger.debug(f"Telegram account info: {telegram_account}")

    # Now you can continue to process the trade
    # Example: Create a trading link
    trading_link = await create_trading_link(telegram_account, token)  # Assume this function is defined

    if trading_link:
        # If the trading link is successfully created, send the trade confirmation
        await update.message.reply_text(f"Trading link created: {trading_link}")
    else:
        await update.message.reply_text("Failed to create trading link.")

    # Return all relevant user data and trading information
    return {
        "telegram_account": telegram_account,
        "trading_link": trading_link,
        "token": token,
        "amount": amount,
    }












-----
async def select_token(update, context, intent: str) -> int:
    """
    Handles the selection of a token for trading or payment. It manages user input,
    validates ticker data, and transitions to the appropriate card state if valid.

    Args:
        update: Incoming update from Telegram.
        context: Callback context containing user data and state information.
        intent: Action user wants to execute on a token (trade or pay).

    Returns:
        int: Next state constant based on user actions.
    """
    logger.debug("Entering select_token state.")

    # Initialize the user's state and ticker data
    context.user_data['state'] = SELECT_TOKEN
    context.user_data['ticker'] = None

    # Initialize prompt, buttons, and card function based on intent
    if intent == "pay":
        ask_prompt = "Select or *Type* the token you want to request:"
        buttons = [
            [InlineKeyboardButton("USDC", callback_data='USDC')],
        ]
        command_prefix = '/pay'  # Command prefix for payment
        create_card = create_payment_card  # Placeholder for payment card function
    else:  # Default to trade intent
        ask_prompt = "Select or *Type* the token you want to trade:"
        buttons = [
            [InlineKeyboardButton("PONKE", callback_data='PONKE'),
             InlineKeyboardButton("BRETT", callback_data='BRETT')],
        ]
        command_prefix = '/trade'  # Default command prefix for trading
        create_card = create_trade_card  # Function to transition to trade card

    try:
        # Check if the function was triggered by a callback query (button click)
        if update.callback_query:
            logger.debug("Triggered by a callback query.")
            query = update.callback_query
            await query.answer()  # Acknowledge the button press

            # Get the ticker from the callback data and convert it to uppercase
            ticker = query.data.upper()
            logger.debug(f"Ticker received from button click: {ticker}")

            # Validate the selected ticker
            if not await validate_ticker(ticker, update, buttons, ask_prompt):
                logger.warning(f"Ticker '{ticker}' is invalid. Asking user to select again.")
                return SELECT_TOKEN  # Stay in SELECT_TOKEN state if invalid

            logger.debug(f"Received valid ticker via button: {ticker}")
            context.user_data['ticker'] = ticker  # Store the valid ticker
            return await create_card(update, context)  # Proceed to the appropriate card

        # Check if the command corresponding to the intent is used
        if context.args and update.message.text.startswith(command_prefix):
            logger.debug(f"Triggered by {command_prefix} command.")
            ticker = context.args[0].upper()  # Extract ticker from command arguments
            logger.debug(f"Ticker received from {command_prefix} command: {ticker}")

            # Validate the ticker from the command
            if not await validate_ticker(ticker, update, buttons, ask_prompt):
                logger.warning(f"Ticker '{ticker}' is invalid. Asking user to select again.")
                return SELECT_TOKEN  # Stay in SELECT_TOKEN state if invalid

            logger.debug(f"Received valid ticker via {command_prefix} command: {ticker}")
            context.user_data['ticker'] = ticker  # Store the valid ticker
            return await create_card(update, context)  # Proceed to the appropriate card

        # Check if the user provided ticker text input
        if update.message and update.message.text.strip():
            logger.debug("Triggered by text input.")
            ticker = update.message.text.strip().upper()  # Extract and format ticker
            logger.debug(f"Ticker received from text input: {ticker}")

            # Validate the ticker from the text input
            if not await validate_ticker(ticker, update, buttons, ask_prompt):
                logger.warning(f"Ticker '{ticker}' is invalid. Asking user to select again.")
                return SELECT_TOKEN  # Stay in SELECT_TOKEN state if invalid

            logger.debug(f"Received valid ticker via text input: {ticker}")
            context.user_data['ticker'] = ticker  # Store the valid ticker
            return await create_card(update, context)  # Proceed to the appropriate card

        # If no valid input is provided, prompt the user to enter a ticker again
        logger.debug("No valid ticker provided. Asking for ticker.")
        await reply(update, ask_prompt, reply_markup=InlineKeyboardMarkup(buttons))
        return SELECT_TOKEN  # Stay in SELECT_TOKEN state

    except Exception as e:
        # Log any errors that occur during the execution of this function
        logger.error(f"Error in select_token: {e}")
        await reply(update, "An error occurred. Please try again.")
        return MENU  # Return to menu in case of error


------




async def select_token(update: Update, context: CallbackContext) -> int:
    logger.debug("Entering select_token function.")

    # Set state and reset ticker
    context.user_data['state'] = SELECT_TOKEN
    context.user_data['ticker'] = None
    ask_prompt = "*Type* the ticker or select one to trade:"

    buttons = [
        [InlineKeyboardButton("PONKE", callback_data='PONKE'),
         InlineKeyboardButton("BRETT", callback_data='BRETT')],
    ]

    try:
        # If triggered by a callback query (button click)
        if update.callback_query:
            return await handle_callback_query(update, context, buttons, ask_prompt)

        # If /trade command is used, ensure it behaves like a command, not just text
        if context.args and update.message.text.startswith('/trade'):
            return await handle_command_input(update, context, buttons, ask_prompt)

        # If text input is provided, handle that as well
        if update.message and update.message.text.strip():
            return await handle_text_input(update, context, buttons, ask_prompt)

        # No valid input, ask for ticker again
        logger.debug("No valid ticker provided. Asking for ticker.")
        await reply(update, ask_prompt, reply_markup=InlineKeyboardMarkup(buttons))
        return SELECT_TOKEN  # Stay in SELECT_TOKEN state

    except Exception as e:
        logger.error(f"Error in select_token: {e}")
        await reply(update, "An error occurred. Please try again.")
        return MENU  # Return to menu in case of error


### Helper Functions ###

async def handle_callback_query(update: Update, context: CallbackContext, buttons, ask_prompt):
    query = update.callback_query
    await query.answer()

    ticker = query.data.upper()
    if not is_valid_ticker(ticker):
        await reply(update, ask_prompt, reply_markup=InlineKeyboardMarkup(buttons))
        return SELECT_TOKEN  # Stay in SELECT_TOKEN state

    logger.debug(f"Received ticker via button: {ticker}")
    context.user_data['ticker'] = ticker
    return await create_trade_card(update, context)


async def handle_command_input(update: Update, context: CallbackContext, buttons, ask_prompt):
    ticker = context.args[0].upper()
    if not is_valid_ticker(ticker):
        await reply(update, ask_prompt, reply_markup=InlineKeyboardMarkup(buttons))
        return SELECT_TOKEN  # Stay in SELECT_TOKEN state

    logger.debug(f"Received ticker via /trade command: {ticker}")
    context.user_data['ticker'] = ticker
    return await create_trade_card(update, context)


async def handle_text_input(update: Update, context: CallbackContext, buttons, ask_prompt):
    ticker = update.message.text.strip().upper()
    token_data = await check_ticker(ticker, update, "trade")

    if token_data:
        logger.debug(f"Valid ticker via text input: {ticker}")
        context.user_data['ticker'] = ticker
        return await create_trade_card(update, context)
    else:
        logger.warning(f"Invalid ticker: {ticker}. Asking for valid ticker.")
        await reply(update, ask_prompt, reply_markup=InlineKeyboardMarkup(buttons))
        return SELECT_TOKEN  # Stay in SELECT_TOKEN state until valid input


def is_valid_ticker(ticker: str) -> bool:
    return bool(ticker and not ticker.isspace())


async def create_trade_card(update: Update, context: CallbackContext):
    context.user_data['state'] = TRADE_CARD
    return await trade_card(update, context)


### State 2: Trade Card - Display Trade Card ###
async def trade_card(update: Update, context: CallbackContext) -> int:
    logger.debug(f"Context user_data in trade_card: {context.user_data}")
    ticker = context.user_data.get('ticker')
    logger.debug(f"Ticker retrieved in trade_card: {ticker}")
    context.user_data['state'] = TRADE_CARD  # Set state to TRADE_CARD

    try:
        # Validate the ticker and retrieve token data
        logger.debug(f"Checking ticker: {ticker}")
        token_data = await check_ticker(ticker, update, "trade")

        if token_data:
            logger.debug(f"Ticker data found for {ticker}. Processing trade card.")
            user_data = get_user_data(update)
            trading_card_text = (f"📢 *Buy {token_data['symbol']}*\\!\n\n"
                                 f"🔗 *Chain ID*\n {token_data['chainId']}\n\n"
                                 f"🏷️ *Token Address*\n {token_data['tokenAddress']}\n\n")

            # Generate trading link
            try:
                trading_link = create_trading_link(user_data, token_data['chainId'], token_data['tokenAddress'], "")
                if trading_link:
                    logger.debug(f"Trading link created successfully for {ticker}.")
                    buttons = [[
                        InlineKeyboardButton(
                            f"Trade {ticker}",
                            web_app=WebAppInfo(url=trading_link)
                        )                    ]]
                    reply_markup = InlineKeyboardMarkup(buttons)

                    # Send trading card with image and options
                    await reply_photo(update, trading_card_text, reply_markup)
                    logger.debug(f"Trading card presented for {ticker}.")
                    return MENU  # Continue in MENU state
                else:
                    logger.warning(f"Failed to create trading link for ticker: {ticker}.")
                    await reply(update, "Trading link couldn't be created.")
                    return MENU  # End conversation if trading link fails

            except Exception as e:
                logger.error(f"Error while creating trading link for {ticker}: {e}")
                await reply(update, "An error occurred while creating the trading link.")
                return MENU  # End conversation on error

        else:
            logger.warning(f"No data found for ticker: {ticker}. Ending conversation.")
            await reply(update, "Ticker not found. Please try again.")
            await select_token(update, context)
            return SELECT_TOKEN  # Back to ticker if ticker is invalid

    except Exception as e:
        logger.error(f"Error in trade_card: {e}")
        await reply(update, "An error occurred. Please try again.")
        return MENU  # End conversation on error

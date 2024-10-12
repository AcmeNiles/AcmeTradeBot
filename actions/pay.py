from config import logger
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, WebAppInfo
from telegram.ext import (
    CallbackContext,  # Fixed the import to use CallbackContext correctly
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
    Application,
    ContextTypes,
    CallbackQueryHandler,
)
from createPaymentLink import create_pay_link
from config import MENU_IMAGE_URL
from utils.checkTicker import check_ticker
from utils.createJWT import get_user_data
from commands.ticker import ask_ticker

### State 1: Pay Flow Start - Ask for Ticker ###
async def start_pay(update: Update, context: CallbackContext) -> int:
    logger.debug("Starting pay process.")
    context.user_data['state'] = ASK_PAY_TICKER  # Set initial state to ASK_PAY_TICKER

    try:
        await ask_ticker(update, context, intent="pay")  # Reference ask_ticker with 'pay' intent
        context.user_data['state'] = ASK_PAY_AMOUNT  # Update state to ASK_PAY_AMOUNT
        return ASK_PAY_AMOUNT

    except Exception as e:
        logger.error(f"Error in start_pay: {e}")
        await reply(update, "An error occurred. Please try again.")
        context.user_data['state'] = MENU  # Go to menu on failure
        return MENU

### State 3: Ask for Pay Ticker ###
async def ask_pay_ticker(update: Update, context: CallbackContext) -> int:
    """
    Prompts the user to select a ticker for the payment flow. Handles the user's selection of a ticker 
    and proceeds to the payment card.
    """
    logger.debug("Entering ask_pay_ticker function. Asking for ticker with pay intent.")
    context.user_data['state'] = ASK_PAY_TICKER  # Update state to ASK_PAY_TICKER

    try:
        # Ask the user to select a ticker
        await ask_ticker(update, context, intent="pay")

        # If the user selects a ticker, process it
        if update.callback_query:
            query = update.callback_query
            await query.answer()  # Acknowledge the callback query
            ticker = query.data.upper()  # Get the selected ticker
            logger.debug(f"User selected ticker for payment: {ticker}")

            # Proceed to pay card with the selected ticker
            await pay_card(update, context, ticker)
            return PAY_AMOUNT  # Return state to PAY_CARD after processing

    except Exception as e:
        logger.error(f"Error in ask_pay_ticker: {e}")
        await reply(update, "An error occurred while asking for the ticker. Please try again.")
        return ConversationHandler.END  # End conversation on error

### State 3: Ask for Pay Amount ###
async def ask_pay_amount(update: Update, context: CallbackContext) -> int:
    logger.debug("Entering ask_pay_amount function.")
    context.user_data['state'] = ASK_PAY_AMOUNT  # Update state to ASK_PAY_AMOUNT

    try:
        amount = update.message.text
        if amount.replace('.', '', 1).isdigit():  # Valid number check
            logger.debug(f"Valid amount received: {amount}")
            # Store the amount in user data
            context.user_data['amount'] = amount
            token_data = context.user_data.get('token_data')  # Retrieve stored token data
            user_data = get_user_data(update)

            # Proceed to the payment card state where we generate the payment link
            await process_payment(update, context, token_data, amount, user_data)
            context.user_data['state'] = PAY_CARD  # Update state to PAY_CARD after processing
            logger.debug("Successfully processed payment amount.")
            return PAY_CARD
        else:
            logger.warning("Invalid amount provided by user.")
            await reply(update, "Please provide a valid numeric amount.")
            return ASK_PAY_AMOUNT

    except Exception as e:
        logger.error(f"Error in ask_pay_amount: {e}")
        await reply(update, "An error occurred. Please try again.")
        context.user_data['state'] = ASK_PAY_AMOUNT  # Return to ASK_PAY_AMOUNT on failure
        return ASK_PAY_AMOUNT

### State 3: Pay Card - Process Payment and Show Payment Link ###
async def pay_card(update: Update, context: CallbackContext, ticker: str) -> int:
    logger.debug(f"Entering pay_card function with ticker: {ticker}")
    # Set the state to track the user is in the PAY_CARD stage
    context.user_data['state'] = PAY_CARD

    try:
        # Fetch token data based on the ticker
        token_data = await check_ticker(ticker, update, "pay")

        if token_data:
            context.user_data['token_data'] = token_data  # Store token data in user context

            # Generate pay card info and buttons
            pay_card_text = (
                f"📢 *Pay in {token_data['symbol']}*\\!\n\n"
                f"🔗 *Chain ID*: {token_data['chainId']}\n"
                f"🏷️ *Token Address*: {token_data['tokenAddress']}\n"
            )

            # Try creating the pay link
            pay_link = create_pay_link(get_user_data(update), token_data['chainId'], token_data['tokenAddress'], "")
            if pay_link:
                buttons = [
                    [InlineKeyboardButton(f"Pay in {ticker}", web_app=WebAppInfo(url=pay_link))],
                    [InlineKeyboardButton("Main Menu", callback_data='MENU')],
                ]
                reply_markup = InlineKeyboardMarkup(buttons)
                await reply_photo(update, pay_card_text, reply_markup)

                # Transition to MENU after success
                context.user_data['state'] = MENU
                logger.debug(f"Pay card presented. Transitioning to MENU state.")
                return MENU

            else:
                logger.warning(f"Failed to create pay link for ticker: {ticker}")
                context.user_data['state'] = ASK_PAY_AMOUNT  # Return to ASK_PAY_AMOUNT to retry
                return ASK_PAY_AMOUNT  # Retry amount input

        else:
            logger.warning(f"No data found for ticker: {ticker}. Asking for a valid ticker.")
            context.user_data['state'] = ASK_PAY_TICKER  # Return to ASK_PAY_TICKER on invalid ticker
            await ask_ticker(update, context, intent="pay")
            return ASK_PAY_TICKER

    except Exception as e:
        logger.error(f"Error in pay_card: {e}")
        await reply(update, "An error occurred. Please try again.")
        context.user_data['state'] = ASK_PAY_TICKER  # Return to ASK_PAY_TICKER on error
        return ASK_PAY_TICKER  # Retry ticker selection

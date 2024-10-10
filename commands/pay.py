import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, WebAppInfo
from telegram.ext import (
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
    Application,
    ContextTypes,
    CallbackQueryHandler,
)
from createPaymentLink import create_pay_link
from config import WELCOME_IMAGE_URL
from utils.checkTicker import check_ticker
from utils.createJWT import get_user_data

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Define conversation states
ASK_PAY_TICKER, ASK_AMOUNT = range(2)

# Function to handle the /pay command
async def pay(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.debug("Received command /pay with arguments: %s", context.args)
    context.user_data['state'] = ASK_PAY_TICKER  # Set the state to ASK_PAY_TICKER
    if context.args and len(context.args) == 1 and context.args[0].isalpha():
        ticker = context.args[0].upper()
        token_data = await check_ticker(ticker, update, "pay")
        if token_data:
            logger.debug("Ticker provided via command: %s", ticker)
            context.user_data['token_data'] = token_data  # Store token data
            await update.message.reply_text("Please enter amount.")
            return ASK_AMOUNT
        else:
            logger.warning("Invalid ticker provided or no ticker in command.")
            await prompt_for_pay_ticker(update)
            return ASK_PAY_TICKER  # Move to the asking state
    else:
        logger.warning("Invalid ticker provided or no ticker in command.")
        await prompt_for_pay_ticker(update)
        return ASK_PAY_TICKER  # Move to the asking state

async def prompt_for_pay_ticker(update: Update):
    keyboard = [
        [InlineKeyboardButton("USDC", callback_data='USDC')],
        [InlineKeyboardButton("Cancel", callback_data='cancel')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Please enter one of the tokens you'd like to get paid in:",
        reply_markup=reply_markup)

async def pay_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    ticker = query.data
    logger.debug("Button clicked with callback data: %s", ticker)

    if ticker == 'cancel':
        await cancel(update, context)
        return ConversationHandler.END

    # Ensure we're in the correct state before processing the ticker
    if context.user_data.get('state') == ASK_PAY_TICKER:
        token_data = await check_ticker(ticker, update, "pay")
        if token_data:
            logger.debug("Valid ticker received from button: %s", ticker)
            context.user_data['token_data'] = token_data  # Store token data
            await query.edit_message_text(text="Please enter amount.")
            return ASK_AMOUNT
        else:
            logger.warning("Invalid ticker selected by user.")
            await query.edit_message_text(text="Please provide a valid ticker.")
            await prompt_for_pay_ticker(update)
            return ASK_PAY_TICKER
    else:
        logger.warning("Button clicked but not in the correct state for payment.")
        await query.edit_message_text(text="Please initiate payment using /pay or select a valid option.")
        return ConversationHandler.END  # Or handle this case appropriately

async def ask_for_ticker(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    ticker = update.message.text.upper()
    token_data = await check_ticker(ticker, update, "pay")
    if token_data:
        logger.debug("User response received for ticker: %s", ticker)
        context.user_data['token_data'] = token_data  # Store token data
        await update.message.reply_text("Please enter amount.")
        return ASK_AMOUNT
    else:
        logger.warning("Invalid ticker provided by user.")
        await update.message.reply_text("Please provide a valid ticker.")
        await prompt_for_pay_ticker(update)
        return ASK_PAY_TICKER

async def ask_for_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    amount = update.message.text
    logger.debug("User response received for amount: %s", amount)
    if amount.replace('.', '', 1).isdigit():  # Check if the input is a valid number
        logger.debug("Valid amount received: %s", amount)
        token_data = context.user_data['token_data']  # Retrieve token data
        user_data = get_user_data(update)
        await process_payment(update, context, token_data, amount, user_data)
        return ConversationHandler.END
    else:
        logger.warning("Invalid amount provided by user.")
        await update.message.reply_text("Please provide a valid amount.")
        return ASK_AMOUNT

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Conversation canceled.")
    context.user_data.clear()  # Clear user data context
    return ConversationHandler.END

async def process_payment(update: Update, context: ContextTypes.DEFAULT_TYPE, token_data: dict, amount: str, user_data) -> None:
    logger.debug("Processing token data: %s", token_data)
    telegram_username = update.effective_user.username

    logger.info("Token data found for ticker: %s", token_data['symbol'])
    welcome_text = (
        f"📢 *PAY {amount} {token_data['symbol']} to {telegram_username}*\\!\n\n"
        f"🔗 *Chain ID*\n {token_data['chainId']}\n\n"
        f"🏷️ *Token Address*\n {token_data['tokenAddress']}\n\n"
    )

    try:
        cryptoAmount = int(float(amount) * (10 ** int(token_data.get('decimals', 0))))

        payment_link = create_pay_link(user_data, token_data['chainId'], token_data['tokenAddress'], cryptoAmount, "")
        if payment_link:
            logger.debug("Payment link created successfully for ticker: %s", token_data['symbol'])
            keyboard = [
                [InlineKeyboardButton(f"Pay {amount} {token_data['symbol']}", web_app=WebAppInfo(url=payment_link))]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_photo(photo=WELCOME_IMAGE_URL, caption=welcome_text, reply_markup=reply_markup, parse_mode='MarkdownV2')
        else:
            logger.error("Failed to create payment link for ticker: %s", token_data['symbol'])
            await update.message.reply_text("Payment link couldn't be created.")
        context.user_data.clear()  # Clear the user data context
    except Exception as e:
        logger.exception("An error occurred while processing the payment link: %s", str(e))
        await update.message.reply_text(f"An error occurred: {str(e)}")
        context.user_data.clear()  # Clear the user data context

# Define the conversation handler
payment_handler = ConversationHandler(
    entry_points=[CommandHandler('receive', pay)],
    states={
        ASK_PAY_TICKER: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, ask_for_ticker),
            CallbackQueryHandler(pay_button_handler)
        ],
        ASK_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_for_amount)],
    },
    fallbacks=[CommandHandler('cancel', cancel)]
)

import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, WebAppInfo
from telegram.ext import (
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
    Application,
    ContextTypes,
)
from createPaymentLink import create_pay_link
from config import WELCOME_IMAGE_URL
from utils.getToken import get_token
from utils.createJWT import get_user_data

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Define conversation states
ASK_TICKER, ASK_AMOUNT = range(2)

# Dummy implementation of `is_decimal` function for example purposes
def is_decimal(value: str) -> bool:
    try:
        float(value)
        return True
    except ValueError:
        return False

# Function to handle the /pay command
async def pay(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.debug("Received command /pay with arguments: %s", context.args)
    if context.args and len(context.args) == 1 and context.args[0].isalpha():
        ticker = context.args[0]
        token_data = get_token(ticker, "pay")
        logger.debug("Ticker provided via command: %s", token_data)
        context.user_data['ticker'] = ticker  # Store the ticker
        await update.message.reply_text("Please enter amount.")
        return ASK_AMOUNT
    else:
        logger.warning("Invalid ticker provided or no ticker in command.")
        await update.message.reply_text("Please enter one of the tokens you'd like get paid in:\n\n- USDC")
        return ASK_TICKER

async def ask_for_ticker(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    ticker = update.message.text
    token_data = get_token(ticker, "pay")
    if token_data['tokenAddress']:
        logger.debug("User response received for ticker: %s", token_data)
        context.user_data['ticker'] = ticker  # Store the ticker
        await update.message.reply_text("Please enter amount.")
        return ASK_AMOUNT
    else:
        logger.warning("Invalid ticker provided by user.")
        await update.message.reply_text("Please provide a valid ticker.")
        return ASK_TICKER

async def ask_for_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    amount = update.message.text
    logger.debug("User response received for amount: %s", amount)
    if float(amount):
        logger.debug("Valid amount received: %s", amount)
        ticker = context.user_data['ticker']
        user_data = get_user_data(update)
        await process_payment(update, context, ticker, amount, user_data)
        return ConversationHandler.END
    else:
        logger.warning("Invalid amount provided by user.")
        await update.message.reply_text("Please provide a valid amount.")
        return ASK_AMOUNT

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Conversation canceled.")
    return ConversationHandler.END

async def process_payment(update: Update, context: ContextTypes.DEFAULT_TYPE, token_ticker: str, amount: float, user_data) -> None:
    logger.debug("Processing token ticker: %s", token_ticker)
    token_data = get_token(token_ticker, "pay")
    if not token_data:
        logger.warning("Token data not found for ticker: %s", token_ticker)
        keyboard = [
            [
                InlineKeyboardButton("Request Listing", url="https://t.me/acmeonetap"),
                InlineKeyboardButton("Trade Another Ticker", callback_data='trade_another')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "🚫 This token is not listed. To request a listing or trade another ticker, please choose:",
            reply_markup=reply_markup
        )
        context.user_data.pop('ticker', None)  # Remove 'ticker' from user data
        return

    logger.info("Token data found for ticker: %s", token_ticker)
    welcome_text = (
        f"📢 *PAY {token_ticker}*\\!\n\n"
        f"🔗 *Chain ID*\n {token_data['chainId']}\n\n"
        f"🏷️ *Token Address*\n {token_data['tokenAddress']}\n\n"
    )

    try:
        cryptoAmount = int(amount) * (10 ** int(token_data.get('decimals')))
        
        payment_link = create_pay_link(user_data, token_data['chainId'], token_data['tokenAddress'], cryptoAmount, "")
        if payment_link:
            logger.debug("Payment link created successfully for ticker: %s", token_ticker)
            keyboard = [
                [InlineKeyboardButton(f"Pay me {amount} {token_ticker}", web_app=WebAppInfo(url=payment_link))]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_photo(photo=WELCOME_IMAGE_URL, caption=welcome_text, reply_markup=reply_markup, parse_mode='MarkdownV2')
        else:
            logger.error("Failed to create payment link for ticker: %s", token_ticker)
            await update.message.reply_text("Payment link couldn't be created.")
    except Exception as e:
        logger.exception("An error occurred while processing the payment link: %s", str(e))
        await update.message.reply_text(f"An error occurred: {str(e)}")

# Define the conversation handler
payment_handler = ConversationHandler(
    entry_points=[CommandHandler('pay', pay)],
    states={
        ASK_TICKER: [MessageHandler(filters.TEXT, ask_for_ticker)],
        ASK_AMOUNT: [MessageHandler(filters.TEXT, ask_for_amount)],
    },
    fallbacks=[CommandHandler('cancel', cancel)]
)
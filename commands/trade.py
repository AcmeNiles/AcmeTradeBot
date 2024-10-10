import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ConversationHandler, CallbackContext

from utils.createJWT import get_user_data  # Import user data extraction function
from createMintingLink import create_minting_link  # Import create_minting_link function
from createTradingLink import create_trading_link  # Import create_trading_link function
from config import WELCOME_IMAGE_URL
from utils.checkTicker import check_ticker  # Import the function to get token data
from utils.membership import member_link  # Import membership check function
from config import CHAT_GROUP

# Setup logging
logging.basicConfig(level=logging.DEBUG)  # Set logging level to DEBUG
logger = logging.getLogger(__name__)  # Create a logger instance

# Define conversation states
START_TRADE, ASK_TICKER = range(2)

# Function to handle the /start command
async def start(update: Update, context: CallbackContext) -> int:
    token_symbol = context.args[0] if context.args else None

    welcome_text = (
        "👋 *Welcome to Acme\!*\n\n"
        "💳 *Tap\. Trade\. Done\.\n*Easily buy any token with your bank card\.\n\n"
        "🤑 *Share to Earn\n*Share trading links and earn 50% of our fees\.\n\n"
        "🔒 *Own your Tokens\n*You always control your tokens\. Acme never touches them\.\n\n"
    )

    if token_symbol:
        welcome_text += (
            f"*Here to create a trading link for {token_symbol}?* Mint a free access pass to start making some money \! 💸 "
        )
    else:
        welcome_text += "*/trade now and start making some money\! 💸*"

    user_data = get_user_data(update)

    try:
        minting_link = create_minting_link(user_data)
        membership_link = await member_link(update.effective_user.id, CHAT_GROUP, context)

        if minting_link:
            keyboard = [
                [
                    InlineKeyboardButton("Claim Your Access Pass", web_app=WebAppInfo(url=minting_link)),
                ],
                [
                    InlineKeyboardButton("Trade Now", callback_data='start_trade'),
                ],
                [
                    InlineKeyboardButton("Open Vault", web_app=WebAppInfo(url='https://app.acme.am/vault')),
                    InlineKeyboardButton("Go to Acme Group", url=membership_link),
                ],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_photo(photo=WELCOME_IMAGE_URL, caption=welcome_text, reply_markup=reply_markup, parse_mode='MarkdownV2')

            return START_TRADE  # Ensure a valid state is returned here
        else:
            await reply(update, "Minting successful, but no minting link was returned.")
            return ConversationHandler.END
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        await reply(update, f"An error occurred: {str(e)}")
        return ConversationHandler.END

# Helper function to handle replies
async def reply(update: Update, text: str):
    if update.message:
        await update.message.reply_text(text)
    elif update.callback_query:
        await update.callback_query.message.reply_text(text)

# Fallback to handle unexpected user input or cancel
async def cancel(update: Update, context: CallbackContext) -> int:
    await reply(update, "Conversation cancelled. You can start again by typing /start.")
    return ConversationHandler.END

# Function to handle the /trade command
async def trade(update: Update, context: CallbackContext) -> int:

    query = update.callback_query  # Get the callback query

    if query:
        await query.answer()  # Acknowledge the button press
        
    if context.args and len(context.args) == 1 and context.args[0].isalpha():
        ticker = context.args[0].upper()
        token_data = await check_ticker(ticker, update, "trade")
        if token_data:
            logger.debug("Ticker provided via command: %s", ticker)
            await process_token_ticker(update, context, ticker, token_data)
            return ConversationHandler.END
        else:
            logger.warning("Invalid ticker provided or no ticker in command.")

    await prompt_for_trade_ticker(update)
    return ASK_TICKER  # Move to the asking state

# Helper function to handle replies
async def reply(update: Update, text: str, reply_markup=None):
    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.message.reply_text(text, reply_markup=reply_markup)

async def prompt_for_trade_ticker(update: Update):
    keyboard = [
        [InlineKeyboardButton("PONKE", callback_data='PONKE')],
        [InlineKeyboardButton("BRETT", callback_data='BRETT')],
        [InlineKeyboardButton("Cancel", callback_data='cancel')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await reply(update, "Please select one of the tokens you'd like to trade or cancel:", reply_markup)


async def ask_for_ticker(update: Update, context: CallbackContext):
    ticker = update.message.text.upper()
    logger.debug("User response received for ticker: %s", ticker)

    token_data = await check_ticker(ticker, update, "trade")
    if token_data:
        logger.debug("Valid ticker received: %s", ticker)
        await process_token_ticker(update, context, ticker, token_data)
        return ConversationHandler.END
    else:
        logger.warning("Invalid ticker format provided by user.")
        await prompt_for_trade_ticker(update)  # Update the prompt function name here
        return ASK_TICKER  # Prompt the user again for a valid input

async def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    if query.data == 'cancel':
        await cancel(update, context)
        return ConversationHandler.END

    ticker = query.data
    token_data = await check_ticker(ticker, query, "trade")
    if token_data:
        logger.debug("Valid ticker received via button:")
        await process_token_ticker(update, context, ticker, token_data)
        return ConversationHandler.END
    else:
        logger.warning("Invalid ticker format provided by button.")
        await prompt_for_trade_ticker(query)  # Update the prompt function name here
        return ASK_TICKER  # Prompt the user again for a valid input

async def process_token_ticker(update: Update, context: CallbackContext, ticker: str, token_data) -> None:
    logger.debug("Processing token ticker: %s", ticker)
    user_data = get_user_data(update)
    welcome_text = (f"📢 *Buy {token_data['symbol']}*\\!\n\n"
                    f"🔗 *Chain ID*\n {token_data['chainId']}\n\n"
                    f"🏷️ *Token Address*\n {token_data['tokenAddress']}\n\n")

    try:
        trading_link = create_trading_link(user_data, token_data['chainId'], token_data['tokenAddress'], "")

        if trading_link:
            logger.debug("Trading link created successfully for ticker: %s", ticker)

            keyboard = [[
                InlineKeyboardButton(
                    f"Trade {ticker}",
                    web_app=WebAppInfo(url=trading_link)
                )
            ]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await reply_photo(update, welcome_text, reply_markup)
        else:
            logger.error("Failed to create trading link for ticker: %s", ticker)
            await reply(update, "Trading link couldn't be created.")
        context.user_data.clear()  # Clear the user data context
    except Exception as e:
        logger.exception("An error occurred while processing the trading link: %s", str(e))
        await reply(update, f"An error occurred: {str(e)}")
        context.user_data.clear()  # Clear the user data context

# Helper function to send a photo reply
async def reply_photo(update: Update, welcome_text: str, reply_markup: InlineKeyboardMarkup):
    if update.message:
        await update.message.reply_photo(photo=WELCOME_IMAGE_URL, caption=welcome_text, reply_markup=reply_markup, parse_mode='MarkdownV2')
    elif update.callback_query:
        await update.callback_query.message.reply_photo(photo=WELCOME_IMAGE_URL, caption=welcome_text, reply_markup=reply_markup, parse_mode='MarkdownV2')

# Define the conversation handler
trade_handler = ConversationHandler(
    entry_points=[
        CommandHandler('trade', trade),
        CommandHandler("start", start),
        MessageHandler(filters.TEXT & ~filters.COMMAND, start),
    ],
    states={
        START_TRADE: [
            CallbackQueryHandler(trade, pattern='start_trade')  # Handles "Trade Now" button
        ],
        ASK_TICKER: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, ask_for_ticker),
            CallbackQueryHandler(button_handler)
        ],
    },
    fallbacks=[CommandHandler('cancel', cancel)]  # Add fallback
)

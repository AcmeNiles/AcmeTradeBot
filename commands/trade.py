import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ConversationHandler, CallbackContext

from utils.createJWT import get_user_data  # Import user data extraction function
from createTradingLink import create_trading_link  # Import create_trading_link function
from config import WELCOME_IMAGE_URL
from utils.getToken import get_token  # Import the function to get token data

# Setup logging
logging.basicConfig(level=logging.DEBUG)  # Set logging level to DEBUG
logger = logging.getLogger(__name__)  # Create a logger instance

# Define conversation states
ASK_TICKER = 0


# Function to handle the /trade command
async def trade(update: Update, context: CallbackContext) -> int:
    # Step 1: Check for ticker in command arguments
    logger.debug("Received command /trade with arguments: %s", context.args)

    if context.args and len(context.args) == 1 and context.args[0].isalpha():
        ticker = context.args[0]
        logger.debug("Ticker provided via command: %s", ticker)

        user_data = get_user_data(update)
        await process_token_ticker(update, context, ticker,
                                   user_data)  # Call with provided ticker
        return ConversationHandler.END  # End the conversation after processing

    else:
        logger.warning("Invalid ticker provided or no ticker in command.")
        await update.message.reply_text(
            "Please enter one of the tokens you'd like to trade:\n\n- PONKE\n- BRETT")
        return ASK_TICKER  # Move to the asking state


async def ask_for_ticker(update: Update, context: CallbackContext):

    ticker = update.message.text
    logger.debug("User response received for ticker: %s", ticker)
    context.user_data["ticker"] = ticker

    # Check if the response is valid
    if ticker.isalpha():
        logger.debug("Valid ticker received: %s", ticker)

        user_data = get_user_data(update)
        await process_token_ticker(update, context, ticker,
                                   user_data)  # Call with user-provided ticker
        return ConversationHandler.END  # End the conversation after processing
    else:
        logger.warning("Invalid ticker format provided by user.")
        await update.message.reply_text(
            "Please provide a valid token (one word only).")
        return ASK_TICKER  # Prompt the user again for a valid input


async def cancel(update: Update, context: CallbackContext):
    await update.message.reply_text("Conversation canceled.")
    return ConversationHandler.END


# Function to process the token ticker
async def process_token_ticker(update: Update, context: CallbackContext,
                               token_ticker: str, user_data) -> None:
    logger.debug("Processing token ticker: %s", token_ticker)

    # Fetch token data from the utility function
    token_data = get_token(token_ticker, "trade")

    # Check if the token data was found
    if not token_data:
        logger.warning("Token data not found for ticker: %s", token_ticker)

        # Create buttons that redirect to the @acmeonetap group and trigger a new trade
        keyboard = [[
            InlineKeyboardButton(
                "Request Listing",
                url="https://t.me/acmeonetap"  # Link to the Telegram group
            ),
            InlineKeyboardButton(
                "Trade Another Ticker",
                callback_data=
                'trade_another'  # Callback to trigger a new command
            )
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "🚫 This token is not listed. To request a listing or trade another ticker, please choose:",
            reply_markup=reply_markup)
        # Clear the ticker from user data after handling the response
        context.user_data.pop('token_ticker',
                              None)  # Remove 'token_ticker' from user data
        return  # Exit the command

    logger.info("Token data found for ticker: %s", token_ticker)
    welcome_text = (f"📢 *Buy {token_ticker}*\\!\n\n"
                    f"🔗 *Chain ID*\n {token_data['chainId']}\n\n"
                    f"🏷️ *Token Address*\n {token_data['tokenAddress']}\n\n")

    try:
        # Create the trading link
        trading_link = create_trading_link(user_data, token_data['chainId'],
                                           token_data['tokenAddress'], "")

        if trading_link:
            logger.debug("Trading link created successfully for ticker: %s",
                         token_ticker)

            # Create an inline keyboard button with the WebAppInfo (to open in Telegram as a web app)
            keyboard = [[
                InlineKeyboardButton(
                    f"Trade {token_ticker}",
                    web_app=WebAppInfo(
                        url=trading_link)  # Open as a Web App inside Telegram
                )
            ]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            # Send the welcome text as the caption of the image
            await update.message.reply_photo(photo=WELCOME_IMAGE_URL,
                                             caption=welcome_text,
                                             reply_markup=reply_markup,
                                             parse_mode='MarkdownV2')
        else:
            logger.error("Failed to create trading link for ticker: %s",
                         token_ticker)
            await update.message.reply_text("Trading link couldn't be created."
                                            )
    except Exception as e:
        logger.exception(
            "An error occurred while processing the trading link: %s", str(e))
        await update.message.reply_text(f"An error occurred: {str(e)}")

# Define the conversation handler
trade_handler = ConversationHandler(
    entry_points=[
        CommandHandler('trade', trade),
        CallbackQueryHandler(trade, pattern='^trade$')
    ],
    states={
        ASK_TICKER: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_for_ticker)],
    },
    fallbacks=[CommandHandler('cancel', cancel)]  # Add fallback
)
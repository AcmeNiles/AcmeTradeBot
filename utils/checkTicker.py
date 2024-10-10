import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from utils.getToken import get_token  # Import the function to get token data

logger = logging.getLogger(__name__)


async def check_ticker(token_ticker, update, type: str):
  # Fetch token data from the utility function
  token_data = get_token(token_ticker, type)
  logger.warning("TOKENDATA: %s", token_data)

  # Check if the token data was found
  if "error" in token_data:
      logger.warning("Ticker not found: %s", token_ticker)
      # Create buttons that redirect to the @acmeonetap group and trigger a new trade
      keyboard = [[
          InlineKeyboardButton(
              "Request Listing",
              url="https://t.me/acmeonetap"  # Link to the Telegram group
          )
      ]]
      reply_markup = InlineKeyboardMarkup(keyboard)

      await update.message.reply_text(
          "🚫 This token is not listed. To request a listing, please contact us:",
          reply_markup=reply_markup)

      return None
  else:
      return token_data
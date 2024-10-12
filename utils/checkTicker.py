from config import logger
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from utils.getToken import get_token  # Import the function to get token data
from utils.reply import reply  # Import the reply function

logger = logging.getLogger(__name__)

async def check_ticker(token_ticker: str, update: Update, intent_type: str):
    # Check if the token ticker is not blank
    if not token_ticker or token_ticker.strip() == "":
        logger.debug("Ticker is blank.")
        return None  # Return None if the ticker is blank

    # Fetch token data from the utility function
    token_data = get_token(token_ticker, intent_type)
    logger.debug("TOKENDATA: %s", token_data)

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

        await reply(update, 
            "🚫 This token is not listed. To request a listing, please contact us:", 
            reply_markup=reply_markup
        )

        return None
    else:
        return token_data


def get_token(ticker: str, type: str):
  # Mapping of tickers to chainId and token_address for trading
  TRADE_TOKENS = {
      "BRETT": {"chainId": "8453", "symbol":"BRETT", "tokenAddress": "0x532f27101965dd16442e59d40670faf5ebb142e4"},
      "PONKE": {"chainId": "solana", "symbol":"PONKE", "tokenAddress": "5z3EqYQo9HiCEs3R84RCDMu2n7anpDMxRhdK8PSWmrRC"},
      # Add more trade tokens as needed
  }

  # Mapping of tickers to chainId and token_address for payments
  PAY_TOKENS = {
      "USDC": {"chainId": "42161", "symbol":"USDC", "tokenAddress": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831", "decimals":6},
      # Add more pay tokens as needed
  }
  logger.warning("THIS WAS TICKER AND TYPE: %s %s", ticker,type)

  """Retrieve token data from the appropriate mapping based on type."""
  if type == "trade":
      token_data = TRADE_TOKENS.get(ticker.upper())
  elif type == "pay":
      token_data = PAY_TOKENS.get(ticker.upper())
  else:
      return {"error": "Invalid type. Must be 'trade' or 'pay'."}

  if token_data:
      return token_data
  else:
      return {"error": "Ticker not found."}
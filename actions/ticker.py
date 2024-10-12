import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext
#from config import ASK_PAY_TICKER, TRADE_CARD, ASK_AMOUNT

logger = logging.getLogger(__name__)

async def ask_ticker(update: Update, context: CallbackContext, intent: str = "trade") -> int:
    logger.debug(f"Entering ask_ticker function with intent: {intent}")

    context.user_data['intent'] = intent  # Store the intent in the user data

    try:
        # Set state based on the intent
        if intent == "trade":
            context.user_data['state'] = ASK_TRADE_TICKER  # Set state for trade
            ask_ticker_message = "Please select or type one of the tokens you'd like to trade:"
            buttons = [
                [InlineKeyboardButton("PONKE", callback_data='PONKE')],
                [InlineKeyboardButton("BRETT", callback_data='BRETT')],
                [InlineKeyboardButton("Menu", callback_data='MENU')],
            ]
            next_state = TRADE_CARD  # Transition to TRADE_CARD after ticker selection

        elif intent == "pay":
            context.user_data['state'] = ASK_PAY_TICKER  # Set state for pay
            ask_ticker_message = "Please select or type one of the tokens you'd like to get paid in:"
            buttons = [
                [InlineKeyboardButton("USDC", callback_data='USDC')],
                [InlineKeyboardButton("Cancel", callback_data='cancel')],
                [InlineKeyboardButton("Menu", callback_data='MENU')],
            ]
            next_state = ASK_AMOUNT  # Transition to ASK_AMOUNT after ticker selection

        # Create the reply markup
        reply_markup = InlineKeyboardMarkup(buttons)
        logger.debug(f"Prompting user for ticker selection with intent: {intent}")

        if update.message:
            await update.message.reply_text(ask_ticker_message, reply_markup=reply_markup)
        elif update.callback_query and update.callback_query.message:
            await update.callback_query.message.reply_text(ask_ticker_message, reply_markup=reply_markup)
        else:
            logger.warning("No valid message or callback query to reply to.")
            await reply(update, "No valid message or callback to reply to.")

        logger.debug(f"User prompted for ticker. Awaiting response. Next state: {next_state}")

        # Check for callback queries to handle ticker selection
        if update.callback_query:
            ticker = update.callback_query.data.upper()
            await update.callback_query.answer()  # Acknowledge the callback query

            # Directly handle PONKE
            if ticker == 'PONKE':
                return await trade_card(update, context, ticker)  # Go directly to trade_card with PONKE

            # Check if a valid ticker is selected
            if ticker in ['BRETT', 'USDC']:
                return await trade_card(update, context, ticker)  # Proceed to trade card

        return next_state  # Return the next state based on intent

    except Exception as e:
        logger.error(f"Error in ask_ticker ({intent}): {e}")
        await update.message.reply_text("An error occurred. Please try again.")

        # On error, take the user back to the previous state
        context.user_data['state'] = ASK_TRADE_TICKER if intent == "trade" else ASK_PAY_TICKER
        return context.user_data['state']  # Retry ticker input for the respective flow

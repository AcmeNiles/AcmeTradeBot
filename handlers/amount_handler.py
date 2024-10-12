from config import logger
from telegram import Update
from telegram.ext import ContextTypes

# Parse and validate the amount
def parse_amount(amount_text: str) -> float:
    """
    Parse and validate the amount from user input.
    """
    try:
        amount = float(amount_text.strip())
        return amount
    except ValueError:
        return None

# Handler for collecting amount
async def handle_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handles the user's amount input and proceeds to execute the action.
    """
    amount_text = update.message.text
    amount = parse_amount(amount_text)

    if amount is not None:  # Valid amount input
        context.user_data['amount'] = amount
        logger.info(f"Amount received: {amount}")

        # Check if recipient is already provided
        if 'recipient' in context.user_data:
            return await execute_action(update, context)  # Proceed to execute action
        else:
            await update.message.reply_text("Please provide the recipient address:")
            return SELECT_RECIPIENT  # Prompt for recipient
    else:
        logger.debug("Invalid amount entered.")
        await update.message.reply_text("Please enter a valid amount:")
        return SELECT_AMOUNT  # Prompt for amount
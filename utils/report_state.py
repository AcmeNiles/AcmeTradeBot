from telegram import Update
from telegram.ext import CallbackContext

async def report_state(update: Update, context: CallbackContext, function:str) -> None:
  current_state = context.user_data.get('state', 'Unknown')
  await update.message.reply_text(f"Your {function} state is: {current_state}")

# handlers/start_handler.py

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import CallbackContext
from utils.createJWT import get_user_data
from utils.minting import create_minting_link
from config import WELCOME_IMAGE_URL, CHAT_GROUP

# Setup logging
logger = logging.getLogger(__name__)

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

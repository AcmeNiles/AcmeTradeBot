import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, InputFile
from telegram.ext import ConversationHandler, ContextTypes

# Import constants
from config import ACME_GROUP, MENU_PHOTO

# Setup logging
logger = logging.getLogger(__name__)

# Process Menu Function
async def process_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, url=None, is_authenticated=False):
    """
    Displays the main menu to authenticated users, or shows minting link to unauthenticated users.
    If the URL is provided, it overrides the menu with a specific action (e.g., minting link).
    """
    logger.info("Displaying the main menu.")

    # Common menu message
    menu_message = (
        "👋 *Welcome to Acme\!* \n\n"
        "💳 *Tap\. Trade\. Done\.*\n"
        "Easily buy any token with your bank card\.\n\n"
        "🤑 *Share to Earn*\n"
        "Share trading links and earn 50\% fees \+ airdrops\.\n\n"
        "🔒 *Own your Tokens*\n"
        "Tokens are secured in a safe\. Only you have the keys\.\n\n"
    )

    # If authenticated, show the regular menu and extra message
    group_name = ACME_GROUP  # Set the group name to get the invite link
    invite_link = await get_invite_link(update.effective_user.id, group_name, context)

    try:
        if not is_authenticated:
            # If user is not authenticated, show the minting link and extra message
            minting_link = url or "https://example.com/mint"  # Replace with actual minting link
            menu_message += "Get your access pass and start making some money\! 💸 \n"

            # Web App Button for "Claim Your Access Pass"
            buttons = [
                [InlineKeyboardButton("Claim Your Access Pass", web_app=WebAppInfo(url=minting_link))],
                [InlineKeyboardButton("Say Hi! 👋", url=invite_link)],
            ]

            # Using MENU_PHOTO for the photo
            await update.message.reply_photo(photo=MENU_PHOTO, caption=menu_message, parse_mode="MarkdownV2", reply_markup=InlineKeyboardMarkup(buttons))
        else:
            menu_message += "Let's start making some money\! 💸 \n"

            buttons = [
                [
                    InlineKeyboardButton("📈 Trade Now", callback_data='/trade'),
                    InlineKeyboardButton("🤑 Share to Earn", callback_data='/share')
                ],
                [
                    InlineKeyboardButton("⬆️ Pay", callback_data='/pay'),
                    InlineKeyboardButton("⬇️ Request", callback_data='/request')
                ],
                [InlineKeyboardButton("👋 Say Hi!", url=invite_link)]
            ]

            # Using MENU_PHOTO for the photo in authenticated case as well
            await update.message.reply_photo(photo=MENU_PHOTO, caption=menu_message, parse_mode="MarkdownV2", reply_markup=InlineKeyboardMarkup(buttons))

    except Exception as e:
        logger.error("Failed to send card: %s", str(e))
        await update.message.reply_text("An error occurred while trying to send the card. Please try again later.")


# Updated get_invite_link function
async def get_invite_link(user_id: int, chat_id: str, context: ContextTypes.DEFAULT_TYPE) -> str:
    try:
        member_status = await context.bot.get_chat_member(chat_id, user_id)

        # If the user is a member, return the group link
        if member_status.status in ['member', 'administrator', 'creator']:
            group_link = f"https://t.me/{chat_id.lstrip('@')}"
            return group_link

        # Otherwise, generate and return an invite link
        else:
            group_invite_link = await context.bot.exportChatInviteLink(chat_id)
            return group_invite_link

    except Exception as e:
        logger.error("Failed to check membership or generate invite link: %s", str(e))

        # Return a fallback invite link or empty string to handle the error gracefully
        return "https://t.me/joinchat/fallbackInviteLink"

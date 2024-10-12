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
    logger.info("Entered process_menu function")
    logger.debug(f"Parameters: url={url}, is_authenticated={is_authenticated}")

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

    group_name = ACME_GROUP
    logger.debug(f"Group name set to: {group_name}")

    try:
        invite_link = await get_invite_link(update.effective_user.id, group_name, context)
        logger.info(f"Generated invite link: {invite_link}")
    except Exception as e:
        logger.error(f"Failed to get invite link: {str(e)}")
        await update.message.reply_text("An error occurred while generating the invite link.")
        return

    try:
        if not is_authenticated:
            logger.info("User is not authenticated, showing minting link")

            # If the user is not authenticated, show the minting link and extra message
            minting_link = url or "https://example.com/mint"
            logger.debug(f"Using minting link: {minting_link}")

            menu_message += "Get your access pass and start making some money\! 💸 \n"

            # Web App Button for "Claim Your Access Pass"
            buttons = [
                [InlineKeyboardButton("Claim Your Access Pass", web_app=WebAppInfo(url=minting_link))],
                [InlineKeyboardButton("Say Hi! 👋", url=invite_link)],
            ]
            logger.debug(f"Buttons prepared for unauthenticated user: {buttons}")

            # Send menu with the minting link
            await update.message.reply_photo(photo=MENU_PHOTO, caption=menu_message, parse_mode="MarkdownV2", reply_markup=InlineKeyboardMarkup(buttons))
            logger.info("Menu sent to unauthenticated user")

        else:
            logger.info("User is authenticated, showing the main menu")

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
            logger.debug(f"Buttons prepared for authenticated user: {buttons}")

            # Send authenticated menu
            await update.message.reply_photo(photo=MENU_PHOTO, caption=menu_message, parse_mode="MarkdownV2", reply_markup=InlineKeyboardMarkup(buttons))
            logger.info("Menu sent to authenticated user")

    except Exception as e:
        logger.error(f"Failed to send menu: {str(e)}")
        await update.message.reply_text("An error occurred while trying to send the menu. Please try again later.")


# Updated get_invite_link function
async def get_invite_link(user_id: int, chat_id: str, context: ContextTypes.DEFAULT_TYPE) -> str:
    """
    Fetches or generates an invite link for the user to the specified chat/group.
    """
    logger.info(f"Entered get_invite_link function for user {user_id} in chat {chat_id}")

    try:
        member_status = await context.bot.get_chat_member(chat_id, user_id)
        logger.debug(f"User membership status: {member_status.status}")

        # If the user is a member, return the group link
        if member_status.status in ['member', 'administrator', 'creator']:
            group_link = f"https://t.me/{chat_id.lstrip('@')}"
            logger.info(f"User is a member, returning group link: {group_link}")
            return group_link
        else:
            # Otherwise, generate and return an invite link
            group_invite_link = await context.bot.exportChatInviteLink(chat_id)
            logger.info(f"Generated new invite link: {group_invite_link}")
            return group_invite_link

    except Exception as e:
        logger.error(f"Failed to check membership or generate invite link: {str(e)}")

        # Return a fallback invite link to handle the error gracefully
        fallback_link = "https://t.me/joinchat/fallbackInviteLink"
        logger.warning(f"Returning fallback invite link: {fallback_link}")
        return fallback_link

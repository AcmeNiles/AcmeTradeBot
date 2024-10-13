from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ConversationHandler, ContextTypes
from config import logger, ACME_GROUP
from messages_photos import PHOTO_MENU, MESSAGE_MENU, MESSAGE_LOGIN, MESSAGE_LOGGED_IN

# Process Menu Function
async def process_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, auth_result=None):
    logger.info("Entered process_menu function")
    logger.debug(f"Authentication result: {auth_result}")
    logger.debug(f"Update object: {update}")

    try:
        # Generate invite link
        invite_link = await get_invite_link(update.effective_user.id, ACME_GROUP, context)
        logger.info(f"Generated invite link: {invite_link}")
    except Exception as e:
        logger.error(f"Failed to generate invite link: {str(e)}")
        await update.message.reply_text("An error occurred while generating the invite link.")
        return

    try:
        # Local copies of message and photo
        local_message_menu = MESSAGE_MENU if MESSAGE_MENU else None
        local_photo_menu = PHOTO_MENU if PHOTO_MENU else None

        if not local_message_menu:
            logger.error("MESSAGE_MENU is missing or None.")
            raise ValueError("MESSAGE_MENU is not available.")

        if not local_photo_menu:
            logger.error("PHOTO_MENU is missing or None.")
            raise ValueError("PHOTO_MENU is not available.")

        logger.debug(f"Loaded local_message_menu: {local_message_menu}")
        logger.debug(f"Loaded local_photo_menu: {local_photo_menu}")

        # Handle unauthenticated user
        if 'url' in auth_result:
            logger.info("User is not authenticated, showing minting link")

            minting_link = auth_result.get('url', "https://bit.ly/iamcoyote")
            logger.debug(f"Using minting link: {minting_link}")

            local_message_menu += MESSAGE_LOGIN
            logger.debug(f"Updated local_message_menu for unauthenticated user: {local_message_menu}")

            # Buttons for unauthenticated users
            buttons = [
                [InlineKeyboardButton("👑 Claim Early Access Pass", web_app=WebAppInfo(url=minting_link))],
                [InlineKeyboardButton("📈 Trade Now", callback_data='/trade')],
                [InlineKeyboardButton("👋 Say Hi!", url=invite_link)],
            ]
            
            logger.debug(f"Buttons for unauthenticated user: {buttons}")
            # Log all information before sending
            logger.debug(f"Preparing to send trading card with the following details:\n"
                         f"Photo: {local_photo_menu}\n"  # Change made here
                         f"Caption: {local_message_menu}\n"
                         f"Buttons: {buttons}")

            # Send the menu with the minting link and photo
            try:
                await update.message.reply_photo(
                    photo=local_photo_menu,
                    caption=local_message_menu,
                    parse_mode="MarkdownV2",
                    reply_markup=InlineKeyboardMarkup(buttons)
                )
                logger.info("Menu sent to unauthenticated user successfully")
            except Exception as e:
                logger.error(f"Failed to send unauthenticated user menu photo: {str(e)}")
                await update.message.reply_text("An error occurred while sending the menu photo.")

        # Handle authenticated user
        elif 'id' in auth_result:
            logger.info("User is authenticated, showing main menu")

            local_message_menu += MESSAGE_LOGGED_IN
            logger.debug(f"Updated local_message_menu for authenticated user: {local_message_menu}")

            # Buttons for authenticated users
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
            logger.debug(f"Buttons for authenticated user: {buttons}")

            # Send the authenticated menu with the photo
            try:
                await update.message.reply_photo(
                    photo=local_photo_menu,
                    caption=local_message_menu,
                    parse_mode="MarkdownV2",
                    reply_markup=InlineKeyboardMarkup(buttons)
                )
                logger.info("Menu sent to authenticated user successfully")
            except Exception as e:
                logger.error(f"Failed to send authenticated user menu photo: {str(e)}")
                await update.message.reply_text("An error occurred while sending the menu photo.")

    except ValueError as ve:
        logger.error(f"ValueError: {str(ve)}")
        await update.message.reply_text(f"An error occurred: {str(ve)}")

    except Exception as e:
        logger.error(f"Failed to process menu: {str(e)}")
        await update.message.reply_text("An error occurred while processing the menu. Please try again later.")


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
        fallback_link = "https://t.me/joinchat/fallbackInviteLink"
        logger.warning(f"Returning fallback invite link: {fallback_link}")
        return fallback_link

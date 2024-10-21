from config import logger
from telegram.ext import ContextTypes

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

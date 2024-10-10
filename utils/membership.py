import logging
from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

async def member_link(user_id: int, chat_id: str, context: ContextTypes.DEFAULT_TYPE) -> str:
    try:
        member_status = await context.bot.get_chat_member(chat_id, user_id)

        if member_status.status in ['member', 'administrator', 'creator']:
            group_link = f"https://t.me/{chat_id.lstrip('@')}"
            return group_link
        else:
            group_invite_link = await context.bot.exportChatInviteLink(chat_id)
            return group_invite_link

    except Exception as e:
        logger.error("Failed to check membership or generate invite link: %s", str(e))
        return "An error occurred while checking your membership status."

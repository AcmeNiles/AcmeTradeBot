from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ConversationHandler, ContextTypes
from config import logger, ACME_GROUP, ACME_APP_URL, PHOTO_COYOTE_MIC, FEATURES, BOT_USERNAME
from utils.membership import get_invite_link
from utils.reply import send_animation, send_photo, clear_cache
from handlers.auth_handler import get_auth_result
from messages_photos import markdown_v2

# Define common menu messages with unescaped characters
LOGGED_OUT = "\n *👋 Start Your Exchange. Today.* \n\n"
LOGGED_IN = "*🚀 [{username_display} Exchange](https://t.me/{bot_username}?start) 🚀*\n\n"


MENU = (
    "💳 *Tap.* *Trade.* *Done*.\n"
    "Buy any token with your bank card.\n_Earn 30% fees + XP_.\n\n"
    "🤑 *Help Others Buy*\n"
    "List & share tokens you love.\n_Earn 50% fees + XP._\n\n"
    "🔐 *Own Your Tokens*\n"
    "Stored in Safes securing $100B+.\n_Only you have the keys._\n\n\n"
    "💸 Let’s make some money!"
)

async def process_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("Entered process_menu function")
    auth_result = await get_auth_result(update, context) or None

    try:
        # Check if the invite link already exists in context
        if 'invite_link' not in context.user_data:
            # Generate invite link
            invite_link = await get_invite_link(update.effective_user.id, ACME_GROUP, context)
            context.user_data['invite_link'] = invite_link
            logger.info(f"Generated invite link: {invite_link}")
        else:
            invite_link = context.user_data['invite_link']
            logger.info(f"Using existing invite link: {invite_link}")

    except Exception as e:
        logger.error(f"Failed to generate or retrieve invite link: {str(e)}")
        await update.message.reply_text("An error occurred while generating the invite link.")
        return  # Early exit on error

    try:
        # Local copies of message and photo
        local_message_menu = markdown_v2(MENU)
        local_photo_menu = PHOTO_COYOTE_MIC

        if local_message_menu is None:
            logger.error("MENU is missing or None.")
            await update.message.reply_text("Menu content is not available.")
            return  # Early exit on error

        if local_photo_menu is None:
            logger.error("PHOTO_MENU is missing or None.")
            await update.message.reply_text("Menu photo is not available.")
            return  # Early exit on error

        if auth_result is None or 'url' in auth_result:
            # Handle unauthenticated user
            logger.info("User is not authenticated, showing minting link")
            buttons = [
                [
                    InlineKeyboardButton("📈 Trade Now", callback_data='/trade')                
                ],
                [
                    InlineKeyboardButton("🤑 Start Your Exchange", callback_data='/list')
                ],
                [
                    InlineKeyboardButton("👋 Say Hi!", url=invite_link)
                ]
            ]
        else:
            # Handle authenticated user
            logger.info("User is authenticated, showing exchange option")
            # Safely get username
            username = auth_result.get('tg_firstName') or BOT_USERNAME
            username_display = f"{username}'" if username and username.endswith('s') else f"{username}'s"

            local_message_menu = markdown_v2(LOGGED_IN.format(
                username_display=username_display,
                bot_username=BOT_USERNAME
            )+MENU)
                                             
            buttons = [
                [
                    InlineKeyboardButton("📈 Trade Now", callback_data='/trade')                
                ],
                [
                    InlineKeyboardButton("🤑 Share Token", callback_data='/share'),
                    InlineKeyboardButton("🤑 Share #Top3", callback_data='/top3')
                ],
                [
                    InlineKeyboardButton("🔐 Open Vault", url=ACME_APP_URL),
                    InlineKeyboardButton("👋 Say Hi!", url=invite_link)
                ],            
            ]

        # Send the menu with the minting link and photo
        await send_photo(
            update=update,
            context=context,
            photo_url=local_photo_menu,
            caption=local_message_menu,
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return await clear_cache(update, context)

    except Exception as e:
        logger.error(f"Failed to process menu: {str(e)}")
        await update.message.reply_text("An error occurred while processing the menu. Please try again later.")

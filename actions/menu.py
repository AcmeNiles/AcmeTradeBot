from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ConversationHandler, ContextTypes
from config import logger, ACME_GROUP, ACME_APP_URL
from utils.membership import get_invite_link
from utils.reply import send_animation, send_photo
from messages_photos import markdown_v2
PHOTO_MENU = "https://imagedelivery.net/P5lw0bNFpEj9CWud4zMJgQ/31de49c1-9e2d-4b3b-498a-a8ec7a34fc00/public"

# Define common menu messages with unescaped characters
MENU = (
    "\n *👋 Welcome to Acme!* \n\n"
    "🤑 *Start Your Exchange*\n"
    "Share trading cards. Get paid instantly.\n\n"
    "💳 *Tap.* *Trade.* *Done*.\n"
    "Easily buy any token with your bank card.\n\n"
    "🔒 *Own your Tokens*\n"
    "Tokens are secured in a safe. Only you have the keys.\n\n"
    "💸 Let’s make some money!"
)


# Process Menu Function
async def process_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("Entered process_menu function")
    auth_result = context.user_data.get('auth_result')

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

    try:
        # Local copies of message and photo
        local_message_menu =  markdown_v2(MENU)
        local_photo_menu = PHOTO_MENU if PHOTO_MENU else None

        if not local_message_menu:
            logger.error("MESSAGE_MENU is missing or None.")
            raise ValueError("MESSAGE_MENU is not available.")

        if not local_photo_menu:
            logger.error("PHOTO_MENU is missing or None.")
            raise ValueError("PHOTO_MENU is not available.")
            
        if 'url' in auth_result:
            # Handle unauthenticated user
            logger.info("User is not authenticated, showing minting link")
            buttons = [
                [InlineKeyboardButton("🤑 Start Your Exchange", callback_data='/list')],
                [InlineKeyboardButton("📈 Trade Now", callback_data='/trade')],
                [InlineKeyboardButton("👋 Say Hi!", url=invite_link)]
            ]
        else:
            # Handle authenticated user
            logger.info("User is authenticated, showing exchange option")
            buttons = [
                [InlineKeyboardButton("📈 Trade Now", callback_data='/trade')],
                [InlineKeyboardButton("🤑 View Exchange", callback_data='/list')],
                [
                    InlineKeyboardButton("🔐 Open Vault", url=ACME_APP_URL),
                    InlineKeyboardButton("👋 Say Hi!", url=invite_link)
                ],            
            ]

        # Send the menu with the minting link and photo
        try:
            await send_photo(
                update=update,
                context=context,
                photo_url=local_photo_menu,
                caption=local_message_menu,
                reply_markup=InlineKeyboardMarkup(buttons)
            )
            logger.info("Menu sent to unauthenticated user successfully")
        except Exception as e:
            logger.error(f"Failed to send unauthenticated user menu photo: {str(e)}")
            await update.message.reply_text("An error occurred while sending the menu photo.")

    except ValueError as ve:
        logger.error(f"ValueError: {str(ve)}")
        await update.message.reply_text(f"An error occurred: {str(ve)}")

    except Exception as e:
        logger.error(f"Failed to process menu: {str(e)}")
        await update.message.reply_text("An error occurred while processing the menu. Please try again later.")

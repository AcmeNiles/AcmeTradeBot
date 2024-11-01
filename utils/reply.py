import random
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext, ConversationHandler, ContextTypes
from config import logger, PHOTO_COYOTE_BANANA, ACME_GROUP, WHY_LIST, WHY_TRADE
from messages_photos import markdown_v2
from utils.membership import get_invite_link

LOADING = [
    "_Cooking up your exchange... 🍳 Just a sec!_",
    "_Tuning your exchange... 🛠️ Just a sec!_",
    "_Firing up your exchange... 🔥 Just a sec!_",
    "_Setting the stage for your exchange... 🎤 Just a sec!_",
    "_Gearing up your exchange... ⚙️ Just a sec!_",
]

async def say_hi_button(update, context):
    """
    Returns a 'Say Hi' button with the invite link logic.

    Args:
        context: Telegram context containing user data.

    Returns:
        InlineKeyboardButton: A 'Say Hi' button with the invite link.
    """
    user_id = update.effective_user.id

    # Check if the invite link already exists in context
    if 'invite_link' not in context.user_data:
        # Generate invite link
        invite_link = await get_invite_link(user_id, ACME_GROUP, context)
        context.user_data['invite_link'] = invite_link
        logger.info(f"Generated invite link: {invite_link}")
    else:
        invite_link = context.user_data['invite_link']
        logger.info(f"Using existing invite link: {invite_link}")

    # Return the "Say Hi" button with the invite link
    return InlineKeyboardButton("👋 Say Hi", url=invite_link)


async def send_message(update: Update, context: CallbackContext, text: str, reply_markup=None):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    buttons = reply_markup.inline_keyboard if reply_markup else []
    reply_markup = InlineKeyboardMarkup(buttons)

    return await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode="MarkdownV2", 
        reply_markup=reply_markup
    )

async def send_photo(update: Update, context: CallbackContext, photo_url: str, caption: str, reply_markup):
    try:
        user_id = update.effective_user.id

        buttons = reply_markup.inline_keyboard if reply_markup else []
        reply_markup = InlineKeyboardMarkup(buttons)

        if update.message:
            return await update.message.reply_photo(
                photo=photo_url,
                caption=caption,
                parse_mode="MarkdownV2",
                reply_markup=reply_markup,
            )
        elif update.callback_query:
            return await update.callback_query.message.reply_photo(
                photo=photo_url,
                caption=caption,
                parse_mode="MarkdownV2",
                reply_markup=reply_markup,
            )
        else:
            raise ValueError("Update is neither a message nor a callback query.")
    except Exception as e:
        logger.error(f"Failed to send photo: {str(e)}")
        await send_message(update, context, "An error occurred while sending the trading card.")


async def send_animation(update: Update, context: CallbackContext, animation_url: str, caption: str, reply_markup):
    try:
        user_id = update.effective_user.id

        buttons = reply_markup.inline_keyboard if reply_markup else []
        reply_markup = InlineKeyboardMarkup(buttons)

        if update.message:
            await update.message.reply_animation(
                animation=animation_url,
                caption=caption,
                parse_mode="MarkdownV2",
                reply_markup=reply_markup,
            )
        elif update.callback_query:
            await update.callback_query.message.reply_animation(
                animation=animation_url,
                caption=caption,
                parse_mode="MarkdownV2",
                reply_markup=reply_markup,
            )
        else:
            raise ValueError("Update is neither a message nor a callback query.")
    except Exception as e:
        logger.error(f"Failed to send animation: {str(e)}")
        await send_message(update, context, "An error occurred while sending the animation.")


async def send_error_message(update: Update, context) -> None:
    """
    Sends an error message with an invite link and a photo.

    Args:
        update (Update): The update containing information about the message.
        context: Telegram context containing user data.
    """
    user_id = update.effective_user.id  # Get the user ID from the update
    photo_url = PHOTO_COYOTE_BANANA
    caption = markdown_v2("⚠️ We're having some issues. Please try again later.")
    say_hi = await say_hi_button(update, context)  # Get the "Say Hi" button

    buttons = [
        [InlineKeyboardButton("Main Menu", callback_data='/menu'), say_hi],
    ]


    await send_photo(
        update,
        context,
        photo_url=photo_url,
        caption=caption,
        reply_markup=InlineKeyboardMarkup(buttons),
    )

async def send_why_trade(update: Update, context) -> int:
    """
    Sends the WHY_TRADE message with an invite link and a photo, then ends the conversation.

    Args:
        update (Update): The update containing information about the message.
        context: Telegram context containing user data.
    """

    photo_url = PHOTO_COYOTE_BANANA  # Replace with your actual WHY_TRADE photo URL
    caption = markdown_v2(WHY_TRADE)
    say_hi = await say_hi_button(update, context)  # Get the "Say Hi" button

    buttons = [
        [InlineKeyboardButton("📈 Trade Now!", callback_data='/trade')],
        [InlineKeyboardButton("Learn More", url="https://acme.am"), say_hi]
    ]

    await send_photo(
        update,
        context,
        photo_url=photo_url,
        caption=caption,
        reply_markup=InlineKeyboardMarkup(buttons),
    )

    return ConversationHandler.END

async def send_why_list(update: Update, context) -> int:
    """
    Sends the WHY_LIST message with an invite link and a photo, then ends the conversation.

    Args:
        update (Update): The update containing information about the message.
        context: Telegram context containing user data.
    """

    photo_url = PHOTO_COYOTE_BANANA  # Replace with your actual WHY_LIST photo URL
    caption = markdown_v2(WHY_LIST)
    
    # Prepare the buttons for the response
    say_hi = await say_hi_button(update, context)  # Get the "Say Hi" button

    buttons = [
        [InlineKeyboardButton("🤑 Earn Now!", callback_data='/list')],
        [InlineKeyboardButton("Learn More", url="https://acme.am"), say_hi]
    ]

    # Now you can use this `buttons` list in your send_message or send_photo functions

    await send_photo(
        update,
        context,
        photo_url=photo_url,
        caption=caption,
        reply_markup=InlineKeyboardMarkup(buttons),
    )

    return ConversationHandler.END

async def send_edit_top3_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a message prompting the user to edit their top 3 tokens."""
    message_text = markdown_v2(
        "_Share to help others buy & earn! 👆_\n\n"
        "_Edit your Top 3:_ /list 👈"
    )
    # Prepare the buttons for the response
    #say_hi = await say_hi_button(update, context)  # Get the "Say Hi" button

    #buttons = InlineKeyboardMarkup([
    #    [InlineKeyboardButton("🔄 Edit #Top3", callback_data="/list"), say_hi]
    #])
    
    await send_message(
        update,
        context,
        message_text,
        reply_markup=None,
    )

async def send_share_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a message prompting the user to edit their top 3 tokens."""
    message_text = markdown_v2(
        "_Getting your exchange ready...👆_"
    )
    # Prepare the buttons for the response
    #say_hi = await say_hi_button(update, context)  # Get the "Say Hi" button

    #buttons = InlineKeyboardMarkup([[say_hi]])

    await send_message(
        update,
        context,
        message_text,
        reply_markup=None,
    )

async def send_share_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a message prompting the user to edit their top 3 tokens."""
    message_text = markdown_v2(
        "_Share to help others buy & earn! 👆_"
    )
    # Prepare the buttons for the response
    #say_hi = await say_hi_button(update, context)  # Get the "Say Hi" button

    #buttons = InlineKeyboardMarkup([[say_hi]])

    await send_message(
        update,
        context,
        message_text,
        reply_markup=None,
    )


async def clear_cache(update, context):
    """Clear specific fields in user data to reset user intent and transaction details."""
    await delete_loading_message(update, context)
    logger.debug("Clearing user_data: intent, tokens, amount, receiver")
    fields_to_clear = ['intent', 'tokens', 'amount', 'receiver']
    for field in fields_to_clear:
        context.user_data.pop(field, None)
    return ConversationHandler.END

async def send_loading_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a random witty loading message and store its message ID."""
    message_text = markdown_v2(random.choice(LOADING))  # Select a random message
    loading_msg = await send_message(
        update,
        context,
        message_text,
        reply_markup=None,
    )
    context.user_data['loading_id'] = loading_msg.message_id  # Store the message ID

async def delete_loading_message(update, context):
    """Delete the previously sent loading message if it exists."""
    loading_id = context.user_data.pop('loading_id', None)
    if loading_id:
        try:
            await context.bot.delete_message(
                chat_id=update.effective_chat.id,
                message_id=loading_id
            )
        except Exception as e:
            logger.warning(f"Failed to delete loading message: {e}")
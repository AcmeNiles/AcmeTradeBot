from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from utils.reply import send_photo
from utils.tokenValidator import validate_tokens
from utils. getAcmeProfile import validate_user_and_tokens
from actions.list import process_list
from config import logger, SELECT_TOKEN, FEATURED_TOKENS_PAY, FEATURED_TOKENS_TRADE, FEATURED_TOKENS_LIST
from messages_photos import markdown_v2


# Define the message outside the function
NOT_LISTED = "🚫 *{tokens_text}* {verb} not listed. Message us to request listing."
ASK_TOKEN = "Type or select *{token_count}* you want to {intent}:"
PHOTO_TOP3 = "https://imagedelivery.net/P5lw0bNFpEj9CWud4zMJgQ/8fddf8d1-8699-48ba-ac01-31a810323e00/public"

async def handle_token(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Main handler to process the token input and route based on intent."""

    # Get requested tokens from user context data
    intent = context.user_data.get("intent")
    requested_tokens = context.user_data.get("tokens", [])
    logger.debug("Requested tokens from user context: %s", requested_tokens)

    # If no token is provided, prompt for input
    if not requested_tokens:
        logger.warning("No token input provided by user: %s", update.effective_user.id)
        return await prompt_for_token(update, context)

    # Validate tokens and store the valid ones
    valid_tokens, invalid_tokens = await validate_tokens(requested_tokens, update, context)
    logger.debug("Validation result - Invalid tokens: %s", invalid_tokens)

    # If invalid tokens found, notify the user
    if invalid_tokens:
        logger.warning("User provided invalid tokens: %s", invalid_tokens)
        return await prompt_for_token(update, context, invalid_tokens=invalid_tokens)

    context.user_data["tokens"] = valid_tokens
    # Log valid tokens before proceeding
    logger.info("Valid tokens for user %s: %s", update.effective_user.id, requested_tokens)

    # Proceed with further actions (like executing intent) after token validation
    logger.info("Proceeding with valid tokens for user: %s", update.effective_user.id)
    return True

async def prompt_for_token(update: Update, context: ContextTypes.DEFAULT_TYPE, invalid_tokens=None) -> int:
    """Prompt the user to enter or select a token."""
    user_intent = context.user_data.get("intent", "trade")  # Default intent is 'trade'

    if invalid_tokens:
        # Create a formatted message for invalid tokens
        invalid_tokens_text = ", ".join(invalid_tokens).upper()
        verb = "is" if len(invalid_tokens) == 1 else "are"
        caption = markdown_v2(NOT_LISTED.format(tokens_text=invalid_tokens_text, verb=verb))
        photo_url = PHOTO_TOP3  # Replace with your actual image URL

        logger.warning(f"Invalid token(s) entered: {invalid_tokens_text}")

        # Prepare buttons
        buttons = [InlineKeyboardButton("👋 Request Listing", url=context.user_data.get('invite_link', 'https://t.me/acmeonetap'))]
        # Send the photo to the user with the caption and buttons
        await send_photo(
            update,
            context,
            photo_url=photo_url,
            caption=caption,
            reply_markup=InlineKeyboardMarkup([buttons])
        )
        return ConversationHandler.END
    else:
        # Determine the token count message based on intent
        token_count = "1 token" if user_intent != 'list' else "TOP 3 tokens"
        caption = markdown_v2(ASK_TOKEN.format(token_count=token_count, intent=user_intent))
        photo_url = PHOTO_TOP3  # Replace with your actual image URL

        logger.debug(f"Prompting user to select {token_count} for {user_intent}.")

        # Choose the featured tokens based on the intent
        if user_intent == 'pay':
            featured_tokens = FEATURED_TOKENS_PAY
        elif user_intent == 'trade':
            featured_tokens = FEATURED_TOKENS_TRADE
        elif user_intent == 'list':
            featured_tokens = FEATURED_TOKENS_LIST
        else:
            featured_tokens = []

        # Prepare buttons for token selection
        buttons = [
            InlineKeyboardButton(
                list(token_dict.keys())[0],
                callback_data=f'/{user_intent} {list(token_dict.values())[0]}')
            for token_dict in featured_tokens
        ]

        # Send the photo to the user with the caption and buttons
        await send_photo(
            update,
            context,
            photo_url=photo_url,
            caption=caption,
            reply_markup=InlineKeyboardMarkup([buttons])
        )
        return SELECT_TOKEN



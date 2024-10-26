from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler
from utils.reply import send_photo, say_hi_button
from utils.tokenValidator import validate_tokens
from utils. getAcmeProfile import validate_user_and_tokens
from actions.list import process_list
from handlers.auth_handler import store_user_top3
from config import logger, SELECT_TOKEN, FEATURED_TOKENS_PAY, FEATURED_TOKENS_TRADE, FEATURED_TOKENS_LIST, BOT_USERNAME, PHOTO_COYOTE_BANANA
from messages_photos import markdown_v2

ASK_TRADE = """
☝️ *Tap. Trade. Done.*  
_Buy any token in #OneTap_

🌐 _Supported Chains:_
`Solana, Base, Arbitrum`

*⌨️ TYPE TOKEN TO {intent}:*  
`Ex: POPCAT / 0x5a31...`

"""
ASK_LIST = """
*🚀 [{username_display} Exchange](https://t.me/{bot_username}?start) 🚀*
_Help others buy your favorite tokens_

*🤑 Share → Earn*
Fees:    *0.5% USDC*
Points: *10 XP*

*⌨️ TYPE TOP 3 TOKENS TO LIST:*
`Memes: POPCAT, TOSHI, BRETT`
`Games: POPCAT, TOSHI, BRETT`
`AI:    POPCAT, TOSHI, BRETT`
"""

# Define the message outside the function
NOT_LISTED = "🚫 *{tokens_text}* {verb} not available. Message us to request listing."

PHOTO_TOP3 = "https://imagedelivery.net/P5lw0bNFpEj9CWud4zMJgQ/455f9727-a972-495d-162e-150f67c3e500/public"

async def handle_token(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Main handler to process the token input and route based on intent."""

    user_tg_username = update.effective_user.username

    # Get the user's intent and requested tokens from context
    intent = context.user_data.get("intent")
    requested_tokens = context.user_data.get("tokens", [])
    logger.debug("Requested tokens from user context: %s", requested_tokens)

    # Prompt for input if no token is provided
    if not requested_tokens:
        logger.warning("No token input provided by user: %s", update.effective_user.id)
        return await prompt_for_token(update, context)

    # Validate tokens
    valid_tokens, invalid_tokens = await validate_tokens(requested_tokens, update, context)
    logger.debug("Validation result - Invalid tokens: %s", invalid_tokens)

    # Handle invalid tokens if any
    if invalid_tokens:
        logger.warning("User provided invalid tokens: %s", invalid_tokens)
        await handle_invalid_tokens(update, context, intent, valid_tokens, invalid_tokens)

    # Store valid tokens in context user data
    context.user_data['tokens'] = valid_tokens  # Store valid tokens for later use

    # If the intent is "list", store valid tokens as the new top3
    if intent == "list":
        await store_user_top3(update, context, valid_tokens)

    logger.info("Valid tokens for user %s: %s", update.effective_user.id, valid_tokens)
    return True


async def prompt_for_token(update: Update, context: ContextTypes.DEFAULT_TYPE, invalid_tokens=None) -> int:
    """Prompt the user to enter or select a token."""
    user_intent = context.user_data.get("intent", "trade")  # Default intent is 'trade'

    # Nested intent-based logic for token prompts with specific "why" buttons
    if user_intent == 'list':
        username = update.effective_user.first_name
        template = ASK_LIST.format(
            username_display = f"{username}'" if username.endswith('s') else f"{username}'s",
            bot_username=BOT_USERNAME
        )
        featured_tokens = FEATURED_TOKENS_LIST
        why_button = InlineKeyboardButton("Learn More", callback_data='/why_list')
    elif user_intent in ['trade', 'share']:
        template = ASK_TRADE.format(
            intent = user_intent.upper()
        )
        featured_tokens = FEATURED_TOKENS_TRADE
        why_button = InlineKeyboardButton("Learn More", callback_data='/why_trade')
    elif user_intent == 'pay':
        template = ASK_PAY
        featured_tokens = FEATURED_TOKENS_PAY
        why_button = InlineKeyboardButton("Learn More", callback_data='/why_pay')
    else:
        template = ASK_TRADE  # Default to trade
        featured_tokens = []
        why_button = InlineKeyboardButton("Learn More", callback_data='/why_trade')

    # Format caption and prepare the photo for sending
    caption = markdown_v2(template)
    photo_url = PHOTO_COYOTE_BANANA  # Replace with your actual image URL
    
    # Prepare buttons for token selection, ensure each button is wrapped in a list (for rows)
    token_buttons = [
        [
            InlineKeyboardButton(
                list(token_dict.keys())[0],
                callback_data=f'/{user_intent} {list(token_dict.values())[0]}'
            ) for token_dict in featured_tokens
        ]
    ]

    # Ensure `say_hi_button` returns an InlineKeyboardButton
    say_hi = await say_hi_button(update, context)

    # Combine the specific "why" button and "Say Hi" button into a new row
    buttons = token_buttons + [[why_button, say_hi]]  # Both buttons are in the second row

    # Send the photo to the user with the caption and buttons
    await send_photo(
        update,
        context,
        photo_url=photo_url,
        caption=caption,
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    return SELECT_TOKEN

async def handle_invalid_tokens(update: Update, context: ContextTypes.DEFAULT_TYPE, intent, valid_tokens, invalid_tokens):
    """Handles invalid tokens by sending a warning and prompting for a listing request."""
    invalid_tokens_text = ", ".join(invalid_tokens).upper()
    verb = "is" if len(invalid_tokens) == 1 else "are"
    caption = markdown_v2(NOT_LISTED.format(tokens_text=invalid_tokens_text, verb=verb))
    photo_url = PHOTO_TOP3  # Replace with your actual image URL

    logger.warning(f"Invalid token(s) entered: {invalid_tokens_text}")

    # Prepare buttons, each in its own row
    buttons = [
        [InlineKeyboardButton("👋 Request Listing", url=context.user_data.get('invite_link', 'https://t.me/acmeonetap'))],
        [InlineKeyboardButton("🔄 Try Again", callback_data=f"/{intent}")]
    ]

    # Send the photo to the user with the caption and buttons
    await send_photo(
        update,
        context,
        photo_url=photo_url,
        caption=caption,
        reply_markup=InlineKeyboardMarkup(buttons)
    )

    # Return ConversationHandler.END only if there are no valid tokens
    if len(valid_tokens) == 0:
        return ConversationHandler.END
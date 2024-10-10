from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, InputFile
from telegram.ext import CallbackContext
from utils.createJWT import get_user_data  # Import user data extraction function
from createMintingLink import create_minting_link  # Import create_minting_link function
from config import WELCOME_IMAGE_URL

# Function to handle the /start command
async def start(update: Update, context: CallbackContext) -> None:
    # Get the token symbol from the command arguments
    token_symbol = context.args[0] if context.args else None

    # Base welcome text
    welcome_text = (
        "👋 *Welcome to Acme\!*\n\n"
        "💳 *Tap\. Trade\. Done\.\n*Easily buy any token with your bank card\.\n\n"
        "🤑 *Share to Earn\n*Share trading links and earn 50% of our fees\.\n\n"
        "🔒 *Own your Tokens\n*You always control your tokens\. Acme never touches them\.\n\n"
    )

    # Conditional addition based on token symbol
    if token_symbol:
        welcome_text += (
            f"*Here to create a trading link for {token_symbol}?* Mint a free access pass to start making some money \! 💸 "
        )
    else:
        welcome_text += (
            "*Claim your free access pass and /trade to start making some money\! 💸 *"
        )

    # Get user data
    user_data = get_user_data(update)

    try:
        # Create the minting link
        minting_link = create_minting_link(user_data)

        if minting_link:
            # Create an inline keyboard button with the WebAppInfo (to open in Telegram as a web app)
            # Assuming minting_link is defined elsewhere in your code
            keyboard = [
                [
                    InlineKeyboardButton(
                        "Mint Your Access Pass",
                        web_app=WebAppInfo(url=minting_link)  # Open as a Web App inside Telegram
                    )
                ],
                [
                    InlineKeyboardButton(
                        "Open Vault",  # Button to open the vault
                        web_app=WebAppInfo(url='https://app.acme.am/vault')  # Link to the vault web app
                    )
                ],
                [
                    InlineKeyboardButton(
                        "Go to Acme Group",  # Button to go to Acme group
                        url='https://t.me/acmeonetap'  # Link to the Telegram group
                    )
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            # Send the welcome text as the caption of the image
            await update.message.reply_photo(photo=WELCOME_IMAGE_URL, caption=welcome_text, reply_markup=reply_markup, parse_mode='MarkdownV2')
        else:
            await update.message.reply_text("Minting successful, but no minting link was returned.")
    except Exception as e:
        await update.message.reply_text(f"An error occurred: {str(e)}")
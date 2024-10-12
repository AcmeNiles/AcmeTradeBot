from config import logger
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import CallbackContext, ConversationHandler
from utils.createTradingLink import create_trading_link
from messages_photos import MESSAGE_TRADE

# Simplified 'process_trade' function
async def process_trade(update: Update, context: CallbackContext) -> int:
    logger.info("Entered process_trade function.")

    try:
        # Retrieve tg_key and token object from user_data
        tg_key = context.user_data.get('tg_key')
        token = context.user_data.get('token')

        # Log the retrieved values
        logger.debug(f"Retrieved tg_key: {tg_key}")
        logger.debug(f"Retrieved token object: {token}")

        # Check if tg_key is available
        if not tg_key:
            logger.error("Telegram key not found in user data.")
            await update.message.reply_text("Failed to authenticate. Please try again.")
            return ConversationHandler.END  # End conversation if tg_key is missing

        # Check if token is provided
        if not token:
            logger.warning("No token found for trade.")
            await update.message.reply_text("Please specify a token to trade.")
            return ConversationHandler.END  # End the conversation if no token

        # Extract chainId and contract_address from the token object
        chain_id = token.get('chain_id')  # Accessing chainId as token['chain_id']
        contract_address = token.get('contract_address')

        # Log chain_id and contract_address values
        logger.debug(f"Extracted chain_id: {chain_id}")
        logger.debug(f"Extracted contract_address: {contract_address}")

        # Ensure both chain_id and contract_address are available
        if not chain_id or not contract_address:
            logger.error("Missing chain ID or contract address in token object.")
            await update.message.reply_text("Token data is incomplete. Please check and try again.")
            return ConversationHandler.END  # End conversation if data is missing

        # Create a trading link for the user
        trading_link = await create_trading_link(tg_key, chain_id, contract_address, "")

        # Log the trading link creation attempt
        logger.debug(f"Creating trading link with tg_key: {tg_key}, chain_id: {chain_id}, contract_address: {contract_address}")

        if trading_link:
            logger.debug(f"Trading link created successfully: {trading_link}")
            buttons = [[
                InlineKeyboardButton(
                    f"Trade {token['symbol']}",
                    web_app=WebAppInfo(url=trading_link)
                )
            ]]

            # Generate trading card text using the token data
            trading_card_text = MESSAGE_TRADE.format(
                symbol=token['symbol'],
                chain_id=chain_id,
                contract_address=contract_address
            )

            # Log the generated trading card text
            logger.debug(f"Generated trading card text: {trading_card_text}")

            # Send the trading card with the photo
            try:
                await update.message.reply_photo(
                    photo="URL_TO_YOUR_TRADING_CARD_IMAGE",  # Replace with actual image URL or variable
                    caption=trading_card_text,
                    parse_mode="MarkdownV2",
                    reply_markup=InlineKeyboardMarkup(buttons)
                )
                logger.info("Trading card presented successfully.")
            except Exception as e:
                logger.error(f"Failed to send trading card photo: {str(e)}")
                await update.message.reply_text("An error occurred while sending the trading card.")

            return ConversationHandler.END  # End conversation after presenting the trading card
        else:
            logger.warning(f"Failed to create trading link for ticker: {token['symbol']}.")
            await update.message.reply_text("Trading link couldn't be created.")
            return ConversationHandler.END  # End conversation if trading link fails

    except Exception as e:
        logger.error(f"Error in process_trade function: {e}")
        await update.message.reply_text("An error occurred while processing the trade. Please try again.")
        return ConversationHandler.END  # End conversation on error

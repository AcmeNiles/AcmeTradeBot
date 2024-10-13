from config import logger
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import CallbackContext, ConversationHandler
from utils.createTradingLink import create_trading_link
from messages_photos import MESSAGE_TRADE  # Removed PHOTO_TRADE since we're using logoUrl

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
        symbol = token.get('symbol').strip().upper()
        chain_id = token.get('chain_id')  # Accessing chain_id as token['chain_id']
        contract_address = token.get('contract_address')
        logoUrl = token.get('logoUrl')

        # Log chain_id and contract_address values
        logger.debug(f"Extracted chain_id: {chain_id}")
        logger.debug(f"Extracted symbol: {symbol}")
        logger.debug(f"Extracted logoUrl: {logoUrl}")
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
                    f"Trade {symbol}",
                    web_app=WebAppInfo(url=trading_link)
                )
            ]]

            # Generate trading card text using the token data
            trading_card_text = MESSAGE_TRADE.format(
                symbol=symbol,
                chain_id=chain_id,
                contract_address=contract_address
            )

            # Log all information before sending
            logger.debug(f"Preparing to send trading card with the following details:\n"
                         f"Photo: {logoUrl}\n"  # Change made here
                         f"Caption: {trading_card_text}\n"
                         f"Buttons: {buttons}")

            # Send the trading card with the photo
            try:
                # Check if the update is from a message or a callback query
                if update.message:
                    await update.message.reply_photo(
                        photo=logoUrl,  # Change made here
                        caption=trading_card_text,
                        parse_mode="MarkdownV2",
                        reply_markup=InlineKeyboardMarkup(buttons)
                    )
                elif update.callback_query:
                    await update.callback_query.message.reply_photo(
                        photo=token['logoUrl'],  # Change made here
                        caption=trading_card_text,
                        parse_mode="MarkdownV2",
                        reply_markup=InlineKeyboardMarkup(buttons)
                    )
                else:
                    logger.error("No message or callback query found in the update.")
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text="An unexpected error occurred. Please try again."
                    )
                logger.info("Trading card presented successfully.")
            except Exception as e:
                logger.error(f"Failed to send trading card photo: {str(e)}")
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="An error occurred while sending the trading card."
                )

            return ConversationHandler.END  # End conversation after presenting the trading card
        else:
            logger.warning(f"Failed to create trading link for ticker: {token['symbol']}.")
            await update.message.reply_text("Trading link couldn't be created.")
            return ConversationHandler.END  # End conversation if trading link fails

    except Exception as e:
        logger.error(f"Error in process_trade function: {e}")
        await update.message.reply_text("An error occurred while processing the trade. Please try again.")
        return ConversationHandler.END  # End conversation on error

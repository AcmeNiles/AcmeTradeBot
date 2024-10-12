import asyncio
from config import logger
from http import HTTPStatus

import uvicorn
from asgiref.wsgi import WsgiToAsgi
from flask import Flask, Response, make_response, request

from telegram import Update
from telegram.ext import (
    Application,
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
)
from telegram.ext import filters  # For filters

from webhook import set_acme_webhook
from config import TOKEN, PORT, URL
from commands.menu import menu, select_intent
from commands.ticker import ask_ticker
from commands.trade import select_token, trade_card
#from commands.pay import start_pay, ask_pay_ticker, ask_pay_amount, pay_card
from utils.report_state import report_state

# Define conversation states
from config import MENU, SELECT_INTENT, SELECT_TOKEN, TRADE_CARD

# Enable logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
# set higher logging level for httpx to avoid all GET and POST requests being logged
#logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# Example fallback handler function
async def unknown_command_handler(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "Sorry, I didn't understand that command. Please use /start to begin or select an option from the menu."
    )
    
async def main() -> None:
    application = (
        Application.builder().token(TOKEN).updater(None).build()
    )
    # register handlers
    # Define the conversation handler
    conversation_handler = ConversationHandler(
        entry_points=[
            CommandHandler('start', menu),  # Entry point for starting the bot
            CommandHandler('trade', select_token),  # Entry point for trading
            MessageHandler(filters.TEXT & ~filters.COMMAND, menu)  # Default to menu for other text
        ],
        states={
            MENU: [
                CallbackQueryHandler(menu, pattern='cancel'),  # Handles cancel button
                CallbackQueryHandler(menu, pattern='menu')  # Handles "menu" button
            ],
            SELECT_INTENT: [
                CallbackQueryHandler(select_intent),  # Handles button clicks for Trade Now and Get Paid
            ],
            SELECT_TOKEN: [
                CallbackQueryHandler(select_token),  # Handles "Trade Now" button
            ],
            TRADE_CARD: [
                CallbackQueryHandler(trade_card),  # Handle trading link interactions
            ],
        },
        fallbacks=[
            CommandHandler('start', menu),  # Entry point for starting the bot
            CommandHandler('trade', select_token),  # Entry point for trading
            MessageHandler(filters.TEXT & ~filters.COMMAND, menu)  # Default to menu for other text       
        ],
    )
    application.add_handler(conversation_handler)


    # Pass webhook settings to telegram
    await application.bot.set_webhook(url=f"{URL}/telegram", allowed_updates=Update.ALL_TYPES)
    set_acme_webhook()

    # Set up webserver
    flask_app = Flask(__name__)
    @flask_app.get("/")  # type: ignore[misc]
    async def health() -> Response:
        """For the health endpoint, reply with a simple plain text message."""
        response = make_response("The bot is still running fine :)", HTTPStatus.OK)
        response.mimetype = "text/plain"
        return response

    @flask_app.post("/telegram")  # type: ignore[misc]
    async def telegram() -> Response:
        """Handle incoming Telegram updates by putting them into the update_queue"""
        await application.update_queue.put(Update.de_json(data=request.json, bot=application.bot))
        return Response(status=HTTPStatus.OK)

    @flask_app.post("/acme")
    async def acme() -> Response:
        """Handle incoming Acme webhook requests."""
        logger.debug("Received an update from Acme.")

        # Accessing the incoming request data
        _message = request.json  # Get the JSON body
        _signature = request.headers.get(
            "acme-signature")  # Get the signature from the headers

        # Process the message after successful signature verification
        try:
            order = _message["order"]
            update = WebhookUpdate(
                id=order["id"],
                status=order["status"],
                created_at=order["createdAt"],
                blockchain_tx_hash=order.get("blockchainTransactionHash", ""),
                execution_message=order.get("executionMessage", ""),
                intent_id=order["intentId"],
                intent_memo=order.get("intentMemo", ""),
                user_id=order["userId"])
            await application.update_queue.put(update)
            return Response(status=HTTPStatus.OK)
        except KeyError as e:
            logger.warning(f"Missing expected key: {e}")
            return Response(status=HTTPStatus.BAD_REQUEST)
        except Exception:
            logger.exception("Error processing Acme webhook")
            return Response(status=HTTPStatus.INTERNAL_SERVER_ERROR)

    webserver = uvicorn.Server(
        config=uvicorn.Config(
            app=WsgiToAsgi(flask_app),
            port=PORT,
            use_colors=False,
            host="0.0.0.0",
        )
    )

    # Run application and webserver together
    async with application:
        await application.start()
        await webserver.serve()
        await application.stop()


if __name__ == "__main__":
    asyncio.run(main())

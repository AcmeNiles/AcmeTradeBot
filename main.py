import logging
from http import HTTPStatus
import asyncio
import uvicorn
from asgiref.wsgi import WsgiToAsgi
from flask import Flask, Response, make_response, request
from config import *
from messages_photos import MESSAGE_MENU
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters
)

from handlers.action_handler import execute_action
from handlers.input_handler import input_to_action
from handlers.token_handler import handle_token
from handlers.amount_handler import handle_amount
from handlers.receiver_handler import handle_recipient
from utils.webhook import set_acme_webhook

# Main function to set up the bot
async def main():
    logger.debug("Starting main setup function.")

    try:
        # Replace 'YOUR_TOKEN' with your actual bot token
        application = ApplicationBuilder().token(BOT_TOKEN).build()
        logger.info("Bot application built successfully.")

        # Define the conversation handler
        conv_handler = ConversationHandler(
            entry_points=[
                CommandHandler(['start', 'menu', 'trade', 'pay', 'request', 'vault'], input_to_action),
                CallbackQueryHandler(input_to_action),
                MessageHandler(filters.TEXT & ~filters.COMMAND, input_to_action)  # Catch any text that isn't a command
            ],
            states={
                SELECT_TOKEN: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_token)],
                SELECT_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_amount)],
                SELECT_RECIPIENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_recipient)],
                WAITING_FOR_AUTH: [MessageHandler(filters.TEXT & ~filters.COMMAND, execute_action)]
            },
            fallbacks=[
                MessageHandler(filters.TEXT & ~filters.COMMAND, input_to_action)  # Catch any text that isn't a command
            ],
            allow_reentry=True
        )

        # Add the conversation handler to the application
        application.add_handler(conv_handler)
        logger.info("Conversation handler added to application.")

        # Pass webhook settings to telegram and acme
        logger.info(f"Setting up Telegram webhook with URL: {URL}/telegram")
        await application.bot.set_webhook(url=f"{URL}/telegram", allowed_updates=Update.ALL_TYPES)

        logger.debug("Setting ACME webhook.")
        await set_acme_webhook()

    except Exception as e:
        logger.error(f"Error during bot and webhook setup: {str(e)}")
        return

    # Set up webserver
    flask_app = Flask(__name__)

    @flask_app.get("/")  # type: ignore[misc]
    async def health() -> Response:
        """For the health endpoint, reply with a simple plain text message."""
        logger.debug("Health endpoint hit. Responding with OK status.")
        response = make_response("The bot is still running fine :)", HTTPStatus.OK)
        response.mimetype = "text/plain"
        return response

    @flask_app.post("/telegram")  # type: ignore[misc]
    async def telegram() -> Response:
        """Handle incoming Telegram updates by putting them into the update_queue"""
        logger.debug("Received a new Telegram update.")
        try:
            await application.update_queue.put(Update.de_json(data=request.json, bot=application.bot))
            logger.info("Telegram update processed successfully.")
            return Response(status=HTTPStatus.OK)
        except Exception as e:
            logger.error(f"Error handling Telegram update: {str(e)}")
            return Response(status=HTTPStatus.INTERNAL_SERVER_ERROR)

    @flask_app.post("/acme")
    async def acme() -> Response:
        """Handle incoming Acme webhook requests."""
        logger.debug("Received an update from Acme.")

        # Accessing the incoming request data
        _message = request.json  # Get the JSON body
        _signature = request.headers.get("acme-signature")  # Get the signature from the headers

        logger.debug(f"Acme message received: {_message}, signature: {_signature}")

        # Process the message after successful signature verification
        try:
            order = _message["order"]
            logger.info(f"Processing Acme order: {order}")

            update = WebhookUpdate(
                id=order["id"],
                status=order["status"],
                created_at=order["createdAt"],
                blockchain_tx_hash=order.get("blockchainTransactionHash", ""),
                execution_message=order.get("executionMessage", ""),
                intent_id=order["intentId"],
                intent_memo=order.get("intentMemo", ""),
                user_id=order["userId"]
            )

            await application.update_queue.put(update)
            logger.info(f"Acme update processed successfully for order ID: {order['id']}")
            return Response(status=HTTPStatus.OK)

        except KeyError as e:
            logger.warning(f"Missing expected key in Acme message: {e}")
            return Response(status=HTTPStatus.BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error processing Acme webhook: {str(e)}")
            return Response(status=HTTPStatus.INTERNAL_SERVER_ERROR)

    try:
        logger.debug("Starting webserver with Uvicorn.")
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
            logger.info("Bot application started successfully.")
            await webserver.serve()
            logger.info("Webserver started successfully.")
            await application.stop()
            logger.info("Bot application stopped successfully.")

    except Exception as e:
        logger.error(f"Error during webserver or application lifecycle: {str(e)}")

if __name__ == "__main__":
    logger.info("Bot is starting up.")
    asyncio.run(main())
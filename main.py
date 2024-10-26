import json
import random
import datetime
from http import HTTPStatus
import asyncio
import uvicorn
from asgiref.wsgi import WsgiToAsgi
from flask import Flask, Response, make_response, request
from config import *
from telegram import Update, Message, Chat, User, MessageEntity
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    TypeHandler,
    filters
)
from handlers.input_handler import input_to_action
from utils.webhook import set_acme_webhook, process_acme_payload, AcmeWebhookUpdate, AcmeContext, webhook_handler

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
                CommandHandler(VALID_COMMANDS, input_to_action),
                MessageHandler(filters.ALL, input_to_action),  # Absolute fallback for any message
                CallbackQueryHandler(input_to_action),
            ],
            states={
                SELECT_TOKEN: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_to_action)],
                SELECT_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_to_action)],
                SELECT_RECEIVER: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_to_action)],
            },
            fallbacks=[
                MessageHandler(filters.ALL, input_to_action),  # Absolute fallback for any message
                CallbackQueryHandler(input_to_action)
            ],
            allow_reentry=True
        )

        # Add the conversation handler to the application
        application.add_handler(conv_handler)
        application.add_handler(TypeHandler(AcmeWebhookUpdate, webhook_handler))
        logger.info("Conversation handler added to application.")

        # Pass webhook settings to telegram and acme
        try:
            logger.info(f"Setting webhook for URL: {URL}/telegram with all update types.")
            await application.bot.set_webhook(url=f"{URL}/telegram", allowed_updates=Update.ALL_TYPES)
            logger.info("Telegram Webhook successfully set.")
        except Exception as e:
            logger.error(f"Failed to set webhook. Error: {e}")

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
        logger.debug("Received an update from Acme.")

        # Step 1: Validate and Process the Payload
        try:
            _message = request.json
            _signature = request.headers.get("acme-signature")

            if not _message or not _signature:
                raise ValueError("Missing message body or Acme signature header.")

            update = await process_acme_payload(_message, _signature, application)

        except ValueError as ve:
            logger.warning(f"Validation error: {ve}")
            return Response(status=HTTPStatus.BAD_REQUEST)
        except Exception as e:
            logger.error(f"Unexpected error during payload processing: {e}", exc_info=True)
            return Response(status=HTTPStatus.INTERNAL_SERVER_ERROR)

        # Step 2: Trigger Synthetic Update if Auth Was Updated
        try:
            if update:
                # Add the update to the queue for processing
                await application.update_queue.put(update)
            else:
                logger.debug(f"No webhook trigger executed.")

        except Exception as e:
            logger.error(f"Error handling synthetic Telegram update: {str(e)}", exc_info=True)
            return Response(status=HTTPStatus.INTERNAL_SERVER_ERROR)

        logger.info("Acme update processed successfully")
        return Response(status=HTTPStatus.OK)

    
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
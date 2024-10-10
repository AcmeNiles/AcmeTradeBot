import asyncio
import html
import logging
from dataclasses import dataclass
from http import HTTPStatus

import uvicorn
from asgiref.wsgi import WsgiToAsgi
from flask import Flask, Response, abort, make_response, request

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackContext,
    CommandHandler,
    ContextTypes,
    ExtBot,
    filters,
    MessageHandler,
    TypeHandler,
)

from webhook import set_acme_webhook
from config import TOKEN, PORT, URL, ACME_API_KEY, ADMIN_CHAT_ID
from commands.start import start
from commands.trade import trade_handler
from commands.pay import payment_handler
# Enable logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

async def main() -> None:
    application = (
        Application.builder().token(TOKEN).updater(None).build()
    )
    # register handlers
    application.add_handler(trade_handler)
    application.add_handler(payment_handler)
    # application.add_handler(CommandHandler("start", start))
    # application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, start))
    # Pass webhook settings to telegram
    await application.bot.set_webhook(url=f"{URL}/telegram", allowed_updates=Update.ALL_TYPES)

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

    set_acme_webhook()
    
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
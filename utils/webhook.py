import logging
import requests
from config import URL, ACME_URL, ACME_API_KEY

# Set up logging
logger = logging.getLogger(__name__)

async def set_acme_webhook():
    # ACME webhook setup URL and headers
    acme_api = ACME_URL + "user/set-web-hook"
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "X-API-KEY": ACME_API_KEY
    }

    # Data payload with the Replit URL as the webhook target
    data = {
        "webHookUrl": URL + "/acme"
    }

    logger.info("Preparing to set ACME webhook.")
    logger.debug(f"ACME API URL: {acme_api}")
    logger.debug(f"Headers: {headers}")
    logger.debug(f"Payload: {data}")

    try:
        # Make the POST request to set the webhook
        logger.info("Sending request to set webhook...")
        response = requests.post(acme_api, json=data, headers=headers)

        # Print the response in the logs
        if response.status_code == 200:
            logger.info(f"ACME webhook set successfully! Status code: {response.status_code}")
            logger.debug(f"Response Text: {response.text}")
            logger.debug(f"Payload Sent: {data}")
        else:
            logger.warning(f"Failed to set ACME webhook. Status code: {response.status_code}")
            logger.warning(f"Response: {response.text}")

    except requests.RequestException as e:
        logger.error(f"An error occurred while setting the ACME webhook: {str(e)}", exc_info=True)
    except Exception as e:
        logger.error(f"An unexpected error occurred: {str(e)}", exc_info=True)

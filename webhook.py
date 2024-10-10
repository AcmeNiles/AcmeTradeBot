import requests
from config import URL, ACME_URL, ACME_API_KEY

def set_acme_webhook():
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

    try:
        # Make the POST request to set the webhook
        response = requests.post(acme_api, json=data, headers=headers)

        # Print the response in the logs
        if response.status_code == 200:
            print(f"ACME webhook set successfully! Response: {response.text}, {data}")
        else:
            print(f"Failed to set ACME webhook. Status code: {response.status_code}\nResponse: {response.text}")

    except Exception as e:
        print(f"An error occurred while setting the ACME webhook: {str(e)}")
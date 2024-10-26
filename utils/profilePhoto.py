import os
import aiohttp
from urllib.parse import unquote
from telegram import Update
from telegram.ext import ContextTypes

from config import CLOUDFLARE_ACCOUNT_ID, CLOUDFLARE_API_TOKEN, CLOUDFLARE_HASH, logger

# Function to check if the image already exists in Cloudflare
async def image_exists_in_cloudflare(image_id: str) -> bool:
    logger.debug(f"Checking if image exists in Cloudflare: {image_id}.")
    async with aiohttp.ClientSession() as session:
        try:
            # Use the Cloudflare image ID or URL for checking
            async with session.get(f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/images/v1/{image_id}", headers={
                'Authorization': f'Bearer {CLOUDFLARE_API_TOKEN}',
            }) as response:
                logger.debug(f"Cloudflare response status: {response.status}.")
                if response.status == 200:
                    data = await response.json()
                    if data['success']:
                        logger.info(f"Image found in Cloudflare: {image_id}.")
                        return True
                else:
                    logger.error(f"Failed to fetch image from Cloudflare. Status: {response.status} - {await response.text()}.")
        except Exception as e:
            logger.error(f"Error while checking image in Cloudflare: {e}.")
    return False
    
# Function to upload user profile photo
async def upload_to_cloudflare(image_path: str, image_name: str) -> dict:
    logger.debug(f"Preparing to upload image from {image_path} with name {image_name}.")
    async with aiohttp.ClientSession() as session:
        with open(image_path, 'rb') as f:
            data = aiohttp.FormData()
            data.add_field('file', f, filename=image_name, content_type='image/jpeg')  # Ensure content type is correct

            upload_url = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/images/v1"
            async with session.post(upload_url, headers={
                'Authorization': f'Bearer {CLOUDFLARE_API_TOKEN}',
                'Accept': 'application/json'
            }, data=data) as response:
                logger.debug(f"Cloudflare upload response status: {response.status}.")
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"Image uploaded successfully for user. Cloudflare ID: {result['result']['id']}")
                    return result  # Return the entire response for further processing
                else:
                    logger.error(f"Failed to upload image. Status: {response.status}. Response: {await response.text()}.")
                    return None

async def fetch_user_profile_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    user_id = update.effective_user.id  # Get the user ID from the update object
    logger.debug(f"Fetching profile photo URL for user_id {user_id}.")

    # Check if the user's profile photo exists on Telegram
    try:
        user = await context.bot.get_chat(user_id)
        if user.photo:
            profile_photo_file_id = user.photo.big_file_id  # Get the largest available photo size
            #logger.info(f"Fetched profile photo file ID for user_id {user_id}. File ID: {profile_photo_file_id}")

            # Get the file path for the photo on Telegram servers
            file = await context.bot.get_file(profile_photo_file_id)
            photo_url = file.file_path  # This will give you the relative path to the file on Telegram's server

            logger.debug(f"Profile photo URL for user_id {user_id}: {photo_url}")
            # Store the URL in context.user_data for future use
            return photo_url  # Return the Telegram profile photo URL

        else:
            logger.warning(f"User {user_id} does not have a profile photo.")
    except Exception as e:
        logger.error(f"Error while fetching user profile photo URL for user_id {user_id}: {e}")

    return None  # Return None if no profile photo is found or an error occurs
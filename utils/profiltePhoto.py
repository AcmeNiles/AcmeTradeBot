import aiohttp
import os
from telegram import Update
from telegram.ext import CallbackContext
from config import CLOUDFLARE_ACCOUNT_ID, CLOUDFLARE_API_TOKEN, logger

# Constants
IMAGE_DIRECTORY = "path/to/image/directory/"  # Set your image directory path here
CLOUDFLARE_API_URL = f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/images/v1"

# Function to check if the image already exists in Cloudflare
async def image_exists_in_cloudflare(image_name: str) -> bool:
    logger.debug(f"Checking if image exists in Cloudflare: {image_name}.")
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(f"{CLOUDFLARE_API_URL}/list", headers={
                'Authorization': f'Bearer {CLOUDFLARE_API_TOKEN}',
            }) as response:
                logger.debug(f"Cloudflare response status: {response.status}.")
                if response.status == 200:
                    data = await response.json()
                    logger.debug(f"Cloudflare images list fetched successfully. Data: {data}.")
                    for image in data['result']:
                        if image['filename'] == image_name:
                            logger.info(f"Image found in Cloudflare: {image_name}.")
                            return True
                    logger.info(f"Image not found in Cloudflare: {image_name}.")
                else:
                    logger.error(f"Failed to fetch images list from Cloudflare. Status: {response.status} - {await response.text()}.")
        except Exception as e:
            logger.error(f"Error while checking image in Cloudflare: {e}.")
    return False

# Function to upload the image to Cloudflare
async def upload_to_cloudflare(image_path: str, user_id: str) -> dict:
    logger.debug(f"Preparing to upload image for user {user_id} from {image_path}.")
    async with aiohttp.ClientSession() as session:
        try:
            with open(image_path, 'rb') as image_file:  # Open the image file
                async with session.post(CLOUDFLARE_API_URL, headers={
                    'Authorization': f'Bearer {CLOUDFLARE_API_TOKEN}',
                    'Content-Type': 'image/jpeg'
                }, data=image_file) as response:
                    logger.debug(f"Cloudflare upload response status: {response.status}.")
                    if response.status == 200:
                        upload_response = await response.json()
                        logger.info(f"Successfully uploaded image for user {user_id}. Response: {upload_response}.")
                        return upload_response  # Return the response containing the image URL
                    else:
                        logger.error(f"Failed to upload image for user {user_id}: {response.status} - {await response.text()}.")
        except Exception as e:
            logger.error(f"Error while uploading image for user {user_id}: {e}.")
    return None

# Helper function to fetch the user's profile photo
async def fetch_user_profile_photo(update: Update, context: CallbackContext) -> str:
    user_id = update.effective_user.id  # Get the user ID from the update object
    logger.debug(f"Fetching profile photo for user_id {user_id}.")

    # Construct the Cloudflare path
    image_name = f"{user_id}_profile.jpg"  # Use a unique image name for the user
    image_path = os.path.join(IMAGE_DIRECTORY, image_name)
    logger.debug(f"Constructed image path: {image_path}.")

    # Check if the image already exists in Cloudflare
    if await image_exists_in_cloudflare(image_name):
        cloudflare_url = f"https://your_cloudflare_images_url/{image_name}"  # Adjust the URL as needed
        logger.info(f"Returning existing Cloudflare URL for user_id {user_id}: {cloudflare_url}.")
        return cloudflare_url  # Return the existing Cloudflare URL

    # Attempt to get the user's profile photo from Telegram
    try:
        user = await context.bot.get_chat(user_id)
        if user.photo:
            profile_photo_file_id = user.photo.big_file_id  # Get the largest available photo size
            logger.info(f"Fetched profile photo for user_id {user_id}. File ID: {profile_photo_file_id}")
    
            # Get the file path for the photo
            file = await context.bot.get_file(profile_photo_file_id)
            photo_url = file.file_path  # This will give you the relative path to the file on Telegram's server
    
    
            # Download the photo
            async with aiohttp.ClientSession() as session:
                async with session.get(photo_url) as response:
                    if response.status == 200:
                        logger.debug(f"Successfully downloaded profile photo from Telegram for user_id {user_id}.")
                        os.makedirs(os.path.dirname(image_path), exist_ok=True)  # Ensure the directory exists
                        with open(image_path, 'wb') as f:
                            f.write(await response.read())  # Save the image locally
                        logger.info(f"Profile photo saved locally for user_id {user_id} at {image_path}.")
    
                        # Upload the profile photo to Cloudflare
                        upload_response = await upload_to_cloudflare(image_path, user_id)  # Upload to Cloudflare
                        if upload_response:
                            logger.info(f"Image uploaded successfully for user {user_id}.")
                            return upload_response['result']['variants'][0]  # Return the URL of the uploaded image
                        else:
                            logger.error(f"Failed to upload profile photo for user {user_id} to Cloudflare.")
                    else:
                        logger.error(f"Failed to download profile photo from Telegram for user_id {user_id}: {response.status} - {await response.text()}.")
        else:
            logger.warning(f"User {user_id} does not have a profile photo.")
    except Exception as e:
        logger.error(f"Error while fetching user profile photo for user_id {user_id}: {e}.")
    
    return None  # Return None if no profile photo is found

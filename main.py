import os
import requests
import logging
import time
import subprocess
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

# Enable detailed logging
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    level=logging.DEBUG,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("bot.log")
    ]
)
logger = logging.getLogger(__name__)

# Your Telegram Bot Token
BOT_TOKEN = "7978226383:AAEyawAWhCKHWGiI-qVHpYSszy3c78QnCWI"

# Directory to save downloaded videos
DOWNLOAD_FOLDER = "downloads"
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

def get_download_url(terabox_link):
    api_url = f"https://tera.ashlynn.workers.dev/?url={terabox_link}"
    logger.debug(f"Attempting to fetch from API: {api_url}")
    try:
        response = requests.get(api_url, timeout=30)
        if response.status_code != 200:
            logger.error(f"API responded with status code: {response.status_code}")
            return None

        data = response.json()
        if data.get("status") == "success" and data.get("download_link", {}).get("url_1"):
            return data["download_link"]["url_1"]
        else:
            logging.error(f"API response: {data}")
            return None
    except Exception as e:
        logging.error(f"Error fetching download URL: {e}")
        return None

def download_with_wget(url, filepath, update, context):
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            # Prepare wget command with custom headers
            wget_command = [
                'wget',
                '--no-check-certificate',  # Skip SSL verification
                '--user-agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"',
                '--continue',  # Enable resume of partial downloads
                '--tries=3',  # Number of retry attempts
                '--timeout=30',  # Timeout in seconds
                '-O', filepath,  # Output file
                url
            ]
            
            # Start download process
            update.message.reply_text("⏳ Starting download with wget...")
            process = subprocess.Popen(
                wget_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            # Monitor download progress
            while True:
                output = process.stderr.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    if '%' in output:
                        # Extract progress information
                        try:
                            progress = output.strip().split()
                            for item in progress:
                                if '%' in item:
                                    update.message.reply_text(f"⏳ Download Progress: {item}")
                                    break
                        except:
                            pass

            # Check if download was successful
            if process.returncode == 0 and os.path.exists(filepath) and os.path.getsize(filepath) > 0:
                return filepath
            else:
                logger.error(f"wget download failed with return code: {process.returncode}")
                
        except Exception as e:
            logger.error(f"Download attempt {attempt + 1} failed: {e}")
            if os.path.exists(filepath):
                os.remove(filepath)
            time.sleep(3)
            
    update.message.reply_text(f"❌ Download failed after {max_retries} attempts.")
    return None

def handle_message(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id
    text = update.message.text

    if "terabox.com" in text or "1024terabox.com" in text:
        update.message.reply_text("⏳ Fetching download link, please wait...")

        download_url = get_download_url(text)
        if not download_url:
            update.message.reply_text("❌ Failed to get download link. The link may be invalid or expired.")
            return

        update.message.reply_text("🚀 Starting download...")
        
        # Create unique filename
        filename = f"video_{int(time.time())}.mp4"
        filepath = os.path.join(DOWNLOAD_FOLDER, filename)
        
        # Download using wget
        video_path = download_with_wget(download_url, filepath, update, context)

        if video_path:
            update.message.reply_text("✅ Download complete! Uploading to Telegram...")
            try:
                with open(video_path, "rb") as video:
                    context.bot.send_video(
                        chat_id=chat_id,
                        video=video,
                        caption="Here is your video! 🎥",
                        timeout=300
                    )
                    
                # Clean up
                os.remove(video_path)
            except Exception as e:
                update.message.reply_text(f"❌ Failed to upload video: {str(e)}")
                logger.error(f"Upload error: {e}")
        else:
            update.message.reply_text("❌ Failed to download the video.")
    else:
        update.message.reply_text("⚠️ Please send a valid Terabox video link.")

def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text("Welcome! Send me a Terabox video link, and I'll fetch the download for you. 🚀")

def main():
    # Check if wget is installed
    try:
        subprocess.run(['wget', '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except FileNotFoundError:
        logger.error("wget is not installed. Please install wget first.")
        return

    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()

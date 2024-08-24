import os
import nest_asyncio
import asyncio
import re
import json
import google.generativeai as gemini
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

# Get the bot token and Gemini API key from environment variables
BOT_TOKEN = os.getenv('BOT_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# Initialize the Gemini API client
gemini.configure(api_key=GEMINI_API_KEY)

async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('Hi! Send me a message with media and text.')

def generate_missing_info(file_name: str, caption: str, missing_parts: list):
    prompt = f"Generate the following missing parts for the file name and caption:\nFile Name: {file_name}\nCaption: {caption}\nMissing Parts: {', '.join(missing_parts)}"
    request = {
        "prompt": prompt,
        "temperature": 1,
        "max_output_tokens": 150
    }
    response = gemini.generate_text(**request)
    additional_info = response.result.strip()
    return additional_info

def extract_existing_parts(caption: str):
    parts = {
        "file_name": None,
        "info": None,
        "hashtags": None,
        "file_type": None,
        "price": "Free"  # Default value for price
    }
    file_name_match = re.search(r'File name:\s*(.*)', caption, re.IGNORECASE)
    info_match = re.search(r'Info:\s*(.*)', caption, re.IGNORECASE)
    hashtags_match = re.search(r'#\w+', caption)
    file_type_match = re.search(r'File type:\s*(.*)', caption, re.IGNORECASE)

    if file_name_match:
        parts["file_name"] = file_name_match.group(1).strip()
    else:
        parts["file_name"] = caption.split('\n')[0].strip()  # Assume the first line is the file name

    if info_match:
        parts["info"] = info_match.group(1).strip()
    else:
        parts["info"] = caption.split('\n')[1].strip()  # Assume the second line is the info

    if hashtags_match:
        parts["hashtags"] = ' '.join(re.findall(r'#\w+', caption))

    if file_type_match:
        parts["file_type"] = file_type_match.group(1).strip()

    return parts

async def handle_message(update: Update, context: CallbackContext) -> None:
    message = update.message
    media = None
    file_name = "Unknown"
    file_url = "https://t.me/mybot"  # URL for the "Download" button

    # Check if the message contains media
    if message.photo:
        media = message.photo[-1]
        file = await media.get_file()
        file_url = file.file_path
    elif message.video:
        media = message.video
        file_name = media.file_name or "Video"
        file = await media.get_file()
        file_url = file.file_path
    elif message.document:
        media = message.document
        file_name = media.file_name
        file = await media.get_file()
        file_url = file.file_path

    # Extract text
    caption = message.caption or message.text or "No text provided"
    existing_parts = extract_existing_parts(caption)
    missing_parts = [key for key, value in existing_parts.items() if not value]

    if missing_parts:
        additional_info = generate_missing_info(existing_parts["file_name"], caption, missing_parts)
        additional_parts = extract_existing_parts(additional_info)
        existing_parts.update({k: v for k, v in additional_parts.items() if v})

    # Ensure the original file name remains unchanged
    file_name = existing_parts["file_name"]

    # Remove the channel username if present
    file_name = re.sub(r'By\s*\(@Free3dAssets\)', '', file_name).strip()

    # Ensure the file extension is not added unless part of the original file name
    file_name = re.sub(r'\.gltf', '', file_name).strip()

    # Ensure the info section does not incorrectly state that the model is free
    info = existing_parts["info"]
    info = re.sub(r'This is a free 3D model of', 'This is a 3D model of', info)

    # Default file type to "3D-Asset" if not determined
    if not existing_parts["file_type"] or existing_parts["file_type"].lower() == "none":
        existing_parts["file_type"] = "3D-Asset"

    # Format the message with bold headings and relevant emojis
    formatted_message = (
        "**" + file_name + "**\n\n" +
        "📝 **𝐈𝐍𝐅𝐎:** " + info + "\n\n" +
        "📂 **𝐅𝐈𝐋𝐄 𝐓𝐘𝐏𝐄:** " + existing_parts['file_type'] + "\n\n" +
        "💰 **𝑷𝑹𝑰𝑪𝑬:** " + existing_parts['price'] + "\n\n" +
        "🏷️ **𝑯𝑨𝑺𝑯𝑻𝑨𝑮𝑺:**\n" + existing_parts['hashtags'].replace(' ', '\n')
    )

    # Create inline buttons
    keyboard = [
        [InlineKeyboardButton("♡︎ 𝐇𝐎𝐖 𝐓𝐎 𝐃𝐎𝐖𝐍𝐋𝐎𝐀𝐃 ♡︎", url="https://t.me/free_3d_assets")],  # Updated URL
        [InlineKeyboardButton("❤️𝐉𝐎𝐈𝐍 𝐔𝐒❤️", url="https://t.me/free_3d_assets")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Send the formatted message with the media
    if media:
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=media.file_id,
            caption=formatted_message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(formatted_message, reply_markup=reply_markup, parse_mode='Markdown')
    # Delete the original forwarded message
    await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)

def main() -> None:
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO | filters.Document.ALL, handle_message))

    # Run the bot
    application.run_polling()

if __name__ == '__main__':
    main()

import telebot
import yt_dlp
import os
from config import TELEGRAM_BOT_TOKEN

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

@bot.message_handler(commands=['start'])
def welcome(message):
    bot.send_message(message.chat.id, "👋 Send me a YouTube link and I’ll give you a download button with video details.")

@bot.message_handler(func=lambda m: 'youtube.com' in m.text or 'youtu.be' in m.text)
def handle_link(message):
    url = message.text.strip()

    ydl_opts = {'quiet': True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = info.get('formats', [])

            best_fmt = None
            for f in formats:
                if f.get("vcodec") != "none" and f.get("acodec") != "none" and f.get("height") and f["ext"] == "mp4":
                    if f['height'] <= 360:
                        best_fmt = f
                        break

            if not best_fmt:
                best_fmt = info['formats'][-1]  # fallback

            # Estimate filesize
            duration = info.get('duration', 0)
            filesize = best_fmt.get("filesize")

            if not filesize and best_fmt.get("tbr") and duration:
                bitrate_kbps = best_fmt["tbr"]
                filesize = (bitrate_kbps * 1000 / 8) * duration  # bytes

            if filesize:
                size_mb = round(filesize / (1024 * 1024), 2)
            else:
                size_mb = "Unknown"

            # Estimate download time
            if isinstance(size_mb, float):
                seconds = (size_mb * 1024) / 250
                minutes = int(seconds // 60)
                seconds = int(seconds % 60)
                est_time = f"{minutes}m {seconds}s"
            else:
                est_time = "Unknown"

            text = (
                f"🎬 *{info['title']}*\n"
                f"📏 Quality: {best_fmt.get('height')}p\n"
                f"📦 Size: {size_mb} MB\n"
                f"⏱️ Est. Time (2 Mbps): {est_time}\n\n"
                f"Click below to download:"
            )

            markup = telebot.types.InlineKeyboardMarkup()
            markup.add(telebot.types.InlineKeyboardButton("⬇️ Download Video", callback_data=url))
            bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=markup)

    except Exception as e:
        bot.send_message(message.chat.id, f"⚠️ Error: {str(e)}")

@bot.callback_query_handler(func=lambda call: True)
def download_video(call):
    url = call.data
    bot.edit_message_text("⏬ Downloading video... Please wait.", call.message.chat.id, call.message.message_id)

    ydl_opts = {
        'format': 'best[height<=360][ext=mp4]/best',
        'outtmpl': '%(title)s.%(ext)s',
        'quiet': True
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url)
            filename = ydl.prepare_filename(info)

        with open(filename, 'rb') as f:
            bot.send_video(call.message.chat.id, f, caption="✅ Here's your video!")

        os.remove(filename)

    except Exception as e:
        bot.send_message(call.message.chat.id, f"❌ Download failed: {str(e)}")

bot.infinity_polling()

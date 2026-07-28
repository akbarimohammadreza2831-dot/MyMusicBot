import telebot
import requests
import os
import asyncio
from shazamio import Shazam
import yt_dlp
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

# --- راضی کردن سرور رندر ---
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b"Bot is running!")

def run_web():
    port = int(os.environ.get("PORT", 8080))
    HTTPServer(('0.0.0.0', port), DummyHandler).serve_forever()

threading.Thread(target=run_web, daemon=True).start()
# -----------------------------

TOKEN = '8956987417:AAFkXir72fzABkCxxdAfY3gyRubB0uZLwO0'
bot = telebot.TeleBot(TOKEN)

async def recognize_song(file_path):
    shazam = Shazam()
    return await shazam.recognize(file_path)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "سلام! لینک اینستاگرام رو بده تا آهنگش رو پیدا کنم 🎶")

@bot.message_handler(func=lambda message: True)
def handle_link(message):
    url = message.text
    if 'instagram.com' not in url:
         bot.reply_to(message, "فعلا فقط لینک اینستاگرام پشتیبانی میشه.")
         return

    msg = bot.reply_to(message, "⏳ در حال استخراج ویدیو از اینستاگرام...")
    temp_audio = f"temp_{message.chat.id}.mp4"
    full_audio = f"full_{message.chat.id}"

    try:
        # استفاده از API واسطه برای دانلود از اینستاگرام (دور زدن تحریم‌های اینستاگرام)
        api_url = f"https://api.cobalt.tools/api/json"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0"
        }
        data = {"url": url}
        
        response = requests.post(api_url, json=data, headers=headers)
        response_json = response.json()

        if response_json.get("status") == "error" or "url" not in response_json:
            bot.edit_message_text("❌ نتونستم ویدیو رو دانلود کنم. پیج پرایوته یا لینک خرابه.", message.chat.id, msg.message_id)
            return
            
        video_url = response_json["url"]
        
        # دانلود فایل ویدیویی
        video_data = requests.get(video_url).content
        with open(temp_audio, 'wb') as f:
             f.write(video_data)

        bot.edit_message_text("🎧 دارم گوش می‌دم ببینم چه آهنگییه...", message.chat.id, msg.message_id)
        
        # دادن ویدیو به شازم (شازم خودش میتونه ویدیو هم بخونه)
        shazam_result = asyncio.run(recognize_song(temp_audio))
        
        if 'track' not in shazam_result:
            bot.edit_message_text("❌ هیچ آهنگی تو این ویدیو پیدا نشد!", message.chat.id, msg.message_id)
            if os.path.exists(temp_audio): os.remove(temp_audio)
            return

        track_title = shazam_result['track']['title']
        track_artist = shazam_result['track']['subtitle']
        search_query = f"{track_title} {track_artist}"

        bot.edit_message_text(f"✅ آهنگ رو شناختم: {search_query}\n📥 در حال دانلود نسخه کامل...", message.chat.id, msg.message_id)

        # پیدا کردن آهنگ کامل از یوتیوب
        ydl_opts_search = {
            'default_search': 'ytsearch1',
            'outtmpl': f"{full_audio}.%(ext)s",
            'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
            'quiet': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts_search) as ydl_search:
            ydl_search.download([search_query])
            
        full_mp3 = f"{full_audio}.mp3"
        bot.edit_message_text("📤 در حال ارسال فایل...", message.chat.id, msg.message_id)
        
        with open(full_mp3, 'rb') as audio:
            bot.send_audio(message.chat.id, audio, title=track_title, performer=track_artist)

        bot.delete_message(message.chat.id, msg.message_id)
        if os.path.exists(temp_audio): os.remove(temp_audio)
        if os.path.exists(full_mp3): os.remove(full_mp3)

    except Exception as e:
        bot.edit_message_text(f"❌ ارور:\n{str(e)}", message.chat.id, msg.message_id)
        if os.path.exists(temp_audio): os.remove(temp_audio)
        if os.path.exists(f"{full_audio}.mp3"): os.remove(f"{full_audio}.mp3")

bot.infinity_polling()

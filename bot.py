import telebot
import yt_dlp
import os
import asyncio
from shazamio import Shazam
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

# --- این بخش برای راضی کردن سرور رندر اضافه شده است ---
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b"Bot is running successfully!")

def run_web():
    port = int(os.environ.get("PORT", 8080))
    server_address = ('0.0.0.0', port)
    httpd = HTTPServer(server_address, DummyHandler)
    httpd.serve_forever()

# اجرای سرور الکی در پس‌زمینه
threading.Thread(target=run_web, daemon=True).start()
# --------------------------------------------------------

# توکن خودت رو دقیقاً بین دو تا کوتیشن پایین بذار
TOKEN = '8956987417:AAFkXir72fzABkCxxdAfY3gyRubB0uZLwO0'
bot = telebot.TeleBot(TOKEN)

async def recognize_song(file_path):
    shazam = Shazam()
    out = await shazam.recognize(file_path)
    return out

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "سلام! لینک ویدیوت رو بده تا بگردم آهنگ کامل و اصلیش رو برات پیدا کنم 🕵️‍♂️🎶")

@bot.message_handler(func=lambda message: True)
def handle_link(message):
    url = message.text
    if not url.startswith('http'):
        bot.reply_to(message, "این که لینک نیست! لطفاً یه لینک درست بفرست.")
        return

    msg = bot.reply_to(message, "⏳ دارم صدای ویدیو رو می‌گیرم تا گوشش بدم...")
    temp_audio = f"temp_{message.chat.id}"
    full_audio = f"full_{message.chat.id}"
    
    ydl_opts_snippet = {
        'format': 'bestaudio/best',
        'outtmpl': f"{temp_audio}.%(ext)s",
        'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
        'quiet': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts_snippet) as ydl:
            ydl.download([url])
        
        temp_mp3 = f"{temp_audio}.mp3"
        bot.edit_message_text("🎧 دارم تمرکز می‌کنم ببینم این چه آهنگییه...", message.chat.id, msg.message_id)
        
        shazam_result = asyncio.run(recognize_song(temp_mp3))
        
        if 'track' not in shazam_result:
            bot.edit_message_text("❌ هرچی گوش دادم نتونستم هیچ آهنگی تو این ویدیو تشخیص بدم!", message.chat.id, msg.message_id)
            if os.path.exists(temp_mp3): os.remove(temp_mp3)
            return

        track_title = shazam_result['track']['title']
        track_artist = shazam_result['track']['subtitle']
        search_query = f"{track_title} {track_artist}"

        bot.edit_message_text(f"✅ آهنگ رو شناختم!\nاسم آهنگ: {search_query}\n\n📥 حالا دارم میرم تو اینترنت نسخه کاملش رو برات دانلود کنم...", message.chat.id, msg.message_id)

        ydl_opts_search = {
            'format': 'bestaudio/best',
            'default_search': 'ytsearch1',
            'outtmpl': f"{full_audio}.%(ext)s",
            'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
            'quiet': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts_search) as ydl_search:
            ydl_search.download([search_query])
            
        full_mp3 = f"{full_audio}.mp3"
        bot.edit_message_text("📤 دانلود شد! دارم فایل رو می‌فرستم تو تلگرام...", message.chat.id, msg.message_id)
        
        with open(full_mp3, 'rb') as audio:
            bot.send_audio(message.chat.id, audio, title=track_title, performer=track_artist)

        bot.delete_message(message.chat.id, msg.message_id)
        if os.path.exists(temp_mp3): os.remove(temp_mp3)
        if os.path.exists(full_mp3): os.remove(full_mp3)

    except Exception as e:
        # تغییر در این قسمت انجام شده تا ارور انگلیسی و دقیق ارسال شود
        bot.edit_message_text(f"❌ ارور سیستم:\n{str(e)}", message.chat.id, msg.message_id)
        if os.path.exists(f"{temp_audio}.mp3"): os.remove(f"{temp_audio}.mp3")
        if os.path.exists(f"{full_audio}.mp3"): os.remove(f"{full_audio}.mp3")

bot.infinity_polling()

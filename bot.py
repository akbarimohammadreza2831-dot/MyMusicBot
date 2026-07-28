import telebot
import yt_dlp
import os
import asyncio
from shazamio import Shazam
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

# --- راضی نگه داشتن سرور رندر ---
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b"Bot is running successfully!")

def run_web():
    port = int(os.environ.get("PORT", 8080))
    HTTPServer(('0.0.0.0', port), DummyHandler).serve_forever()

threading.Thread(target=run_web, daemon=True).start()
# ---------------------------------

TOKEN = '8956987417:AAFkXir72fzABkCxxdAfY3gyRubB0uZLwO0'
bot = telebot.TeleBot(TOKEN)

async def recognize_song(file_path):
    shazam = Shazam()
    return await shazam.recognize(file_path)

def smart_download(query, outtmpl, is_search=False):
    """
    این تابع به قدری هوشمند است که اگر فرمت صدا موجود نباشد،
    خودش ویدیو را دانلود کرده و صدا را جدا می‌کند تا ارور ندهد.
    """
    base_opts = {
        'outtmpl': f"{outtmpl}.%(ext)s",
        'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3'}],
        'quiet': True,
        'cookiefile': 'cookies.txt', # استفاده از کوکی برای دور زدن گارد اینستاگرام/یوتیوب
        'nocheckcertificate': True,
    }
    if is_search:
        base_opts['default_search'] = 'ytsearch1'

    try:
        # تلاش اول: دانلود مستقیم صدا
        opts1 = base_opts.copy()
        opts1['format'] = 'bestaudio/best'
        with yt_dlp.YoutubeDL(opts1) as ydl:
            ydl.download([query])
    except Exception:
        # تلاش دوم (جلوگیری از ارور فرمت): دانلود کل فایل و استخراج صدا
        opts2 = base_opts.copy()
        opts2['format'] = 'best'
        with yt_dlp.YoutubeDL(opts2) as ydl:
            ydl.download([query])

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "سلام! لینک اینستاگرام یا یوتیوب رو بده تا آهنگش رو پیدا کنم 🕵️‍♂️🎶")

@bot.message_handler(func=lambda message: True)
def handle_link(message):
    url = message.text
    if not url.startswith('http'):
        bot.reply_to(message, "لطفاً یک لینک معتبر بفرست.")
        return

    msg = bot.reply_to(message, "⏳ در حال دانلود و استخراج صدا...")
    temp_audio = f"temp_{message.chat.id}"
    full_audio = f"full_{message.chat.id}"

    try:
        # ۱. دانلود از لینک ارسالی (اینستا یا یوتیوب)
        smart_download(url, temp_audio, is_search=False)
        temp_mp3 = f"{temp_audio}.mp3"
        
        bot.edit_message_text("🎧 دارم گوش می‌دم ببینم چه آهنگییه...", message.chat.id, msg.message_id)
        
        # ۲. ارسال به شازم
        shazam_result = asyncio.run(recognize_song(temp_mp3))
        
        if 'track' not in shazam_result:
            bot.edit_message_text("❌ هیچ آهنگی تو این ویدیو تشخیص داده نشد!", message.chat.id, msg.message_id)
            return

        track_title = shazam_result['track']['title']
        track_artist = shazam_result['track']['subtitle']
        search_query = f"{track_title} {track_artist}"

        bot.edit_message_text(f"✅ آهنگ رو شناختم: {search_query}\n📥 در حال جستجو و دانلود نسخه کامل...", message.chat.id, msg.message_id)

        # ۳. جستجو و دانلود نسخه کامل
        smart_download(search_query, full_audio, is_search=True)
        full_mp3 = f"{full_audio}.mp3"
        
        bot.edit_message_text("📤 در حال ارسال فایل به تلگرام...", message.chat.id, msg.message_id)
        
        with open(full_mp3, 'rb') as audio:
            bot.send_audio(message.chat.id, audio, title=track_title, performer=track_artist)

        bot.delete_message(message.chat.id, msg.message_id)
        
    except Exception as e:
        bot.edit_message_text(f"❌ ارور سیستم:\nاحتمالاً فایل کوکی (cookies.txt) منقضی شده یا لینک پرایوت است.", message.chat.id, msg.message_id)
        
    finally:
        # پاکسازی فایل‌های اضافه از روی سرور
        if os.path.exists(f"{temp_audio}.mp3"): os.remove(f"{temp_audio}.mp3")
        if os.path.exists(f"{full_audio}.mp3"): os.remove(f"{full_audio}.mp3")

bot.infinity_polling()

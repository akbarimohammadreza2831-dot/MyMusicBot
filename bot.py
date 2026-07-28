import telebot
import yt_dlp
import os
import asyncio
from shazamio import Shazam
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading

class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running successfully!")

def run_web():
    port = int(os.environ.get("PORT", 8080))
    HTTPServer(('0.0.0.0', port), DummyHandler).serve_forever()

threading.Thread(target=run_web, daemon=True).start()

TOKEN = '8956987417:AAFkXir72fzABkCxxdAfY3gyRubB0uZLwO0'
bot = telebot.TeleBot(TOKEN)

async def recognize_song(file_path):
    shazam = Shazam()
    return await shazam.recognize(file_path)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "سلام! لینک اینستاگرام یا یوتیوب رو بده تا آهنگش رو پیدا کنم 🕵️‍♂️🎶")

@bot.message_handler(func=lambda message: True)
def handle_link(message):
    url = message.text
    if not url.startswith('http'):
        bot.reply_to(message, "لطفاً یک لینک معتبر بفرست.")
        return

    msg = bot.reply_to(message, "⏳ در حال دانلود ویدیو...")
    temp_audio = f"temp_{message.chat.id}"
    full_audio = f"full_{message.chat.id}"
    temp_mp3 = f"{temp_audio}.mp3"
    full_mp3 = f"{full_audio}.mp3"

    # مرحله ۱: دانلود از لینک اصلی (با استفاده از کوکی)
    try:
        opts = {
            'outtmpl': f"{temp_audio}.%(ext)s",
            'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3'}],
            'quiet': True,
            'cookiefile': 'cookies.txt',
            'format': 'bestaudio/best'
        }
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])
        except:
            opts['format'] = 'best'
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])
    except Exception as e:
        bot.edit_message_text("❌ نتونستم ویدیو رو دانلود کنم. احتمالاً کشوری که سرور توشه توسط اینستاگرام لیمیت شده.", message.chat.id, msg.message_id)
        return

    # مرحله ۲: شناسایی آهنگ
    bot.edit_message_text("🎧 دارم گوش می‌دم ببینم چه آهنگییه...", message.chat.id, msg.message_id)
    try:
        shazam_result = asyncio.run(recognize_song(temp_mp3))
        if 'track' not in shazam_result:
            bot.edit_message_text("❌ هیچ آهنگی تو این ویدیو تشخیص داده نشد!", message.chat.id, msg.message_id)
            if os.path.exists(temp_mp3): os.remove(temp_mp3)
            return
    except Exception as e:
        bot.edit_message_text("❌ ارور در ارتباط با سرور شازم.", message.chat.id, msg.message_id)
        if os.path.exists(temp_mp3): os.remove(temp_mp3)
        return

    track_title = shazam_result['track']['title']
    track_artist = shazam_result['track']['subtitle']
    search_query = f"{track_title} {track_artist}"

    bot.edit_message_text(f"✅ آهنگ رو شناختم: {search_query}\n📥 در حال دانلود نسخه کامل...", message.chat.id, msg.message_id)

    # مرحله ۳: جستجو و دانلود نسخه کامل (بدون کوکی برای جلوگیری از مسدود شدن)
    try:
        search_opts = {
            'default_search': 'ytsearch1',
            'outtmpl': f"{full_audio}.%(ext)s",
            'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3'}],
            'quiet': True,
            'format': 'bestaudio/best'
            # حذف کوکی از اینجا تا یوتیوب به جستجوی ما گیر ندهد
        }
        try:
            with yt_dlp.YoutubeDL(search_opts) as ydl_search:
                ydl_search.download([search_query])
        except:
            search_opts['format'] = 'best'
            with yt_dlp.YoutubeDL(search_opts) as ydl_search:
                ydl_search.download([search_query])
    except Exception as e:
        bot.edit_message_text(f"❌ آهنگ '{search_query}' پیدا شد، اما نتونستم فایلش رو از یوتیوب استخراج کنم.", message.chat.id, msg.message_id)
        if os.path.exists(temp_mp3): os.remove(temp_mp3)
        return
        
    # مرحله ۴: ارسال به کاربر
    bot.edit_message_text("📤 در حال ارسال فایل به تلگرام...", message.chat.id, msg.message_id)
    try:
        with open(full_mp3, 'rb') as audio:
            bot.send_audio(message.chat.id, audio, title=track_title, performer=track_artist)
        bot.delete_message(message.chat.id, msg.message_id)
    except:
        bot.edit_message_text("❌ تو ارسال فایل به تلگرام مشکل پیش اومد.", message.chat.id, msg.message_id)
        
    # پاکسازی نهایی
    if os.path.exists(temp_mp3): os.remove(temp_mp3)
    if os.path.exists(full_mp3): os.remove(full_mp3)

bot.infinity_polling()

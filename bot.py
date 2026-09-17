import os
import json
import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
from dotenv import load_dotenv

from gemini_translator import translate_text, translate_with_langs

load_dotenv(override=True)

API_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
WEBAPP_URL = os.getenv('WEBAPP_URL', 'https://example.com/')

if not API_TOKEN or API_TOKEN == "bu_yerga_telegram_tokenni_yozing":
    raise ValueError("TELEGRAM_BOT_TOKEN topilmadi!")

bot = telebot.TeleBot(API_TOKEN)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    web_app = WebAppInfo(url=WEBAPP_URL)
    markup.add(KeyboardButton(text="🔥 Yangi Tarjimon", web_app=web_app))
    
    salom_matn = (
        "👋 Salom! Men **Aqlli Tilshunos (Linguist)** botman.\n\n"
        "Menga istalgan so'z yoki gapni yuboring. O'zbek tiliga yoki siz xohlagan tillar orasida "
        "tarjima qilib beraman.\n\n"
        "Pastdagi **🔥 Yangi Tarjimon** tugmasini bosib, tillarni o'zingiz tanlashingiz ham mumkin."
    )
    bot.reply_to(message, salom_matn, reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(content_types=['web_app_data'])
def web_app_data_handler(message):
    try:
        data = json.loads(message.web_app_data.data)
        if data.get('action') == 'translate':
            source = data.get('sourceLang')
            target = data.get('targetLang')
            text = data.get('text')
            
            wait_msg = bot.send_message(message.chat.id, f"⏳ Tarjima qilinmoqda...")
            translation = translate_with_langs(text, source, target)
            bot.edit_message_text(translation, chat_id=message.chat.id, message_id=wait_msg.message_id, parse_mode="Markdown")
            
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Xatolik yuz berdi: {e}")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    text = message.text
    if not text:
        return
        
    wait_msg = bot.send_message(message.chat.id, "⏳ Sun'iy intellekt tarjima qilmoqda...")
    try:
        translation = translate_text(text)
        bot.edit_message_text(translation, chat_id=message.chat.id, message_id=wait_msg.message_id, parse_mode="Markdown")
    except Exception as e:
        bot.edit_message_text("❌ Xatolik yuz berdi.", chat_id=message.chat.id, message_id=wait_msg.message_id)

# --- Cloud Serverlar uchun Dummy Web Server ---
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b"Bot ishladi!")

def run_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), DummyHandler)
    server.serve_forever()

if __name__ == '__main__':
    # Serverni alohida oqimda ishga tushirish (Render va boshqalar uchun kerak)
    threading.Thread(target=run_dummy_server, daemon=True).start()
    
    print("Bot ishga tushdi!")
    bot.infinity_polling()

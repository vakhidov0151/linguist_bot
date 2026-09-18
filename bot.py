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

from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

# ... (other code remains the same, assuming imports are at top)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = InlineKeyboardMarkup()
    web_app = WebAppInfo(url=WEBAPP_URL)
    
    # 1-qator: To'liq ekranli Mini App tugmasi
    markup.add(InlineKeyboardButton(text="🚀 Open Mini App", web_app=web_app))
    
    # 2-qator: Tillar tugmalari
    markup.row(
        InlineKeyboardButton(text="🇺🇿 O'zbek", callback_data="lang_uz"),
        InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en"),
        InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru")
    )
    
    salom_matn = (
        "👋 Salom! Men — **Aqlli Tilshunos (Linguist)** botman.\n\n"
        "Menga istalgan so'z yoki gapni yuboring. Men uni nafaqat tarjima qilaman, "
        "balki darajasi, boshqa ma'nolari va misollar bilan chuqur tahlil qilib beraman! 🎯\n\n"
        "Pastdagi tugmalar orqali Mini Appni ochishingiz yoki tilni tanlashingiz mumkin."
    )
    bot.reply_to(message, salom_matn, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith('lang_'))
def handle_language_selection(call):
    langs = {
        'lang_uz': "🇺🇿 O'zbek tili tanlandi!",
        'lang_en': "🇬🇧 English selected!",
        'lang_ru': "🇷🇺 Выбран русский язык!"
    }
    bot.answer_callback_query(call.id, langs.get(call.data, "Tanlandi"))
    bot.send_message(call.message.chat.id, langs.get(call.data, "Tanlandi"))

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
        bot.edit_message_text(f"❌ Xatolik yuz berdi: {str(e)}", chat_id=message.chat.id, message_id=wait_msg.message_id)

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

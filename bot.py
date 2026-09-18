import os
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from dotenv import load_dotenv

from gemini_translator import translate_text, translate_with_langs

load_dotenv(override=True)

API_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
WEBAPP_URL = os.getenv('WEBAPP_URL', 'https://example.com/')
CHANNEL_USERNAME = "@amaliysanatjilosi"

if not API_TOKEN or API_TOKEN == "bu_yerga_telegram_tokenni_yozing":
    raise ValueError("TELEGRAM_BOT_TOKEN topilmadi!")

bot = telebot.TeleBot(API_TOKEN)

# Obunani tekshirish funksiyasi
def check_subscription(user_id):
    try:
        status = bot.get_chat_member(CHANNEL_USERNAME, user_id).status
        return status in ['member', 'administrator', 'creator']
    except Exception as e:
        # Agar bot kanalga admin qilinmagan bo'lsa, xato berishi mumkin.
        return False

# A'zo bo'lishni so'rash menyusi
def send_subscription_warning(chat_id):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(text="📢 Kanalga a'zo bo'lish", url=f"https://t.me/{CHANNEL_USERNAME[1:]}"))
    markup.add(InlineKeyboardButton(text="🔄 Tasdiqlash", callback_data="check_sub_callback"))
    
    msg = (
        "🛑 **Botdan foydalanish uchun avval homiy kanalimizga a'zo bo'lishingiz kerak!**\n\n"
        "1. Pastdagi tugma orqali kanalga a'zo bo'ling.\n"
        "2. Keyin **'Tasdiqlash'** tugmasini bosing."
    )
    bot.send_message(chat_id, msg, reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(commands=['start'])
def send_welcome(message):
    # Majburiy obunani tekshiramiz
    if not check_subscription(message.from_user.id):
        send_subscription_warning(message.chat.id)
        return

    markup = InlineKeyboardMarkup()
    web_app = WebAppInfo(url=WEBAPP_URL)
    
    markup.add(InlineKeyboardButton(text="🚀 Open Mini App", web_app=web_app))
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

@bot.callback_query_handler(func=lambda call: call.data == "check_sub_callback")
def handle_sub_check(call):
    if check_subscription(call.from_user.id):
        bot.answer_callback_query(call.id, "✅ Rahmat! A'zolik tasdiqlandi. Botdan bemalol foydalanishingiz mumkin.")
        bot.delete_message(call.message.chat.id, call.message.message_id)
        send_welcome(call.message) # Asosiy menyuni ko'rsatamiz
    else:
        bot.answer_callback_query(call.id, "❌ Hali a'zo bo'lmadingiz! Iltimos, kanalga qo'shiling.", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data.startswith('lang_'))
def handle_language_selection(call):
    if not check_subscription(call.from_user.id):
        send_subscription_warning(call.message.chat.id)
        return

    langs = {
        'lang_uz': "🇺🇿 O'zbek tili tanlandi!",
        'lang_en': "🇬🇧 English selected!",
        'lang_ru': "🇷🇺 Выбран русский язык!"
    }
    bot.answer_callback_query(call.id, langs.get(call.data, "Tanlandi"))
    bot.send_message(call.message.chat.id, langs.get(call.data, "Tanlandi"))

@bot.message_handler(content_types=['web_app_data'])
def web_app_data_handler(message):
    if not check_subscription(message.from_user.id):
        send_subscription_warning(message.chat.id)
        return

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
        bot.send_message(message.chat.id, f"❌ Xatolik yuz berdi: {str(e)}")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    text = message.text
    if not text:
        return
        
    if not check_subscription(message.from_user.id):
        send_subscription_warning(message.chat.id)
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
    threading.Thread(target=run_dummy_server, daemon=True).start()
    print("Bot ishga tushdi!")
    bot.infinity_polling()

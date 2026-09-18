import os
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from dotenv import load_dotenv

from gemini_translator import translate_text, translate_audio

load_dotenv(override=True)

API_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
WEBAPP_URL = os.getenv('WEBAPP_URL', 'https://example.com/')
CHANNEL_USERNAME = "@amaliysanatjilosi"

if not API_TOKEN or API_TOKEN == "bu_yerga_telegram_tokenni_yozing":
    raise ValueError("TELEGRAM_BOT_TOKEN topilmadi!")

bot = telebot.TeleBot(API_TOKEN)

# Foydalanuvchi tillarini saqlash (oddiy dictionary)
user_langs = {}

LANGUAGES = {
    'uz': "🇺🇿 O'zbek",
    'en': "🇬🇧 English",
    'ru': "🇷🇺 Русский",
    'ar': "🇸🇦 العربية",
    'zh': "🇨🇳 中文",
    'ko': "🇰🇷 한국어",
    'it': "🇮🇹 Italiano",
    'de': "🇩🇪 Deutsch",
    'fr': "🇫🇷 Français",
    'es': "🇪🇸 Español",
    'ja': "🇯🇵 日本語"
}

def get_user_lang(user_id):
    return LANGUAGES.get(user_langs.get(user_id, 'uz'), "O'zbek")

# Obunani tekshirish funksiyasi
def check_subscription(user_id):
    try:
        status = bot.get_chat_member(CHANNEL_USERNAME, user_id).status
        return status in ['member', 'administrator', 'creator']
    except Exception as e:
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
    if not check_subscription(message.from_user.id):
        send_subscription_warning(message.chat.id)
        return

    markup = InlineKeyboardMarkup()
    web_app = WebAppInfo(url=WEBAPP_URL)
    
    markup.add(InlineKeyboardButton(text="🚀 Open Mini App", web_app=web_app))
    
    # Barcha 11 ta tilni 2 tadan qator qilib joylash
    lang_keys = list(LANGUAGES.keys())
    for i in range(0, len(lang_keys), 2):
        row = []
        for j in range(2):
            if i + j < len(lang_keys):
                code = lang_keys[i+j]
                # Tanlangan til oldida belgi bo'lishi mumkin, lekin oddiy holatda nomi chiqadi
                btn_text = LANGUAGES[code]
                if user_langs.get(message.from_user.id, 'uz') == code:
                    btn_text = "✅ " + btn_text
                row.append(InlineKeyboardButton(text=btn_text, callback_data=f"lang_{code}"))
        markup.row(*row)
    
    current_lang = get_user_lang(message.from_user.id)
    salom_matn = (
        f"👋 Salom! Men — **Aqlli Tilshunos (Linguist)** botman.\n\n"
        f"Hozirgi tarjima tili: **{current_lang}**\n\n"
        "Menga istalgan so'z, gap yoki ovozli xabar yuboring. Men uni ushbu tilga tarjima qilaman va tahlil qilib beraman! 🎯\n\n"
        "Pastdagi tugmalar orqali tilni almashtirishingiz mumkin."
    )
    bot.reply_to(message, salom_matn, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "check_sub_callback")
def handle_sub_check(call):
    if check_subscription(call.from_user.id):
        bot.answer_callback_query(call.id, "✅ Rahmat! A'zolik tasdiqlandi.")
        bot.delete_message(call.message.chat.id, call.message.message_id)
        send_welcome(call.message)
    else:
        bot.answer_callback_query(call.id, "❌ Hali a'zo bo'lmadingiz!", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data.startswith('lang_'))
def handle_language_selection(call):
    if not check_subscription(call.from_user.id):
        send_subscription_warning(call.message.chat.id)
        return

    lang_code = call.data.split('_')[1]
    if lang_code in LANGUAGES:
        user_langs[call.from_user.id] = lang_code
        bot.answer_callback_query(call.id, f"{LANGUAGES[lang_code]} tanlandi!")
        
        # Menyuni yangilash (✅ belgisi tushishi uchun)
        send_welcome(call.message)

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
            
            # Mini appdagi target tilini olamiz
            target_lang_str = target if target else "O'zbek"
            
            wait_msg = bot.send_message(message.chat.id, f"⏳ Tarjima qilinmoqda...")
            # Mini Appdan kelgan matnni to'g'ridan to'g'ri translate_text ga yuboramiz
            translation = translate_text(f"(Bu matn {source} tilidan kiritildi): {text}", target_lang=target_lang_str)
            bot.edit_message_text(translation, chat_id=message.chat.id, message_id=wait_msg.message_id, parse_mode="Markdown")
            
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Xatolik yuz berdi: {str(e)}")

@bot.message_handler(content_types=['voice'])
def handle_voice(message):
    if not check_subscription(message.from_user.id):
        send_subscription_warning(message.chat.id)
        return
        
    wait_msg = bot.send_message(message.chat.id, "🎤 Ovozli xabar eshitilmoqda...")
    try:
        file_info = bot.get_file(message.voice.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        target_lang = get_user_lang(message.from_user.id)
        translation = translate_audio(downloaded_file, target_lang=target_lang)
        bot.edit_message_text(translation, chat_id=message.chat.id, message_id=wait_msg.message_id, parse_mode="Markdown")
    except Exception as e:
        bot.edit_message_text(f"❌ Ovozni tarjima qilishda xatolik yuz berdi: {str(e)}", chat_id=message.chat.id, message_id=wait_msg.message_id)

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
        target_lang = get_user_lang(message.from_user.id)
        translation = translate_text(text, target_lang=target_lang)
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

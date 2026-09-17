import os
import json
import logging
import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
from dotenv import load_dotenv

from gemini_translator import translate_text, translate_with_langs

load_dotenv(override=True)

API_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
WEBAPP_URL = os.getenv('WEBAPP_URL', 'https://example.com/')

if not API_TOKEN or API_TOKEN == "bu_yerga_telegram_tokenni_yozing":
    raise ValueError("TELEGRAM_BOT_TOKEN topilmadi!")

# Markdown o'rniga ba'zan MarkdownV2 kerak bo'lishi mumkin, lekin Gemini oddiy Markdown qaytaradi.
bot = telebot.TeleBot(API_TOKEN)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    web_app = WebAppInfo(url=WEBAPP_URL)
    markup.add(KeyboardButton(text="🔥 Yangi Tarjimon", web_app=web_app))
    
    salom_matn = (
        "👋 Salom! Men **Aqlli Tilshunos (Linguist)** botman.\n\n"
        "Menga istalgan so'z yoki gapni yuboring. O'zbek tiliga yoki siz xohlagan tillar orasida "
        "(masalan, *ruschadan xitoychaga, koreyschadan ispanchaga*) tarjima qilib beraman.\n\n"
        "Men shunchaki tarjima qilmayman, balki so'zning darajasi, boshqa ma'nolari va misollar bilan "
        "chuqur tahlil qilib beraman! 🎯\n\n"
        "Pastdagi **📱 Mini App** tugmasini bosib, tillarni o'zingiz tanlashingiz ham mumkin."
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
            
            wait_msg = bot.send_message(message.chat.id, f"⏳ Mini App orqali tarjima qilinmoqda ({source} -> {target})...")
            
            translation = translate_with_langs(text, source, target)
            bot.edit_message_text(translation, chat_id=message.chat.id, message_id=wait_msg.message_id, parse_mode="Markdown")
            
    except Exception as e:
        logging.error(f"WebApp Error: {e}")
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
        logging.error(f"Translation Error: {e}")
        bot.edit_message_text("❌ Xatolik yuz berdi. Iltimos keyinroq qayta urinib ko'ring.", chat_id=message.chat.id, message_id=wait_msg.message_id)

if __name__ == '__main__':
    print("Bot ishga tushdi!")
    bot.infinity_polling()

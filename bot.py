import os
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo, LabeledPrice
from dotenv import load_dotenv

from gemini_translator import translate_text, translate_audio
from database import get_voice_balance, add_voice_balance, use_voice_balance

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

# Tariflar (To'lov menyusi)
def send_tariff_menu(chat_id):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(text="🌟 100 ta xabar (99 ⭐)", callback_data="buy_package_100"))
    markup.add(InlineKeyboardButton(text="🌟 1000 ta xabar (999 ⭐)", callback_data="buy_package_1000"))
    markup.add(InlineKeyboardButton(text="💳 Karta orqali (P2P)", callback_data="buy_p2p"))
    
    msg = (
        "🎙 **Ovozli xabarlarni tarjima qilish pullik.**\n\n"
        "Ovozli xabarlarni cheklovsiz yuborish uchun quyidagi paketlardan birini xarid qiling:"
    )
    bot.send_message(chat_id, msg, reply_markup=markup, parse_mode="Markdown")

# Chek yuborishni kutayotgan foydalanuvchilar holati
waiting_for_receipt = {}
ADMIN_ID = os.getenv('ADMIN_ID', 'Sizning_Telegram_ID_raqamingizni_shu_yerga_yozing') # Masalan: 123456789

@bot.message_handler(commands=['start'])
def send_welcome(message):
    if not check_subscription(message.from_user.id):
        send_subscription_warning(message.chat.id)
        return

    # Holatni tozalash
    if message.chat.id in waiting_for_receipt:
        del waiting_for_receipt[message.chat.id]

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
                btn_text = LANGUAGES[code]
                if user_langs.get(message.from_user.id, 'uz') == code:
                    btn_text = "✅ " + btn_text
                row.append(InlineKeyboardButton(text=btn_text, callback_data=f"lang_{code}"))
        markup.row(*row)
    
    # Balansni ko'rsatuvchi tugma
    balance = get_voice_balance(message.from_user.id)
    markup.row(InlineKeyboardButton(text=f"💳 Ovozli xabar balansi: {balance} ta", callback_data="show_balance"))
    
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

@bot.callback_query_handler(func=lambda call: call.data == "show_balance")
def handle_show_balance(call):
    balance = get_voice_balance(call.from_user.id)
    bot.answer_callback_query(call.id, f"Sizning hisobingizda {balance} ta ovozli xabar limiti bor.", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "buy_p2p")
def handle_buy_p2p(call):
    card_info = os.getenv('CARD_INFO', '8600 0000 0000 0000 (Ism Familiya)')
    msg = (
        "💳 **Karta orqali to'lov (P2P)**\n\n"
        "To'lovni quyidagi raqamga o'tkazing:\n"
        f"💳 Karta: `{card_info}`\n\n"
        "**Narxlar:**\n"
        "🔹 100 ta ovozli xabar — 10,000 so'm\n"
        "🔹 1000 ta ovozli xabar — 90,000 so'm\n\n"
        "To'lovni amalga oshirgach, **Chekni (Skrinshotni)** aynan shu yerga yuboring! Men uni adminga yuboraman."
    )
    waiting_for_receipt[call.from_user.id] = True
    bot.edit_message_text(msg, chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith('buy_package_'))
def handle_buy_package(call):
    package_type = call.data.split('_')[2]
    
    if package_type == "100":
        title = "100 ta Ovozli Tarjima"
        description = "Sun'iy intellekt orqali 100 ta ovozli xabarni yuqori aniqlikda tarjima qilish paketi."
        price = 99
        payload = "voice_pkg_100"
    elif package_type == "1000":
        title = "1000 ta Ovozli Tarjima"
        description = "Sun'iy intellekt orqali 1000 ta ovozli xabarni yuqori aniqlikda tarjima qilish paketi."
        price = 999
        payload = "voice_pkg_1000"
    else:
        return

    prices = [LabeledPrice(label=title, amount=price)]

    bot.send_invoice(
        call.message.chat.id,
        title=title,
        description=description,
        invoice_payload=payload,
        provider_token="", # Telegram Stars uchun bo'sh qoldiriladi
        currency="XTR",
        prices=prices
    )
    bot.answer_callback_query(call.id)

@bot.pre_checkout_query_handler(func=lambda query: True)
def checkout(pre_checkout_query):
    bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True, error_message="To'lovda xatolik yuz berdi. Qaytadan urinib ko'ring.")

@bot.message_handler(content_types=['successful_payment'])
def got_payment(message):
    payload = message.successful_payment.invoice_payload
    if payload == "voice_pkg_100":
        add_voice_balance(message.from_user.id, 100)
        bot.send_message(message.chat.id, "🎉 To'lov muvaffaqiyatli amalga oshirildi!\nHisobingizga **100 ta ovozli xabar** qo'shildi.")
    elif payload == "voice_pkg_1000":
        add_voice_balance(message.from_user.id, 1000)
        bot.send_message(message.chat.id, "🎉 To'lov muvaffaqiyatli amalga oshirildi!\nHisobingizga **1000 ta ovozli xabar** qo'shildi.")
        
    # Balansni ko'rsatish
    send_welcome(message)

# Admin tomonidan P2P to'lovni tasdiqlash
@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_approve_') or call.data.startswith('admin_reject_'))
def handle_admin_decision(call):
    if str(call.from_user.id) != str(ADMIN_ID) and ADMIN_ID != 'Sizning_Telegram_ID_raqamingizni_shu_yerga_yozing':
        bot.answer_callback_query(call.id, "Siz admin emassiz!", show_alert=True)
        return

    data_parts = call.data.split('_')
    action = data_parts[1] # approve yoki reject
    user_id = int(data_parts[2])
    
    if action == "approve":
        amount = int(data_parts[3])
        add_voice_balance(user_id, amount)
        bot.edit_message_caption(f"✅ Tasdiqlandi! Foydalanuvchiga {amount} ta limit qo'shildi.", chat_id=call.message.chat.id, message_id=call.message.message_id)
        bot.send_message(user_id, f"🎉 Admin to'lovingizni tasdiqladi! Hisobingizga **{amount} ta ovozli xabar** qo'shildi.")
    elif action == "reject":
        bot.edit_message_caption("❌ Rad etildi.", chat_id=call.message.chat.id, message_id=call.message.message_id)
        bot.send_message(user_id, "❌ To'lovingiz admin tomonidan rad etildi. Iltimos tekshirib qaytadan urinib ko'ring.")

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

@bot.message_handler(content_types=['photo', 'document'])
def handle_receipt(message):
    if waiting_for_receipt.get(message.from_user.id):
        if str(ADMIN_ID) == 'Sizning_Telegram_ID_raqamingizni_shu_yerga_yozing':
            bot.send_message(message.chat.id, "Hozircha admin ID sozlanmagan. Iltimos dasturchiga murojaat qiling.")
            return
            
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("✅ 100 ta qo'shish", callback_data=f"admin_approve_{message.from_user.id}_100"))
        markup.add(InlineKeyboardButton("✅ 1000 ta qo'shish", callback_data=f"admin_approve_{message.from_user.id}_1000"))
        markup.add(InlineKeyboardButton("❌ Rad etish", callback_data=f"admin_reject_{message.from_user.id}"))
        
        caption = f"💸 Yangi to'lov (Karta orqali)\n👤 Foydalanuvchi: {message.from_user.first_name} (ID: {message.from_user.id})\n\nIltimos to'lovni tekshirib, quyidagilardan birini tanlang:"
        
        try:
            if message.photo:
                bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=caption, reply_markup=markup)
            elif message.document:
                bot.send_document(ADMIN_ID, message.document.file_id, caption=caption, reply_markup=markup)
                
            bot.send_message(message.chat.id, "✅ Chek qabul qilindi. Adminga yuborildi. Tasdiqlanishi bilan sizga xabar beramiz!")
            del waiting_for_receipt[message.from_user.id]
        except Exception as e:
            bot.send_message(message.chat.id, f"Adminga yuborishda xatolik: {e}")
    else:
        # Agar oddiy holatda rasm yuborsa hech narsa qilmaslik mumkin yoki...
        pass

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
            
            target_lang_str = target if target else "O'zbek"
            
            wait_msg = bot.send_message(message.chat.id, f"⏳ Tarjima qilinmoqda...")
            translation = translate_text(f"(Bu matn {source} tilidan kiritildi): {text}", target_lang=target_lang_str)
            bot.edit_message_text(translation, chat_id=message.chat.id, message_id=wait_msg.message_id, parse_mode="Markdown")
            
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Xatolik yuz berdi: {str(e)}")

@bot.message_handler(content_types=['voice'])
def handle_voice(message):
    if not check_subscription(message.from_user.id):
        send_subscription_warning(message.chat.id)
        return
        
    # Balansni tekshiramiz
    if not use_voice_balance(message.from_user.id):
        send_tariff_menu(message.chat.id)
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
        # Xato bo'lsa bitta limitni qaytarib qo'yamiz
        add_voice_balance(message.from_user.id, 1)

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

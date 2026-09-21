import os
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo, LabeledPrice
from dotenv import load_dotenv

from gemini_translator import translate_text, translate_audio
from database import (
    get_voice_balance, add_voice_balance, use_voice_balance,
    increment_translations, get_user_stats, set_interface_lang, get_interface_lang,
    set_referrer, get_all_users, get_total_user_count, register_user
)

load_dotenv(override=True)

API_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
WEBAPP_URL = os.getenv('WEBAPP_URL', 'https://example.com/')
CHANNEL_USERNAME = "@amaliysanatjilosi"
ADMIN_ID = os.getenv('ADMIN_ID', 'Sizning_Telegram_ID_raqamingizni_shu_yerga_yozing')

if not API_TOKEN or API_TOKEN == "bu_yerga_telegram_tokenni_yozing":
    raise ValueError("TELEGRAM_BOT_TOKEN topilmadi!")

bot = telebot.TeleBot(API_TOKEN)
bot_info = bot.get_me()
BOT_USERNAME = bot_info.username

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

# --- UI MATNLARI (INTERFEYS TILLARI) ---
UI_TEXTS = {
    'uz': {
        'sub_warning': "🛑 **Botdan foydalanish uchun avval homiy kanalimizga a'zo bo'lishingiz kerak!**\n\n1. Pastdagi tugma orqali kanalga a'zo bo'ling.\n2. Keyin **'Tasdiqlash'** tugmasini bosing.",
        'btn_join': "📢 Kanalga a'zo bo'lish",
        'btn_verify': "🔄 Tasdiqlash",
        'sub_success': "✅ Rahmat! A'zolik tasdiqlandi.",
        'sub_fail': "❌ Hali a'zo bo'lmadingiz!",
        'btn_webapp': "🚀 Open Mini App",
        'btn_profile': "👤 Mening Profilim",
        'btn_interface_lang': "🌐 Interfeys tili",
        'welcome': "👋 Salom! Men — **Aqlli Tilshunos (Linguist)** botman.\n\nHozirgi tarjima tili: **{lang}**\n\nMenga istalgan so'z, gap yoki ovozli xabar yuboring. Men uni ushbu tilga tarjima qilaman va tahlil qilib beraman! 🎯",
        'profile_text': "👤 **Sizning Profilingiz:**\n\n🆔 ID raqamingiz: `{user_id}`\n🌐 Interfeys tili: {ui_lang}\n💳 Ovozli xabar balansi: **{balance} ta**\n📊 Jami tarjimalaringiz: **{total_trans} ta**\n👥 Taklif qilgan do'stlaringiz: **{refs} ta**\n\n🔗 **Sizning Taklif Ssilkangiz (Referal):**\n`https://t.me/{bot_user}?start=ref{user_id}`\n\n*Ushbu ssilkani do'stlaringizga yuboring. Ular botga kirishsa, sizga avtomat 5 ta Bepul Ovozli tarjima limiti qo'shiladi!*",
        'btn_share': "↗️ Do'stlarga Ulashish",
        'tariff_msg': "🎙 **Ovozli xabarlarni tarjima qilish pullik.**\n\nCheklovsiz yuborish uchun paket xarid qiling yoki taklif ssilkangiz orqali do'stlaringizni taklif qilib tekin limit oling!",
        'card_info': "💳 **Karta orqali to'lov (P2P)**\n\nTo'lovni quyidagi raqamga o'tkazing:\n💳 Karta: `{card}`\n\n**Narxlar:**\n🔹 100 ta ovozli xabar — 10,000 so'm\n🔹 1000 ta ovozli xabar — 90,000 so'm\n\nTo'lov qilib chekni shu yerga yuboring!",
        'translating': "⏳ Tarjima qilinmoqda...",
        'voice_listening': "🎤 Ovozli xabar eshitilmoqda...",
        'error': "❌ Xatolik yuz berdi: {err}",
        'new_referral': "🎉 Tabriklaymiz! Sizning taklifingiz bilan do'stingiz botga qo'shildi!\nSizga **5 ta Bepul Ovozli xabar** limiti sovg'a qilindi! 🎁"
    },
    'ru': {
        'sub_warning': "🛑 **Для использования бота подпишитесь на наш канал!**\n\n1. Подпишитесь по кнопке ниже.\n2. Нажмите **'Подтвердить'**.",
        'btn_join': "📢 Подписаться",
        'btn_verify': "🔄 Подтвердить",
        'sub_success': "✅ Спасибо! Подписка подтверждена.",
        'sub_fail': "❌ Вы еще не подписались!",
        'btn_webapp': "🚀 Open Mini App",
        'btn_profile': "👤 Мой Профиль",
        'btn_interface_lang': "🌐 Язык интерфейса",
        'welcome': "👋 Привет! Я — **Умный Лингвист (Linguist)**.\n\nТекущий язык перевода: **{lang}**\n\nОтправьте мне текст или голосовое сообщение, и я переведу его! 🎯",
        'profile_text': "👤 **Ваш Профиль:**\n\n🆔 Ваш ID: `{user_id}`\n🌐 Язык: {ui_lang}\n💳 Баланс голосовых: **{balance} шт**\n📊 Всего переводов: **{total_trans} шт**\n👥 Приглашенных друзей: **{refs} чел**\n\n🔗 **Ваша реферальная ссылка:**\n`https://t.me/{bot_user}?start=ref{user_id}`\n\n*Отправьте эту ссылку друзьям. Если они зайдут, вы получите 5 бесплатных голосовых переводов!*",
        'btn_share': "↗️ Поделиться с друзьями",
        'tariff_msg': "🎙 **Голосовые переводы платные.**\n\nКупите пакет или пригласите друзей по вашей ссылке для получения бесплатных лимитов!",
        'card_info': "💳 **Оплата картой (P2P)**\n\nПереведите на:\n💳 Карта: `{card}`\n\n**Цены:**\n🔹 100 переводов — 10,000 сум\n🔹 1000 переводов — 90,000 сум\n\nОтправьте чек сюда после оплаты!",
        'translating': "⏳ Перевод...",
        'voice_listening': "🎤 Слушаю голосовое...",
        'error': "❌ Ошибка: {err}",
        'new_referral': "🎉 Поздравляем! По вашей ссылке зашел друг!\nВам начислено **5 бесплатных голосовых** переводов! 🎁"
    },
    'en': {
        'sub_warning': "🛑 **Subscribe to our sponsor channel to use the bot!**\n\n1. Join via the button below.\n2. Click **'Verify'**.",
        'btn_join': "📢 Join Channel",
        'btn_verify': "🔄 Verify",
        'sub_success': "✅ Thank you! Subscription verified.",
        'sub_fail': "❌ You haven't joined yet!",
        'btn_webapp': "🚀 Open Mini App",
        'btn_profile': "👤 My Profile",
        'btn_interface_lang': "🌐 Interface Language",
        'welcome': "👋 Hello! I am the **Smart Linguist** bot.\n\nCurrent translation target: **{lang}**\n\nSend me text or voice, and I will translate and analyze it! 🎯",
        'profile_text': "👤 **Your Profile:**\n\n🆔 Your ID: `{user_id}`\n🌐 Interface: {ui_lang}\n💳 Voice Balance: **{balance}**\n📊 Total Translations: **{total_trans}**\n👥 Invited Friends: **{refs}**\n\n🔗 **Your Referral Link:**\n`https://t.me/{bot_user}?start=ref{user_id}`\n\n*Share this link. You get 5 free voice limits for each friend who joins!*",
        'btn_share': "↗️ Share with Friends",
        'tariff_msg': "🎙 **Voice translations require a balance.**\n\nBuy a package or invite friends using your referral link for free limits!",
        'card_info': "💳 **Card Payment (P2P)**\n\nTransfer to:\n💳 Card: `{card}`\n\n**Prices:**\n🔹 100 voices — 10,000 UZS\n🔹 1000 voices — 90,000 UZS\n\nSend the receipt screenshot here!",
        'translating': "⏳ Translating...",
        'voice_listening': "🎤 Listening to voice...",
        'error': "❌ Error: {err}",
        'new_referral': "🎉 Congratulations! A friend joined using your link!\nYou received **5 Free Voice Limits**! 🎁"
    }
}

def get_text(user_id, key, **kwargs):
    ui_lang = get_interface_lang(user_id)
    if ui_lang not in UI_TEXTS:
        ui_lang = 'uz'
    text = UI_TEXTS[ui_lang].get(key, UI_TEXTS['uz'].get(key, ""))
    return text.format(**kwargs)

def get_user_lang(user_id):
    return LANGUAGES.get(user_langs.get(user_id, 'uz'), "O'zbek")

# Obunani tekshirish funksiyasi
def check_subscription(user_id):
    try:
        status = bot.get_chat_member(CHANNEL_USERNAME, user_id).status
        return status in ['member', 'administrator', 'creator']
    except Exception as e:
        return False

def send_subscription_warning(chat_id, user_id):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(text=get_text(user_id, 'btn_join'), url=f"https://t.me/{CHANNEL_USERNAME[1:]}"))
    markup.add(InlineKeyboardButton(text=get_text(user_id, 'btn_verify'), callback_data="check_sub_callback"))
    bot.send_message(chat_id, get_text(user_id, 'sub_warning'), reply_markup=markup, parse_mode="Markdown")

# Tariflar
def send_tariff_menu(chat_id, user_id):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(text="🌟 100 (99 ⭐)", callback_data="buy_package_100"), 
               InlineKeyboardButton(text="🌟 1000 (999 ⭐)", callback_data="buy_package_1000"))
    markup.add(InlineKeyboardButton(text="💳 Karta orqali (P2P)", callback_data="buy_p2p"))
    bot.send_message(chat_id, get_text(user_id, 'tariff_msg'), reply_markup=markup, parse_mode="Markdown")

waiting_for_receipt = {}
admin_broadcast_state = {}
admin_add_limit_state = {}

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    register_user(user_id)
    
    # Referal tizimi
    parts = message.text.split()
    if len(parts) > 1 and parts[1].startswith('ref'):
        try:
            referrer_id = int(parts[1][3:])
            if referrer_id != user_id:
                is_new = set_referrer(user_id, referrer_id)
                if is_new:
                    add_voice_balance(referrer_id, 5)
                    bot.send_message(referrer_id, get_text(referrer_id, 'new_referral'))
        except:
            pass

    if not check_subscription(user_id):
        send_subscription_warning(message.chat.id, user_id)
        return

    if message.chat.id in waiting_for_receipt:
        del waiting_for_receipt[message.chat.id]

    from telebot.types import ReplyKeyboardMarkup, KeyboardButton
    reply_markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    web_app_btn = KeyboardButton(text="🤖 AI Tarjimon", web_app=WebAppInfo(url=WEBAPP_URL))
    reply_markup.add(web_app_btn)
    
    btn_profile = KeyboardButton(text="👤 Profil")
    btn_lang = KeyboardButton(text="🌐 Tarjima Tili")
    reply_markup.add(btn_profile, btn_lang)
    
    if str(user_id) == str(ADMIN_ID):
        reply_markup.add(KeyboardButton(text="⚙️ Admin"))
    
    current_lang = get_user_lang(user_id)
    salom_matn = get_text(user_id, 'welcome', lang=current_lang)
    
    bot.send_message(message.chat.id, salom_matn, reply_markup=reply_markup, parse_mode="Markdown")
    show_language_menu(message.chat.id, user_id)

def show_language_menu(chat_id, user_id):
    markup = InlineKeyboardMarkup()
    lang_keys = list(LANGUAGES.keys())
    for i in range(0, len(lang_keys), 2):
        row = []
        for j in range(2):
            if i + j < len(lang_keys):
                code = lang_keys[i+j]
                btn_text = LANGUAGES[code]
                if user_langs.get(user_id, 'uz') == code:
                    btn_text = "✅ " + btn_text
                row.append(InlineKeyboardButton(text=btn_text, callback_data=f"lang_{code}"))
        markup.row(*row)
    
    # Interfeys tili tugmasini ham shu yerga qo'shamiz
    markup.row(InlineKeyboardButton(text=get_text(user_id, 'btn_interface_lang'), callback_data="change_ui_lang"))
    bot.send_message(chat_id, "👇 Qaysi tilga tarjima qilishni tanlang:", reply_markup=markup)

def send_profile_info(chat_id, user_id):
    bal, trans, refs, ui = get_user_stats(user_id)
    
    # ui None bo'lishi mumkinligini tekshiramiz
    ui_str = ui.upper() if ui else 'UZ'
    
    markup = InlineKeyboardMarkup()
    share_text = f"Zo'r bot ekan, sinab ko'ring! 🎁"
    share_url = f"https://t.me/share/url?url=https://t.me/{BOT_USERNAME}?start=ref{user_id}&text={share_text}"
    markup.add(InlineKeyboardButton(text=get_text(user_id, 'btn_share'), url=share_url))
    
    bot_user_escaped = BOT_USERNAME.replace('_', '\\_') if BOT_USERNAME else "Bot"
    
    text = get_text(user_id, 'profile_text', user_id=user_id, ui_lang=ui_str, balance=bal, total_trans=trans, refs=refs, bot_user=bot_user_escaped)
    
    try:
        bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")
    except telebot.apihelper.ApiTelegramException as e:
        if "parse entities" in str(e).lower():
            bot.send_message(chat_id, text, reply_markup=markup)
        else:
            bot.send_message(chat_id, f"Xatolik: {e}")

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if str(message.from_user.id) != str(ADMIN_ID):
        bot.send_message(message.chat.id, "Siz admin emassiz!")
        return
        
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("📊 Statistika", callback_data="admin_stats"))
    markup.add(InlineKeyboardButton("✉️ Xabar yuborish (Rassilka)", callback_data="admin_broadcast"))
    markup.add(InlineKeyboardButton("🎁 Limit qo'shish", callback_data="admin_add_limit"))
    
    bot.send_message(message.chat.id, "⚙️ **Admin Panel**\n\nKerakli bo'limni tanlang:", reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_'))
def handle_admin_callbacks(call):
    if str(call.from_user.id) != str(ADMIN_ID):
        bot.answer_callback_query(call.id, "Ruxsat yo'q!", show_alert=True)
        return
        
    action = call.data
    
    if action == "admin_stats":
        total_users = get_total_user_count()
        bot.answer_callback_query(call.id, f"📊 Jami foydalanuvchilar: {total_users} ta", show_alert=True)
        
    elif action == "admin_broadcast":
        msg = bot.send_message(call.message.chat.id, "Xabarni yuboring (Rasm, video yoki matn):")
        admin_broadcast_state[call.from_user.id] = True
        
    elif action == "admin_add_limit":
        msg = bot.send_message(call.message.chat.id, "Limit qo'shish uchun foydalanuvchining ID raqamini va summani bo'sh joy tashlab yozing:\nMasalan: `123456789 100`", parse_mode="Markdown")
        admin_add_limit_state[call.from_user.id] = True
        
    elif action.startswith("admin_approve_"):
        parts = call.data.split('_')
        user_id = int(parts[2])
        amount = int(parts[3])
        add_voice_balance(user_id, amount)
        bot.edit_message_caption(f"✅ Tasdiqlandi! Foydalanuvchiga {amount} ta qo'shildi.", chat_id=call.message.chat.id, message_id=call.message.message_id)
        bot.send_message(user_id, f"🎉 Admin to'lovingizni tasdiqladi! {amount} ta qo'shildi.")
        
    elif action.startswith("admin_reject_"):
        user_id = int(call.data.split('_')[2])
        bot.edit_message_caption("❌ Rad etildi.", chat_id=call.message.chat.id, message_id=call.message.message_id)
        bot.send_message(user_id, "❌ To'lov rad etildi.")

@bot.callback_query_handler(func=lambda call: call.data == "check_sub_callback")
def handle_sub_check(call):
    if check_subscription(call.from_user.id):
        bot.answer_callback_query(call.id, get_text(call.from_user.id, 'sub_success'))
        bot.delete_message(call.message.chat.id, call.message.message_id)
        send_welcome(call.message)
    else:
        bot.answer_callback_query(call.id, get_text(call.from_user.id, 'sub_fail'), show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "show_profile")
def handle_show_profile(call):
    user_id = call.from_user.id
    bal, trans, refs, ui = get_user_stats(user_id)
    
    markup = InlineKeyboardMarkup()
    share_text = f"Zo'r bot ekan, sinab ko'ring! 🎁"
    share_url = f"https://t.me/share/url?url=https://t.me/{BOT_USERNAME}?start=ref{user_id}&text={share_text}"
    markup.add(InlineKeyboardButton(text=get_text(user_id, 'btn_share'), url=share_url))
    
    text = get_text(user_id, 'profile_text', user_id=user_id, ui_lang=ui.upper(), balance=bal, total_trans=trans, refs=refs, bot_user=BOT_USERNAME)
    bot.edit_message_text(text, chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "change_ui_lang")
def handle_ui_lang(call):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🇺🇿 O'zbek", callback_data="uilang_uz"),
               InlineKeyboardButton("🇷🇺 Русский", callback_data="uilang_ru"),
               InlineKeyboardButton("🇬🇧 English", callback_data="uilang_en"))
    bot.edit_message_text("Tilni tanlang / Выберите язык / Choose language:", chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('uilang_'))
def handle_uilang_select(call):
    lang = call.data.split('_')[1]
    set_interface_lang(call.from_user.id, lang)
    bot.answer_callback_query(call.id, "✅")
    bot.delete_message(call.message.chat.id, call.message.message_id)
    send_welcome(call.message)

@bot.callback_query_handler(func=lambda call: call.data == "buy_p2p")
def handle_buy_p2p(call):
    card_info = os.getenv('CARD_INFO', '8600 0000 0000 0000 (Ism Familiya)')
    msg = get_text(call.from_user.id, 'card_info', card=card_info)
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
        provider_token="", 
        currency="XTR",
        prices=prices
    )
    bot.answer_callback_query(call.id)

@bot.pre_checkout_query_handler(func=lambda query: True)
def checkout(pre_checkout_query):
    bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True, error_message="Xatolik.")

@bot.message_handler(content_types=['successful_payment'])
def got_payment(message):
    payload = message.successful_payment.invoice_payload
    if payload == "voice_pkg_100":
        add_voice_balance(message.from_user.id, 100)
    elif payload == "voice_pkg_1000":
        add_voice_balance(message.from_user.id, 1000)
    bot.send_message(message.chat.id, "🎉 To'lov muvaffaqiyatli amalga oshirildi!")
    send_welcome(message)

@bot.callback_query_handler(func=lambda call: call.data.startswith('lang_'))
def handle_language_selection(call):
    if not check_subscription(call.from_user.id):
        send_subscription_warning(call.message.chat.id, call.from_user.id)
        return

    lang_code = call.data.split('_')[1]
    if lang_code in LANGUAGES:
        user_langs[call.from_user.id] = lang_code
        bot.answer_callback_query(call.id, f"{LANGUAGES[lang_code]} tanlandi!")
        bot.delete_message(call.message.chat.id, call.message.message_id)
        send_welcome(call.message)

@bot.message_handler(content_types=['photo', 'document'])
def handle_receipt(message):
    user_id = message.from_user.id
    
    # Rassilka holati bo'lsa
    if admin_broadcast_state.get(user_id):
        users = get_all_users()
        sent = 0
        for uid in users:
            try:
                bot.copy_message(uid, message.chat.id, message.message_id)
                sent += 1
            except:
                pass
        bot.send_message(message.chat.id, f"✅ Xabar {sent} ta foydalanuvchiga muvaffaqiyatli yuborildi.")
        del admin_broadcast_state[user_id]
        return

    if waiting_for_receipt.get(user_id):
        if str(ADMIN_ID) == 'Sizning_Telegram_ID_raqamingizni_shu_yerga_yozing':
            bot.send_message(message.chat.id, "Hozircha admin ID sozlanmagan.")
            return
            
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("✅ 100 ta", callback_data=f"admin_approve_{user_id}_100"),
                   InlineKeyboardButton("✅ 1000 ta", callback_data=f"admin_approve_{user_id}_1000"))
        markup.add(InlineKeyboardButton("❌ Rad etish", callback_data=f"admin_reject_{user_id}"))
        
        caption = f"💸 Yangi to'lov (Karta)\n👤 {message.from_user.first_name} (ID: {user_id})"
        
        try:
            bot.copy_message(ADMIN_ID, message.chat.id, message.message_id, caption=caption, reply_markup=markup)
            bot.send_message(message.chat.id, "✅ Chek Adminga yuborildi.")
            del waiting_for_receipt[user_id]
        except Exception as e:
            bot.send_message(message.chat.id, f"Xatolik: {e}")

@bot.message_handler(content_types=['web_app_data'])
def web_app_data_handler(message):
    user_id = message.from_user.id
    if not check_subscription(user_id):
        send_subscription_warning(message.chat.id, user_id)
        return

    try:
        data = json.loads(message.web_app_data.data)
        if data.get('action') == 'translate':
            source = data.get('sourceLang')
            target = data.get('targetLang')
            text = data.get('text')
            
            target_lang_str = target if target else "O'zbek"
            wait_msg = bot.send_message(message.chat.id, get_text(user_id, 'translating'))
            translation = translate_text(f"(Bu matn {source} tilidan kiritildi): {text}", target_lang=target_lang_str)
            try:
                bot.edit_message_text(translation, chat_id=message.chat.id, message_id=wait_msg.message_id, parse_mode="Markdown")
            except telebot.apihelper.ApiTelegramException as e:
                if "parse entities" in str(e).lower():
                    bot.edit_message_text(translation, chat_id=message.chat.id, message_id=wait_msg.message_id)
                else:
                    raise e
            increment_translations(user_id)
    except Exception as e:
        bot.send_message(message.chat.id, get_text(user_id, 'error', err=str(e)))

@bot.message_handler(content_types=['voice'])
def handle_voice(message):
    user_id = message.from_user.id
    if not check_subscription(user_id):
        send_subscription_warning(message.chat.id, user_id)
        return
        
    if not use_voice_balance(user_id):
        send_tariff_menu(message.chat.id, user_id)
        return
        
    wait_msg = bot.send_message(message.chat.id, get_text(user_id, 'voice_listening'))
    try:
        file_info = bot.get_file(message.voice.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        target_lang = get_user_lang(user_id)
        translation = translate_audio(downloaded_file, target_lang=target_lang)
        try:
            bot.edit_message_text(translation, chat_id=message.chat.id, message_id=wait_msg.message_id, parse_mode="Markdown")
        except telebot.apihelper.ApiTelegramException as e:
            if "parse entities" in str(e).lower():
                bot.edit_message_text(translation, chat_id=message.chat.id, message_id=wait_msg.message_id)
            else:
                raise e
        increment_translations(user_id)
    except Exception as e:
        bot.edit_message_text(get_text(user_id, 'error', err=str(e)), chat_id=message.chat.id, message_id=wait_msg.message_id)
        add_voice_balance(user_id, 1)

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.from_user.id
    text = message.text
    
    if not text:
        return
        
    if text == "👤 Profil":
        send_profile_info(message.chat.id, user_id)
        return
    elif text == "🌐 Tarjima Tili":
        show_language_menu(message.chat.id, user_id)
        return
    elif text == "⚙️ Admin" and str(user_id) == str(ADMIN_ID):
        admin_panel(message)
        return
    
    # Admin rassilka
    if admin_broadcast_state.get(user_id):
        users = get_all_users()
        sent = 0
        for uid in users:
            try:
                bot.send_message(uid, text, parse_mode="Markdown")
                sent += 1
            except:
                pass
        bot.send_message(message.chat.id, f"✅ Xabar {sent} ta foydalanuvchiga muvaffaqiyatli yuborildi.")
        del admin_broadcast_state[user_id]
        return
        
    # Admin limit qo'shish
    if admin_add_limit_state.get(user_id):
        parts = text.split()
        if len(parts) == 2:
            try:
                target_user = int(parts[0])
                amount = int(parts[1])
                add_voice_balance(target_user, amount)
                bot.send_message(target_user, f"🎁 Admin sizga {amount} ta ovozli tarjima limiti sovg'a qildi!")
                bot.send_message(message.chat.id, f"✅ Limit muvaffaqiyatli qo'shildi.")
            except:
                bot.send_message(message.chat.id, "❌ Xato kiritildi.")
        del admin_add_limit_state[user_id]
        return

    if not check_subscription(user_id):
        send_subscription_warning(message.chat.id, user_id)
        return
        
    wait_msg = bot.send_message(message.chat.id, get_text(user_id, 'translating'))
    try:
        target_lang = get_user_lang(user_id)
        translation = translate_text(text, target_lang=target_lang)
        try:
            bot.edit_message_text(translation, chat_id=message.chat.id, message_id=wait_msg.message_id, parse_mode="Markdown")
        except telebot.apihelper.ApiTelegramException as e:
            if "parse entities" in str(e).lower():
                bot.edit_message_text(translation, chat_id=message.chat.id, message_id=wait_msg.message_id)
            else:
                raise e
        increment_translations(user_id)
    except Exception as e:
        bot.edit_message_text(get_text(user_id, 'error', err=str(e)), chat_id=message.chat.id, message_id=wait_msg.message_id)

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

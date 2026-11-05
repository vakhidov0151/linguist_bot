import os
import json
import time
import logging
import threading
from datetime import date
from urllib.parse import quote
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import telebot
from telebot import util
from telebot.apihelper import ApiTelegramException
from telebot.types import (InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo, LabeledPrice,
                           ReplyKeyboardMarkup, KeyboardButton)
from dotenv import load_dotenv

from gemini_translator import translate_text, translate_audio
from formatting import md_to_html, strip_tags, split_chunks
from database import (
    add_voice_balance, use_voice_balance,
    increment_translations, get_user_stats, set_interface_lang, get_interface_lang,
    set_target_lang, get_target_lang, save_feedback_message, get_feedback_user,
    set_referrer, get_all_users, get_total_user_count, register_user
)

load_dotenv(override=True)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("bot")

API_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
# Mini App shu botning o'zidan (Railway public domain) beriladi; WEBAPP_URL bilan boshqasini ko'rsatish mumkin
_railway_domain = os.getenv('RAILWAY_PUBLIC_DOMAIN')
WEBAPP_URL = os.getenv('WEBAPP_URL') or (f"https://{_railway_domain}/" if _railway_domain else None)
CHANNEL_USERNAME = "@amaliysanatjilosi"
ADMIN_ID = os.getenv('ADMIN_ID', 'Sizning_Telegram_ID_raqamingizni_shu_yerga_yozing')

# Bepul matnli tarjima cheklovlari (Gemini xarajatini suiiste'mol qilishdan himoya)
TEXT_DAILY_LIMIT = int(os.getenv('TEXT_DAILY_LIMIT', '300'))
MIN_SECONDS_BETWEEN_REQUESTS = float(os.getenv('MIN_SECONDS_BETWEEN_REQUESTS', '2'))
MAX_VOICE_SECONDS = int(os.getenv('MAX_VOICE_SECONDS', '300'))
MAX_TEXT_LENGTH = 3000

if not API_TOKEN or API_TOKEN == "bu_yerga_telegram_tokenni_yozing":
    raise ValueError("TELEGRAM_BOT_TOKEN topilmadi!")

# Standart 2 ta thread o'rniga 16 ta: Gemini javobini kutayotgan foydalanuvchilar boshqalarni to'sib qo'ymaydi
bot = telebot.TeleBot(API_TOKEN, num_threads=int(os.getenv('BOT_THREADS', '16')))
bot_info = bot.get_me()
BOT_USERNAME = bot_info.username

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
        'error': "❌ Xatolik yuz berdi. Birozdan so'ng qayta urinib ko'ring.",
        'new_referral': "🎉 Tabriklaymiz! Sizning taklifingiz bilan do'stingiz botga qo'shildi!\nSizga **5 ta Bepul Ovozli xabar** limiti sovg'a qilindi! 🎁",
        'lang_menu': "👇 Qaysi tilga tarjima qilishni tanlang:",
        'slow_down': "⏳ Biroz sekinroq — {sec} soniyada bitta so'rov yuborish mumkin.",
        'daily_limit': "📵 Bugungi bepul tarjimalar limiti tugadi ({limit} ta). Ertaga yana urinib ko'ring.",
        'voice_too_long': "🎙 Ovozli xabar juda uzun. Eng ko'pi bilan {sec} soniya.",
        'text_too_long': "✂️ Matn juda uzun. Eng ko'pi bilan {limit} belgi yuboring.",
        'fb_menu': "✉️ **Taklif va shikoyat**\n\nMurojaat turini tanlang:",
        'fb_complaint': "⚠️ Shikoyat",
        'fb_idea': "💡 Taklif",
        'fb_question': "❓ Savol",
        'fb_cancel': "❌ Bekor qilish",
        'fb_cancelled': "Bekor qilindi.",
        'fb_write': "✍️ Xabaringizni yozing. Matn, rasm, video yoki ovozli xabar yuborishingiz mumkin:",
        'fb_sent': "✅ Murojaatingiz adminga yuborildi! Rahmat.",
        'fb_wait': "⏳ Biroz kuting va qayta yuboring.",
        'fb_off': "Hozircha murojaat qabul qilinmayapti. Keyinroq urinib ko'ring.",
        'fb_reply': "📩 Admin javobi:"
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
        'error': "❌ Произошла ошибка. Попробуйте ещё раз чуть позже.",
        'new_referral': "🎉 Поздравляем! По вашей ссылке зашел друг!\nВам начислено **5 бесплатных голосовых** переводов! 🎁",
        'lang_menu': "👇 Выберите язык перевода:",
        'slow_down': "⏳ Не так быстро — не чаще одного запроса в {sec} сек.",
        'daily_limit': "📵 Дневной лимит бесплатных переводов исчерпан ({limit}). Попробуйте завтра.",
        'voice_too_long': "🎙 Голосовое слишком длинное. Максимум {sec} сек.",
        'text_too_long': "✂️ Текст слишком длинный. Максимум {limit} символов.",
        'fb_menu': "✉️ **Предложения и жалобы**\n\nВыберите тип обращения:",
        'fb_complaint': "⚠️ Жалоба",
        'fb_idea': "💡 Предложение",
        'fb_question': "❓ Вопрос",
        'fb_cancel': "❌ Отмена",
        'fb_cancelled': "Отменено.",
        'fb_write': "✍️ Напишите сообщение. Можно отправить текст, фото, видео или голосовое:",
        'fb_sent': "✅ Ваше обращение отправлено администратору! Спасибо.",
        'fb_wait': "⏳ Подождите немного и отправьте снова.",
        'fb_off': "Сейчас обращения не принимаются. Попробуйте позже.",
        'fb_reply': "📩 Ответ администратора:"
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
        'error': "❌ Something went wrong. Please try again in a moment.",
        'new_referral': "🎉 Congratulations! A friend joined using your link!\nYou received **5 Free Voice Limits**! 🎁",
        'lang_menu': "👇 Choose the target language:",
        'slow_down': "⏳ Slow down — one request every {sec} seconds.",
        'daily_limit': "📵 Today's free translation limit is used up ({limit}). Try again tomorrow.",
        'voice_too_long': "🎙 Voice message is too long. Maximum {sec} seconds.",
        'text_too_long': "✂️ Text is too long. Maximum {limit} characters.",
        'fb_menu': "✉️ **Suggestions and complaints**\n\nChoose the type of your message:",
        'fb_complaint': "⚠️ Complaint",
        'fb_idea': "💡 Suggestion",
        'fb_question': "❓ Question",
        'fb_cancel': "❌ Cancel",
        'fb_cancelled': "Cancelled.",
        'fb_write': "✍️ Write your message. You can send text, a photo, a video or a voice message:",
        'fb_sent': "✅ Your message was sent to the admin! Thank you.",
        'fb_wait': "⏳ Please wait a moment and send it again.",
        'fb_off': "Messages are not accepted right now. Please try later.",
        'fb_reply': "📩 Admin's reply:"
    }
}


def get_text(user_id, key, /, **kwargs):
    # "/" — matn ichida {user_id} bo'lsa ham argumentlar to'qnashmaydi (profilda shunday edi)
    ui_lang = get_interface_lang(user_id)
    if ui_lang not in UI_TEXTS:
        ui_lang = 'uz'
    text = UI_TEXTS[ui_lang].get(key, UI_TEXTS['uz'].get(key, ""))
    return text.format(**kwargs)


def get_user_lang(user_id):
    return LANGUAGES.get(get_target_lang(user_id), LANGUAGES['uz'])


def is_admin(user_id):
    return str(user_id) == str(ADMIN_ID)


# --- Xabar yuborish yordamchilari (HTML + 4096 belgidan uzun matnni bo'lish) ---
def _send_chunk(chat_id, chunk, reply_markup=None, edit_message_id=None):
    # Avval HTML bilan, teglar buzilgan bo'lsa — oddiy matn sifatida
    for parse_mode, body in (("HTML", chunk), (None, strip_tags(chunk))):
        try:
            if edit_message_id:
                return bot.edit_message_text(body, chat_id=chat_id, message_id=edit_message_id,
                                             reply_markup=reply_markup, parse_mode=parse_mode)
            return bot.send_message(chat_id, body, reply_markup=reply_markup, parse_mode=parse_mode)
        except ApiTelegramException as e:
            if parse_mode and "parse" in str(e).lower():
                continue
            raise


def send_html(chat_id, html_text, reply_markup=None, edit_message_id=None):
    chunks = split_chunks(html_text)
    last = None
    for i, chunk in enumerate(chunks):
        markup = reply_markup if i == len(chunks) - 1 else None
        last = _send_chunk(chat_id, chunk, markup, edit_message_id if i == 0 else None)
    return last


def send_md(chat_id, text, reply_markup=None, edit_message_id=None):
    return send_html(chat_id, md_to_html(text), reply_markup, edit_message_id)


def safe_delete(chat_id, message_id):
    try:
        bot.delete_message(chat_id, message_id)
    except Exception:
        pass


# --- Obuna tekshiruvi (ijobiy natija 10 daqiqa keshlanadi) ---
_sub_cache = {}


def check_subscription(user_id):
    now = time.time()
    if _sub_cache.get(user_id, 0) > now:
        return True
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
    except ApiTelegramException as e:
        if "user not found" in str(e).lower() or "participant" in str(e).lower():
            return False
        # Bot kanalda admin bo'lmasa — hamma foydalanuvchini bloklamaymiz, faqat logga yozamiz
        log.error("Obunani tekshirib bo'lmadi (bot %s da adminmi?): %s", CHANNEL_USERNAME, e)
        return True
    except Exception as e:
        log.warning("Obuna tekshiruvi xatosi: %s", e)
        return True
    ok = member.status in ('member', 'administrator', 'creator') or \
        (member.status == 'restricted' and getattr(member, 'is_member', False))
    if ok:
        _sub_cache[user_id] = now + 600
    return ok


def send_subscription_warning(chat_id, user_id):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(text=get_text(user_id, 'btn_join'), url=f"https://t.me/{CHANNEL_USERNAME[1:]}"))
    markup.add(InlineKeyboardButton(text=get_text(user_id, 'btn_verify'), callback_data="check_sub_callback"))
    send_md(chat_id, get_text(user_id, 'sub_warning'), reply_markup=markup)


# --- Tezlik va kunlik cheklov (faqat bepul matnli tarjimalar uchun) ---
_rate_lock = threading.Lock()
_last_request = {}
_daily_usage = {}


def rate_limit_message(user_id):
    """Cheklovga tushsa foydalanuvchiga ko'rsatiladigan matn, aks holda None."""
    if is_admin(user_id):
        return None
    now = time.time()
    today = date.today().isoformat()
    with _rate_lock:
        if now - _last_request.get(user_id, 0) < MIN_SECONDS_BETWEEN_REQUESTS:
            return get_text(user_id, 'slow_down', sec=int(MIN_SECONDS_BETWEEN_REQUESTS))
        day, count = _daily_usage.get(user_id, (today, 0))
        if day != today:
            count = 0
        if count >= TEXT_DAILY_LIMIT:
            return get_text(user_id, 'daily_limit', limit=TEXT_DAILY_LIMIT)
        _last_request[user_id] = now
        _daily_usage[user_id] = (today, count + 1)
    return None


# Tariflar
def send_tariff_menu(chat_id, user_id):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(text="🌟 100 (99 ⭐)", callback_data="buy_package_100"),
               InlineKeyboardButton(text="🌟 1000 (999 ⭐)", callback_data="buy_package_1000"))
    markup.add(InlineKeyboardButton(text="💳 Karta orqali (P2P)", callback_data="buy_p2p"))
    send_md(chat_id, get_text(user_id, 'tariff_msg'), reply_markup=markup)


waiting_for_receipt = {}
FEEDBACK_BUTTON = "✉️ Taklif va shikoyat"
FEEDBACK_KINDS = ('complaint', 'idea', 'question')
FEEDBACK_COOLDOWN = 30  # soniya: bir foydalanuvchi adminni xabarga ko'mib yubormasligi uchun
feedback_state = {}      # user_id -> murojaat turi (xabar kutilmoqda)
feedback_last_sent = {}  # user_id -> oxirgi yuborilgan vaqt
admin_broadcast_state = {}
admin_add_limit_state = {}
_processed_receipts = set()
_receipt_lock = threading.Lock()


def show_main_menu(chat_id, user_id, with_lang_menu=True):
    """Asosiy menyu. user_id har doim haqiqiy foydalanuvchiniki (callback'da call.message.from_user — bu bot!)."""
    if not check_subscription(user_id):
        send_subscription_warning(chat_id, user_id)
        return

    waiting_for_receipt.pop(user_id, None)
    feedback_state.pop(user_id, None)

    reply_markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    if WEBAPP_URL:
        reply_markup.add(KeyboardButton(text="🤖 AI Tarjimon", web_app=WebAppInfo(url=WEBAPP_URL)))
    reply_markup.add(KeyboardButton(text="👤 Profil"), KeyboardButton(text="🌐 Tarjima Tili"))
    reply_markup.add(KeyboardButton(text=FEEDBACK_BUTTON))
    if is_admin(user_id):
        reply_markup.add(KeyboardButton(text="⚙️ Admin"))

    send_md(chat_id, get_text(user_id, 'welcome', lang=get_user_lang(user_id)), reply_markup=reply_markup)
    if with_lang_menu:
        show_language_menu(chat_id, user_id)


@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    is_new = register_user(user_id)

    # Referal tizimi: faqat botga BIRINCHI marta kirgan foydalanuvchi hisoblanadi
    parts = (message.text or "").split()
    if is_new and len(parts) > 1 and parts[1].startswith('ref'):
        try:
            referrer_id = int(parts[1][3:])
        except ValueError:
            referrer_id = None
        if referrer_id and set_referrer(user_id, referrer_id):
            add_voice_balance(referrer_id, 5)
            try:
                send_md(referrer_id, get_text(referrer_id, 'new_referral'))
            except Exception:
                pass

    show_main_menu(message.chat.id, user_id)


def show_language_menu(chat_id, user_id):
    markup = InlineKeyboardMarkup()
    current = get_target_lang(user_id)
    lang_keys = list(LANGUAGES.keys())
    for i in range(0, len(lang_keys), 2):
        row = []
        for code in lang_keys[i:i + 2]:
            btn_text = LANGUAGES[code]
            if current == code:
                btn_text = "✅ " + btn_text
            row.append(InlineKeyboardButton(text=btn_text, callback_data=f"lang_{code}"))
        markup.row(*row)

    # Interfeys tili tugmasini ham shu yerga qo'shamiz
    markup.row(InlineKeyboardButton(text=get_text(user_id, 'btn_interface_lang'), callback_data="change_ui_lang"))
    bot.send_message(chat_id, get_text(user_id, 'lang_menu'), reply_markup=markup)


def build_profile(user_id):
    bal, trans, refs, ui = get_user_stats(user_id)

    markup = InlineKeyboardMarkup()
    share_text = quote("Zo'r bot ekan, sinab ko'ring! 🎁")
    share_link = quote(f"https://t.me/{BOT_USERNAME}?start=ref{user_id}", safe='')
    share_url = f"https://t.me/share/url?url={share_link}&text={share_text}"
    markup.add(InlineKeyboardButton(text=get_text(user_id, 'btn_share'), url=share_url))

    text = get_text(user_id, 'profile_text', user_id=user_id, ui_lang=(ui or 'uz').upper(), balance=bal,
                    total_trans=trans, refs=refs, bot_user=BOT_USERNAME or "Bot")
    return text, markup


def send_profile_info(chat_id, user_id):
    text, markup = build_profile(user_id)
    send_md(chat_id, text, reply_markup=markup)


@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if not is_admin(message.from_user.id):
        bot.send_message(message.chat.id, "Siz admin emassiz!")
        return

    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("📊 Statistika", callback_data="admin_stats"))
    markup.add(InlineKeyboardButton("✉️ Xabar yuborish (Rassilka)", callback_data="admin_broadcast"))
    markup.add(InlineKeyboardButton("🎁 Limit qo'shish", callback_data="admin_add_limit"))

    send_md(message.chat.id, "⚙️ **Admin Panel**\n\nKerakli bo'limni tanlang:", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_'))
def handle_admin_callbacks(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "Ruxsat yo'q!", show_alert=True)
        return

    action = call.data

    if action == "admin_stats":
        total_users = get_total_user_count()
        bot.answer_callback_query(call.id, f"📊 Jami foydalanuvchilar: {total_users} ta", show_alert=True)
        return

    bot.answer_callback_query(call.id)

    if action == "admin_broadcast":
        bot.send_message(call.message.chat.id, "Xabarni yuboring (matn, rasm, video, ovoz — istalgan turdagi).\n"
                                               "Bekor qilish uchun: /cancel")
        admin_broadcast_state[call.from_user.id] = True

    elif action == "admin_add_limit":
        send_md(call.message.chat.id, "Limit qo'shish uchun foydalanuvchining ID raqamini va summani bo'sh joy "
                                      "tashlab yozing:\nMasalan: `123456789 100`\nBekor qilish uchun: /cancel")
        admin_add_limit_state[call.from_user.id] = True

    elif action.startswith("admin_approve_") or action.startswith("admin_reject_"):
        # Ikki marta bosilsa ikki marta qo'shilmasligi uchun
        key = (call.message.chat.id, call.message.message_id)
        with _receipt_lock:
            if key in _processed_receipts:
                return
            _processed_receipts.add(key)

        parts = action.split('_')
        user_id = int(parts[2])
        if action.startswith("admin_approve_"):
            amount = int(parts[3])
            add_voice_balance(user_id, amount)
            result_text = f"✅ Tasdiqlandi! Foydalanuvchiga {amount} ta qo'shildi."
            user_text = f"🎉 Admin to'lovingizni tasdiqladi! {amount} ta qo'shildi."
        else:
            result_text = "❌ Rad etildi."
            user_text = "❌ To'lov rad etildi."
        try:
            bot.edit_message_caption(result_text, chat_id=call.message.chat.id, message_id=call.message.message_id)
        except Exception:
            bot.send_message(call.message.chat.id, result_text)
        try:
            bot.send_message(user_id, user_text)
        except Exception:
            pass


@bot.callback_query_handler(func=lambda call: call.data == "check_sub_callback")
def handle_sub_check(call):
    if check_subscription(call.from_user.id):
        bot.answer_callback_query(call.id, get_text(call.from_user.id, 'sub_success'))
        safe_delete(call.message.chat.id, call.message.message_id)
        show_main_menu(call.message.chat.id, call.from_user.id)
    else:
        bot.answer_callback_query(call.id, get_text(call.from_user.id, 'sub_fail'), show_alert=True)


@bot.callback_query_handler(func=lambda call: call.data == "show_profile")
def handle_show_profile(call):
    text, markup = build_profile(call.from_user.id)
    bot.answer_callback_query(call.id)
    send_md(call.message.chat.id, text, reply_markup=markup, edit_message_id=call.message.message_id)


@bot.callback_query_handler(func=lambda call: call.data == "change_ui_lang")
def handle_ui_lang(call):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🇺🇿 O'zbek", callback_data="uilang_uz"),
               InlineKeyboardButton("🇷🇺 Русский", callback_data="uilang_ru"),
               InlineKeyboardButton("🇬🇧 English", callback_data="uilang_en"))
    bot.answer_callback_query(call.id)
    bot.edit_message_text("Tilni tanlang / Выберите язык / Choose language:", chat_id=call.message.chat.id,
                          message_id=call.message.message_id, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith('uilang_'))
def handle_uilang_select(call):
    lang = call.data.split('_')[1]
    if lang not in UI_TEXTS:
        bot.answer_callback_query(call.id)
        return
    set_interface_lang(call.from_user.id, lang)
    bot.answer_callback_query(call.id, "✅")
    safe_delete(call.message.chat.id, call.message.message_id)
    show_main_menu(call.message.chat.id, call.from_user.id)


@bot.callback_query_handler(func=lambda call: call.data == "buy_p2p")
def handle_buy_p2p(call):
    card_info = os.getenv('CARD_INFO', '8600 0000 0000 0000 (Ism Familiya)')
    msg = get_text(call.from_user.id, 'card_info', card=card_info)
    waiting_for_receipt[call.from_user.id] = True
    bot.answer_callback_query(call.id)
    send_md(call.message.chat.id, msg, edit_message_id=call.message.message_id)


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
        bot.answer_callback_query(call.id)
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
    ok = pre_checkout_query.invoice_payload in ("voice_pkg_100", "voice_pkg_1000")
    bot.answer_pre_checkout_query(pre_checkout_query.id, ok=ok, error_message="Xatolik.")


@bot.message_handler(content_types=['successful_payment'])
def got_payment(message):
    payload = message.successful_payment.invoice_payload
    if payload == "voice_pkg_100":
        add_voice_balance(message.from_user.id, 100)
    elif payload == "voice_pkg_1000":
        add_voice_balance(message.from_user.id, 1000)
    bot.send_message(message.chat.id, "🎉 To'lov muvaffaqiyatli amalga oshirildi!")
    show_main_menu(message.chat.id, message.from_user.id, with_lang_menu=False)


@bot.callback_query_handler(func=lambda call: call.data.startswith('lang_'))
def handle_language_selection(call):
    user_id = call.from_user.id
    if not check_subscription(user_id):
        bot.answer_callback_query(call.id)
        send_subscription_warning(call.message.chat.id, user_id)
        return

    lang_code = call.data.split('_')[1]
    if lang_code in LANGUAGES:
        set_target_lang(user_id, lang_code)
        bot.answer_callback_query(call.id, f"{LANGUAGES[lang_code]} tanlandi!")
        safe_delete(call.message.chat.id, call.message.message_id)
        show_main_menu(call.message.chat.id, user_id, with_lang_menu=False)
    else:
        bot.answer_callback_query(call.id)


# --- Admin holatlari: boshqa handlerlardan OLDIN ro'yxatdan o'tadi (istalgan turdagi xabar) ---
def _broadcast_worker(admin_chat_id, from_chat_id, message_id):
    users = get_all_users()
    sent = failed = 0
    for uid in users:
        for _attempt in range(3):
            try:
                bot.copy_message(uid, from_chat_id, message_id)
                sent += 1
                break
            except ApiTelegramException as e:
                if e.error_code == 429:
                    retry_after = (e.result_json or {}).get('parameters', {}).get('retry_after', 5)
                    time.sleep(int(retry_after) + 1)
                    continue
                failed += 1
                break
            except Exception:
                failed += 1
                break
        time.sleep(0.05)  # Telegram limiti: ~30 xabar/soniya
    bot.send_message(admin_chat_id, f"✅ Rassilka tugadi.\n✔️ Yuborildi: {sent} ta\n❌ Yetib bormadi: {failed} ta")


MENU_BUTTONS = ("👤 Profil", "🌐 Tarjima Tili", "⚙️ Admin", FEEDBACK_BUTTON)


# --- Taklif va shikoyat ---
@bot.message_handler(func=lambda m: m.from_user and is_admin(m.from_user.id) and m.reply_to_message
                     and get_feedback_user(m.reply_to_message.message_id),
                     content_types=util.content_type_media)
def handle_admin_feedback_reply(message):
    user_id = get_feedback_user(message.reply_to_message.message_id)
    try:
        bot.send_message(user_id, get_text(user_id, 'fb_reply'))
        bot.copy_message(user_id, message.chat.id, message.message_id)
        bot.send_message(message.chat.id, "✅ Javobingiz foydalanuvchiga yuborildi!")
    except Exception as e:
        log.warning("Admin javobi yetmadi (%s): %s", user_id, e)
        bot.send_message(message.chat.id, "❌ Javob yetmadi: foydalanuvchi botni bloklagan bo'lishi mumkin.")


@bot.message_handler(commands=['aloqa'])
@bot.message_handler(func=lambda m: m.text == FEEDBACK_BUTTON)
def feedback_start(message):
    user_id = message.from_user.id
    feedback_state.pop(user_id, None)
    markup = InlineKeyboardMarkup()
    for kind in FEEDBACK_KINDS:
        markup.add(InlineKeyboardButton(get_text(user_id, f'fb_{kind}'), callback_data=f"fb_type_{kind}"))
    markup.add(InlineKeyboardButton(get_text(user_id, 'fb_cancel'), callback_data="fb_cancel"))
    send_md(message.chat.id, get_text(user_id, 'fb_menu'), reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith('fb_type_'))
def feedback_type_selected(call):
    kind = call.data[len('fb_type_'):]
    if kind not in FEEDBACK_KINDS:
        bot.answer_callback_query(call.id)
        return
    user_id = call.from_user.id
    feedback_state[user_id] = kind
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(get_text(user_id, 'fb_cancel'), callback_data="fb_cancel"))
    bot.answer_callback_query(call.id)
    bot.edit_message_text(get_text(user_id, 'fb_write'), chat_id=call.message.chat.id,
                          message_id=call.message.message_id, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == "fb_cancel")
def feedback_cancel(call):
    feedback_state.pop(call.from_user.id, None)
    bot.answer_callback_query(call.id, get_text(call.from_user.id, 'fb_cancelled'))
    safe_delete(call.message.chat.id, call.message.message_id)


@bot.message_handler(func=lambda m: m.from_user and m.from_user.id in feedback_state,
                     content_types=util.content_type_media)
def feedback_message(message):
    user_id = message.from_user.id

    # Menyu tugmasi yoki buyruq: murojaat bekor bo'ladi, tugma odatdagidek ishlaydi
    if message.text in MENU_BUTTONS:
        feedback_state.pop(user_id, None)
        handle_message(message)
        return
    if (message.text or "").startswith('/'):
        feedback_state.pop(user_id, None)
        bot.send_message(message.chat.id, get_text(user_id, 'fb_cancelled'))
        return

    if time.time() - feedback_last_sent.get(user_id, 0) < FEEDBACK_COOLDOWN:
        bot.send_message(message.chat.id, get_text(user_id, 'fb_wait'))
        return

    kind = feedback_state.pop(user_id)
    if not str(ADMIN_ID).lstrip('-').isdigit():
        log.error("ADMIN_ID o'rnatilmagan: murojaat yetkazilmadi")
        bot.send_message(message.chat.id, get_text(user_id, 'fb_off'))
        return

    user = message.from_user
    info = (f"📩 Yangi murojaat: {UI_TEXTS['uz'][f'fb_{kind}']}\n\n"
            f"Foydalanuvchi: {user.first_name or ''} (ID: {user_id})\n")
    if user.username:
        info += f"Username: @{user.username}\n"
    info += "\n↩️ Javob berish uchun shu xabarga yoki keyingi xabarga Reply qiling."
    try:
        info_msg = bot.send_message(int(ADMIN_ID), info)
        copied = bot.copy_message(int(ADMIN_ID), message.chat.id, message.message_id)
        save_feedback_message(info_msg.message_id, user_id)
        save_feedback_message(copied.message_id, user_id)
    except Exception:
        log.exception("Murojaatni adminga yuborib bo'lmadi")
        bot.send_message(message.chat.id, get_text(user_id, 'error'))
        return

    feedback_last_sent[user_id] = time.time()
    bot.send_message(message.chat.id, get_text(user_id, 'fb_sent'))



@bot.message_handler(func=lambda m: m.from_user and admin_broadcast_state.get(m.from_user.id)
                     and m.text not in MENU_BUTTONS,  # menyu tugmasi tasodifan rassilka bo'lib ketmasin
                     content_types=util.content_type_media)
def handle_admin_broadcast(message):
    admin_broadcast_state.pop(message.from_user.id, None)
    if message.text and message.text.strip() == '/cancel':
        bot.send_message(message.chat.id, "❌ Rassilka bekor qilindi.")
        return
    total = get_total_user_count()
    bot.send_message(message.chat.id, f"⏳ Xabar {total} ta foydalanuvchiga yuborilmoqda...")
    # Alohida thread'da — bot boshqa foydalanuvchilarga javob berishda davom etadi
    threading.Thread(target=_broadcast_worker, args=(message.chat.id, message.chat.id, message.message_id),
                     daemon=True).start()


@bot.message_handler(func=lambda m: m.from_user and admin_add_limit_state.get(m.from_user.id))
def handle_admin_add_limit(message):
    admin_add_limit_state.pop(message.from_user.id, None)
    text = (message.text or "").strip()
    if text == '/cancel':
        bot.send_message(message.chat.id, "❌ Bekor qilindi.")
        return
    parts = text.split()
    try:
        target_user, amount = int(parts[0]), int(parts[1])
        if len(parts) != 2 or not (0 < amount <= 100000):
            raise ValueError
    except (ValueError, IndexError):
        bot.send_message(message.chat.id, "❌ Xato kiritildi. Masalan: 123456789 100")
        return
    add_voice_balance(target_user, amount)
    try:
        bot.send_message(target_user, f"🎁 Admin sizga {amount} ta ovozli tarjima limiti sovg'a qildi!")
    except Exception:
        pass
    bot.send_message(message.chat.id, "✅ Limit muvaffaqiyatli qo'shildi.")


@bot.message_handler(content_types=['photo', 'document'])
def handle_receipt(message):
    user_id = message.from_user.id

    if waiting_for_receipt.get(user_id):
        if not str(ADMIN_ID).lstrip('-').isdigit():
            bot.send_message(message.chat.id, "Hozircha admin ID sozlanmagan.")
            return

        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("✅ 100 ta", callback_data=f"admin_approve_{user_id}_100"),
                   InlineKeyboardButton("✅ 1000 ta", callback_data=f"admin_approve_{user_id}_1000"))
        markup.add(InlineKeyboardButton("❌ Rad etish", callback_data=f"admin_reject_{user_id}"))

        caption = f"💸 Yangi to'lov (Karta)\n👤 {message.from_user.first_name} (ID: {user_id})"

        try:
            bot.copy_message(int(ADMIN_ID), message.chat.id, message.message_id, caption=caption, reply_markup=markup)
            bot.send_message(message.chat.id, "✅ Chek Adminga yuborildi.")
            waiting_for_receipt.pop(user_id, None)
        except Exception:
            log.exception("Chekni adminga yuborib bo'lmadi")
            bot.send_message(message.chat.id, get_text(user_id, 'error'))


def deliver_translation(chat_id, user_id, wait_msg, translate_fn):
    """Tarjimani bajaradi va natijani (HTML, kerak bo'lsa bo'lib) yuboradi. Muvaffaqiyatli bo'lsa True."""
    try:
        translation = translate_fn()
        send_md(chat_id, translation, edit_message_id=wait_msg.message_id)
        increment_translations(user_id)
        return True
    except Exception:
        log.exception("Tarjima xatosi (user %s)", user_id)
        try:
            bot.edit_message_text(get_text(user_id, 'error'), chat_id=chat_id, message_id=wait_msg.message_id)
        except Exception:
            pass
        return False


@bot.message_handler(content_types=['web_app_data'])
def web_app_data_handler(message):
    user_id = message.from_user.id
    if not check_subscription(user_id):
        send_subscription_warning(message.chat.id, user_id)
        return

    try:
        data = json.loads(message.web_app_data.data)
    except ValueError:
        return
    if data.get('action') != 'translate':
        return

    source = str(data.get('sourceLang') or 'Auto')[:30]
    target_lang_str = str(data.get('targetLang') or "O'zbek")[:30]
    text = str(data.get('text') or '').strip()
    if not text:
        return
    if len(text) > MAX_TEXT_LENGTH:
        bot.send_message(message.chat.id, get_text(user_id, 'text_too_long', limit=MAX_TEXT_LENGTH))
        return
    limited = rate_limit_message(user_id)
    if limited:
        bot.send_message(message.chat.id, limited)
        return

    wait_msg = bot.send_message(message.chat.id, get_text(user_id, 'translating'))
    deliver_translation(message.chat.id, user_id, wait_msg,
                        lambda: translate_text(f"(Bu matn {source} tilidan kiritildi): {text}",
                                               target_lang=target_lang_str))


@bot.message_handler(content_types=['voice'])
def handle_voice(message):
    user_id = message.from_user.id
    if not check_subscription(user_id):
        send_subscription_warning(message.chat.id, user_id)
        return

    if (message.voice.duration or 0) > MAX_VOICE_SECONDS:
        bot.send_message(message.chat.id, get_text(user_id, 'voice_too_long', sec=MAX_VOICE_SECONDS))
        return

    if not use_voice_balance(user_id):
        send_tariff_menu(message.chat.id, user_id)
        return

    wait_msg = bot.send_message(message.chat.id, get_text(user_id, 'voice_listening'))

    def _translate():
        file_info = bot.get_file(message.voice.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        return translate_audio(downloaded_file, target_lang=get_user_lang(user_id))

    if not deliver_translation(message.chat.id, user_id, wait_msg, _translate):
        add_voice_balance(user_id, 1)  # xato bo'lsa limit qaytariladi


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
    elif text == "⚙️ Admin" and is_admin(user_id):
        admin_panel(message)
        return

    if not check_subscription(user_id):
        send_subscription_warning(message.chat.id, user_id)
        return

    if len(text) > MAX_TEXT_LENGTH:
        bot.send_message(message.chat.id, get_text(user_id, 'text_too_long', limit=MAX_TEXT_LENGTH))
        return
    limited = rate_limit_message(user_id)
    if limited:
        bot.send_message(message.chat.id, limited)
        return

    wait_msg = bot.send_message(message.chat.id, get_text(user_id, 'translating'))
    deliver_translation(message.chat.id, user_id, wait_msg,
                        lambda: translate_text(text, target_lang=get_user_lang(user_id)))


# --- HTTP server: Railway health-check + Mini App (webapp/index.html) ---
WEBAPP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'webapp')


class WebHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split('?')[0]
        index_path = os.path.join(WEBAPP_DIR, 'index.html')
        if path in ('/', '/index.html') and os.path.exists(index_path):
            with open(index_path, 'rb') as f:
                body = f.read()
            ctype = 'text/html; charset=utf-8'
        elif path in ('/', '/health'):
            body, ctype = b"Bot ishladi!", 'text/plain; charset=utf-8'
        else:
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    server = ThreadingHTTPServer(('0.0.0.0', port), WebHandler)
    server.serve_forever()


if __name__ == '__main__':
    threading.Thread(target=run_web_server, daemon=True).start()
    log.info("Bot ishga tushdi! Mini App: %s", WEBAPP_URL or "(sozlanmagan)")
    bot.infinity_polling(timeout=20, long_polling_timeout=20)

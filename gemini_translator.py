import os
import base64
import logging
import threading

import requests

log = logging.getLogger(__name__)

API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
# Model nomini Railway Variables orqali almashtirish mumkin
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
GEMINI_FALLBACK_MODEL = os.getenv("GEMINI_FALLBACK_MODEL", "gemini-3.5-flash")
# (ulanish, javob kutish) soniyalarda — Gemini "osilib" qolsa bot qotib qolmasligi uchun
TIMEOUT = (10, int(os.getenv("GEMINI_TIMEOUT", "90")))

_local = threading.local()


class TranslationError(Exception):
    """Foydalanuvchiga texnik tafsilotlarsiz ko'rsatiladigan xato."""


def _session():
    # requests.Session thread-safe emas — har bir thread uchun alohida
    if not hasattr(_local, "session"):
        _local.session = requests.Session()
    return _local.session


def _generate(parts):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise TranslationError("GEMINI_API_KEY topilmadi!")

    # Kalit URL da emas, sarlavhada: xato matnlarida va loglarda ko'rinmaydi
    headers = {"Content-Type": "application/json", "x-goog-api-key": api_key}
    payload = {"contents": [{"parts": parts}]}

    last_error = None
    for model in (GEMINI_MODEL, GEMINI_FALLBACK_MODEL):
        if not model:
            continue
        try:
            response = _session().post(f"{API_BASE}/{model}:generateContent",
                                       headers=headers, json=payload, timeout=TIMEOUT)
        except requests.RequestException as e:
            log.warning("Gemini (%s) tarmoq xatosi: %s", model, type(e).__name__)
            last_error = e
            continue

        if response.status_code in (429, 500, 503, 504):
            # Yuklama yuqori — zaxira modelga o'tamiz
            log.warning("Gemini (%s) HTTP %s", model, response.status_code)
            last_error = response.status_code
            continue
        if response.status_code != 200:
            log.error("Gemini (%s) HTTP %s: %s", model, response.status_code, response.text[:300])
            raise TranslationError("Gemini so'rovni qabul qilmadi")

        try:
            data = response.json()
            return "".join(p.get("text", "") for p in data["candidates"][0]["content"]["parts"]).strip()
        except (KeyError, IndexError, ValueError):
            log.error("Gemini kutilmagan javob: %s", str(response.text)[:300])
            raise TranslationError("Gemini javob bermadi (matn bloklangan bo'lishi mumkin)")

    raise TranslationError(f"Gemini hozir band ({last_error})")


def translate_text(text: str, target_lang: str = "O'zbek") -> str:
    """
    Matnni qabul qilib, uni Gemini API orqali ko'rsatilgan tilga tarjima qiladi.
    """
    prompt = f"""
    Iltimos, ushbu so'z yoki gapni {target_lang} tiliga tarjima qilib tahlil qiling.
    Barcha tushuntirishlar va javoblarni aynan {target_lang} tilida yozing!
    Javob har doim quyidagi tuzilmada bo'lsin (Sarlavhalarni ham {target_lang} tiliga o'giring):

    > 🎯 **Asosiy tarjima:** ...
    > 🧠 **Kontekst / Ma'nosi:** ...
    > 📊 **Darajasi:** ...
    > 🔄 **Boshqa ma'nolari:** ...
    > 📝 **Misol:** ...

    Matn: "{text}"
    """
    return _generate([{"text": prompt}])


def translate_audio(audio_bytes: bytes, target_lang: str = "O'zbek") -> str:
    """
    Ovozli xabarni (audio_bytes) Gemini API orqali tarjima qiladi.
    """
    encoded_audio = base64.b64encode(audio_bytes).decode('utf-8')

    prompt = f"""
    Iltimos, ushbu ovozli xabarni diqqat bilan eshiting va unda aytilgan so'z yoki gapni {target_lang} tiliga tarjima qilib tahlil qiling.
    Barcha tushuntirishlar va javoblarni aynan {target_lang} tilida yozing!
    Javob har doim quyidagi tuzilmada bo'lsin (Sarlavhalarni ham {target_lang} tiliga o'giring):

    > 🎯 **Asosiy tarjima:** ...
    > 🧠 **Kontekst / Ma'nosi:** ...
    > 📊 **Darajasi:** ...
    > 🔄 **Boshqa ma'nolari:** ...
    > 📝 **Misol:** ...
    """
    return _generate([
        {"text": prompt},
        {"inlineData": {"mimeType": "audio/ogg", "data": encoded_audio}},
    ])

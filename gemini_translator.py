import os
import requests

def translate_text(text: str) -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY topilmadi!")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
import base64

def translate_text(text: str, target_lang: str = "O'zbek") -> str:
    """
    Matnni qabul qilib, uni Gemini API orqali ko'rsatilgan tilga tarjima qiladi.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY topilmadi!")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    
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
    
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        return data['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        print(f"Gemini API xatosi: {e}")
        raise e

def translate_audio(audio_bytes: bytes, target_lang: str = "O'zbek") -> str:
    """
    Ovozli xabarni (audio_bytes) Gemini API orqali tarjima qiladi.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY topilmadi!")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    
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
    
    payload = {
        "contents": [{
            "parts": [
                {"text": prompt},
                {
                    "inlineData": {
                        "mimeType": "audio/ogg",
                        "data": encoded_audio
                    }
                }
            ]
        }]
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        return data['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        print(f"Gemini Audio API xatosi: {e}")
        raise e

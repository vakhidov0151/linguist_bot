import os
import requests

def translate_text(text: str) -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY topilmadi!")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    
    prompt = f"""
Siz "Aqlli Tilshunos" (Linguist) botsiz. Siz istalgan tillar orasida tarjima qila olasiz.
Foydalanuvchi sizga quyidagi xabarni yubordi: "{text}"

Vazifangiz:
1. Foydalanuvchi qaysi tillar orasida tarjima so'rayotganini xabarning o'zidan aniqlash. Agar aniq aytilmagan bo'lsa, xorijiy tildan o'zbek tiliga (yoki o'zbek tilidan ingliz tiliga) tarjima qiling. Masalan foydalanuvchi "rus tilidan xitoy tiliga tarjima qil: ..." desa, shu tillarda tarjima qilasiz. "koreyschadan ispanchaga" desa shunday qilasiz.
2. Quyidagi formatda Markdown yordamida chiroyli qilib javob qaytaring. Sarlavhalarni va emojilarni aynan saqlab qoling:

> **Foydalanuvchi yuborgan so'z/matn:** [So'z yoki Matn]
> 
> 🎯 **Asosiy tarjima:** [Asosiy tarjimasi]
> 🧠 **Kontekst / Ma'nosi:** [Qisqacha tushuntirish va kontekst]
> 📊 **Darajasi:** [A1/B2/C1 va hokazo, agar qisqa so'z bo'lsa]
> 🔄 **Boshqa ma'nolari:** 
> 1. ...
> 2. ...
> 
> 📝 **Misol:** "[Asl tildagi misol]" ([Tarjima qilingan misol])

Javobingiz faqat shu formatda bo'lishi kerak. Qo'shimcha gaplar yoki salomlashishlar yozmang.
"""
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    data = response.json()
    return data['candidates'][0]['content']['parts'][0]['text']

def translate_with_langs(text: str, source: str, target: str) -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY topilmadi!")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.6-flash:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    
    source_str = "avtomatik aniqlangan til" if source == "Auto" else source

    prompt = f"""
Siz "Aqlli Tilshunos" (Linguist) botsiz. 
Iltimos, quyidagi matnni {source_str} tilidan {target} tiliga tarjima qiling: "{text}"

Quyidagi formatda Markdown yordamida chiroyli qilib javob qaytaring:

> **Foydalanuvchi yuborgan so'z/matn:** {text}
> 
> 🎯 **Asosiy tarjima:** [Asosiy tarjimasi]
> 🧠 **Kontekst / Ma'nosi:** [Qisqacha tushuntirish va kontekst]
> 📊 **Darajasi:** [A1/B2/C1 va hokazo, agar qisqa so'z bo'lsa]
> 🔄 **Boshqa ma'nolari:** 
> 1. ...
> 2. ...
> 
> 📝 **Misol:** "[Asl tildagi misol]" ([Tarjima qilingan misol])

Javobingiz faqat shu formatda bo'lishi kerak.
"""
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    data = response.json()
    return data['candidates'][0]['content']['parts'][0]['text']

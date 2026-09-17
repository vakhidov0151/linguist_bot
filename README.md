# Linguist AI 🤖🌍

Aqlli va ko'p tilli Telegram bot va Telegram Mini App. Bu bot oddiy tarjimondan farqli o'laroq, so'zlarni nafaqat tarjima qiladi, balki ularning darajasini (A1, B2, C1), kontekstini va qo'shimcha ma'nolarini misollar bilan tushuntirib beradi.

## Imkoniyatlari 🚀
- **Aqlli Tarjima:** Matnni qaysi ma'noda kelayotganini tushunib tarjima qiladi.
- **Telegram Mini App:** Zamonaviy "Glassmorphism" uslubidagi ichki oyna orqali tillarni qulay tanlash imkoniyati.
- **Ko'p tilli qo'llab-quvvatlash:** O'zbek, Ingliz, Rus, Arab, Xitoy, Koreys, Ispan va Turk tillari.
- **Gemini AI:** Google'ning eng so'nggi `Gemini 3.6 Flash` sun'iy intellekt modeli asosida ishlaydi.

## O'rnatish 🛠️

1. Ushbu repozitoriyni yuklab oling:
```bash
git clone https://github.com/SizningUsername/Linguist-AI.git
cd Linguist-AI
```

2. Kerakli kutubxonalarni o'rnating:
```bash
pip install -r requirements.txt
```

3. `.env` faylini yarating va o'z ma'lumotlaringizni kiriting:
```env
TELEGRAM_BOT_TOKEN=sizning_telegram_tokeningiz
GEMINI_API_KEY=sizning_gemini_api_kalitingiz
WEBAPP_URL=https://sizning_saytingiz.netlify.app/
```

4. Botni ishga tushiring:
```bash
python bot.py
```

## Mini App'ni ishga tushirish (Frontend) 🌐
`webapp/index.html` faylini **Netlify**, **GitHub Pages** yoki **Vercel** kabi xizmatlarga bepul yuklashingiz va olingan ssilkani `.env` dagi `WEBAPP_URL` qismiga yozishingiz kifoya.

## Texnologiyalar
- Python 3
- pyTelegramBotAPI (Telebot)
- Gemini REST API
- HTML / CSS / JS (Frontend uchun)

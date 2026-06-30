# 🩰 Noza | Study Blog — Telegram Bot

Railway.app orqali deploy qilish uchun qo'llanma.

## 📁 Fayllar

| Fayl | Vazifasi |
|---|---|
| `bot.py` | Asosiy bot kodi |
| `requirements.txt` | Python kutubxonalari |
| `Procfile` | Railway'ga botni qanday ishga tushirishni aytadi |
| `runtime.txt` | Python versiyasi |
| `.env.example` | Kerakli environment variable'lar namunasi |

---

## 🚀 Railway'ga deploy qilish (qadam-baqadam)

### 1) GitHub'ga yuklash
Bu papkadagi barcha fayllarni yangi GitHub repo'siga yuklang (yoki Railway orqali to'g'ridan-to'g'ri papkani yuklash mumkin).

### 2) Railway'da yangi loyiha yarating
1. https://railway.app ga kiring
2. **New Project** → **Deploy from GitHub repo**
3. Repo'ingizni tanlang

### 3) Environment Variables qo'shing
Railway loyihangizda **Variables** bo'limiga o'ting va quyidagilarni qo'shing:

```
BOT_TOKEN=sizning_bot_tokeningiz
CHANNEL_ID=@nozastudyarea
ADMIN_IDS=7542964116
```

> 🔑 **BOT_TOKEN** ni @BotFather'dan oling (`/newbot` yoki mavjud bot tokeni)

### 4) Persistent Volume qo'shish (DB saqlanishi uchun) — TAVSIYA ETILADI
Railway konteynerlari qayta ishga tushganda fayllar o'chib ketishi mumkin. Database yo'qolmasligi uchun:

1. Railway loyihangizda **Settings** → **Volumes** ga o'ting
2. **New Volume** bosing, mount path: `/data`
3. Variables bo'limiga qo'shing:
   ```
   DB_PATH=/data/noza_bot.db
   ```

### 5) Deploy
Railway avtomatik ravishda `requirements.txt` o'rnatadi va `Procfile` asosida botni ishga tushiradi. Loglarni **Deployments** bo'limidan kuzatishingiz mumkin.

Muvaffaqiyatli ishga tushsa, logda quyidagini ko'rasiz:
```
🩰 Noza Study Blog Bot ishga tushdi...
```

---

## ⚙️ Bot sozlamalari (allaqachon kiritilgan)

- **Admin ID:** `7542964116`
- **Kanal:** `@nozastudyarea` (https://t.me/nozastudyarea)

Agar keyinchalik o'zgartirish kerak bo'lsa — buni kodda emas, Railway'ning **Variables** bo'limida o'zgartirsangiz bo'ladi, qayta deploy qilish shart emas (faqat **Restart** qiling).

---

## 🤖 Botni sinash

1. Botingizga `/start` yuboring
2. Kanalga obuna bo'lmagan bo'lsangiz, obuna so'raladi
3. Obuna bo'lgach, asosiy menyu chiqadi
4. Admin sifatida **⚙️ Admin Panel** tugmasi ko'rinadi (chunki ID mos keladi)

## ❗ Eslatma

- Bot kodida hech qanday maxfiy ma'lumot (token) yozilmagan — hammasi Railway Variables orqali beriladi, bu xavfsizroq.
- `.env.example` faqat namuna, haqiqiy `.env` faylni Railway'ga yuklamang — token'ni Variables orqali kiriting.

import telebot
import sqlite3
import os
import json
import random
from datetime import datetime, time
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

# ══════════════════════════════════════════════════════════════
#  CONFIG – bularni o'zingiznikiga almashtiring
# ══════════════════════════════════════════════════════════════
BOT_TOKEN   = os.environ.get("BOT_TOKEN", "")
CHANNEL_ID  = os.environ.get("CHANNEL_ID", "@nozastudyarea")
ADMIN_IDS   = [int(x) for x in os.environ.get("ADMIN_IDS", "7542964116").split(",")]

bot = telebot.TeleBot(BOT_TOKEN)

# Railway'da persistent volume ulasangiz shu yerga saqlanadi (masalan /data)
DB_PATH = os.environ.get("DB_PATH", "noza_bot.db")

# ══════════════════════════════════════════════════════════════
#  DATABASE SETUP
# ══════════════════════════════════════════════════════════════
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS users (
        user_id     INTEGER PRIMARY KEY,
        username    TEXT,
        full_name   TEXT,
        joined_at   TEXT,
        referrer_id INTEGER DEFAULT NULL,
        referral_count INTEGER DEFAULT 0,
        badge       TEXT DEFAULT NULL,
        is_subscribed INTEGER DEFAULT 0
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS content (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        title       TEXT,
        category    TEXT,
        content_type TEXT,   -- 'pdf', 'photo', 'link'
        file_id     TEXT,    -- Telegram file_id yoki URL
        description TEXT,
        added_at    TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS quotes (
        id      INTEGER PRIMARY KEY AUTOINCREMENT,
        text    TEXT,
        author  TEXT DEFAULT 'Noza | Study Blog'
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS broadcast_log (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        message     TEXT,
        sent_at     TEXT,
        sent_count  INTEGER
    )""")

    # Default motivatsion iqtiboslar
    default_quotes = [
        ("Nothing feel better than working on yourself! 🩰", "Noza"),
        ("Har bir daqiqang qimmat – uni o'qishga sarf qil! ✨", "Noza | Study Blog"),
        ("Study hard in silence, let success make the noise. 📚", "Noza"),
        ("Til o'rganish – dunyoni ochishdir! 🌍", "Noza | Study Blog"),
        ("Consistency is the key to mastery. 🔑", "Noza"),
        ("Bugun o'qimasang, ertaga afsus qilasan. 💪", "Noza | Study Blog"),
        ("Dream big, study harder! 🎯", "Noza"),
        ("Har bir yangi so'z – yangi imkoniyat! 🇰🇷🇺🇸", "Noza | Study Blog"),
    ]
    c.executemany("INSERT OR IGNORE INTO quotes (text, author) VALUES (?,?)", default_quotes)
    conn.commit()
    conn.close()

def get_conn():
    return sqlite3.connect(DB_PATH)

# ══════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════
def is_admin(user_id):
    return user_id in ADMIN_IDS

def check_subscription(user_id):
    try:
        member = bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

def register_user(user, referrer_id=None):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT user_id FROM users WHERE user_id=?", (user.id,))
    exists = c.fetchone()
    if not exists:
        c.execute("""INSERT INTO users (user_id, username, full_name, joined_at, referrer_id)
                     VALUES (?,?,?,?,?)""",
                  (user.id,
                   user.username or "",
                   user.first_name + (" " + user.last_name if user.last_name else ""),
                   datetime.now().strftime("%Y-%m-%d %H:%M"),
                   referrer_id))
        # Referrer ga +1
        if referrer_id:
            c.execute("UPDATE users SET referral_count = referral_count + 1 WHERE user_id=?", (referrer_id,))
            check_and_assign_badge(c, referrer_id)
        conn.commit()
    conn.close()
    return not exists  # True = yangi foydalanuvchi

def check_and_assign_badge(c, user_id):
    c.execute("SELECT referral_count, badge FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    if not row:
        return
    count, current_badge = row
    if count >= 20 and current_badge != "🏆 Legend":
        c.execute("UPDATE users SET badge='🏆 Legend' WHERE user_id=?", (user_id,))
    elif count >= 10 and current_badge not in ["🥇 Pro", "🏆 Legend"]:
        c.execute("UPDATE users SET badge='🥇 Pro' WHERE user_id=?", (user_id,))
    elif count >= 5 and current_badge not in ["🥈 Rising Star", "🥇 Pro", "🏆 Legend"]:
        c.execute("UPDATE users SET badge='🥈 Rising Star' WHERE user_id=?", (user_id,))
    elif count >= 1 and current_badge is None:
        c.execute("UPDATE users SET badge='🥉 Starter' WHERE user_id=?", (user_id,))

def get_user(user_id):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row

def get_random_quote():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT text, author FROM quotes ORDER BY RANDOM() LIMIT 1")
    row = c.fetchone()
    conn.close()
    return row if row else ("Keep studying! 💪", "Noza | Study Blog")

# ══════════════════════════════════════════════════════════════
#  KEYBOARDS
# ══════════════════════════════════════════════════════════════
def main_menu(user_id):
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(KeyboardButton("📚 Study Content"), KeyboardButton("💡 Kunlik Iqtibos"))
    kb.row(KeyboardButton("👥 Referral"), KeyboardButton("👤 Mening Profilim"))
    kb.row(KeyboardButton("ℹ️ Kanal Haqida"))
    if is_admin(user_id):
        kb.row(KeyboardButton("⚙️ Admin Panel"))
    return kb

def admin_menu():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(KeyboardButton("📤 Content Qo'shish"), KeyboardButton("📢 Broadcast"))
    kb.row(KeyboardButton("📊 Statistika"), KeyboardButton("💬 Iqtibos Qo'shish"))
    kb.row(KeyboardButton("👥 Foydalanuvchilar"), KeyboardButton("🔙 Orqaga"))
    return kb

def content_category_kb():
    kb = InlineKeyboardMarkup()
    kb.row(InlineKeyboardButton("📄 PDF Fayllar", callback_data="cat_pdf"),
           InlineKeyboardButton("🖼 Rasmlar", callback_data="cat_photo"))
    kb.row(InlineKeyboardButton("🔗 Havolalar", callback_data="cat_link"),
           InlineKeyboardButton("📋 Hammasi", callback_data="cat_all"))
    return kb

def sub_check_kb():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("📢 Kanalga O'tish", url=f"https://t.me/{CHANNEL_ID.lstrip('@')}"))
    kb.add(InlineKeyboardButton("✅ Tekshirish", callback_data="check_sub"))
    return kb

# ══════════════════════════════════════════════════════════════
#  /start
# ══════════════════════════════════════════════════════════════
@bot.message_handler(commands=["start"])
def start(msg):
    args = msg.text.split()
    referrer_id = None
    if len(args) > 1 and args[1].startswith("ref_"):
        try:
            referrer_id = int(args[1][4:])
            if referrer_id == msg.from_user.id:
                referrer_id = None
        except:
            referrer_id = None

    is_new = register_user(msg.from_user, referrer_id)

    # Obuna tekshiruv
    if not check_subscription(msg.from_user.id):
        bot.send_message(msg.chat.id,
            "💗 Assalomu alaykum! *Noza | Study Blog* botiga xush kelibsiz!\n\n"
            "Botdan foydalanish uchun avval kanalimizga obuna bo'ling 👇",
            parse_mode="Markdown", reply_markup=sub_check_kb())
        return

    welcome = (
        f"🩰 Salom, *{msg.from_user.first_name}*!\n\n"
        f"*Noza | Study Blog* botiga xush kelibsiz ✨\n\n"
        f"📚 Bu yerda siz:\n"
        f"• Study materiallar yuklab olishingiz\n"
        f"• Kunlik motivatsion iqtiboslar olishingiz\n"
        f"• Do'stlaringizni taklif qilib badge yig'ishingiz mumkin!\n\n"
        f"_Nothing feel better than working on yourself!_ 💪"
    )
    if is_new and referrer_id:
        welcome += f"\n\n🎉 Siz do'stingiz taklifi orqali keldingiz!"

    bot.send_message(msg.chat.id, welcome, parse_mode="Markdown",
                     reply_markup=main_menu(msg.from_user.id))

# ══════════════════════════════════════════════════════════════
#  OBUNA TEKSHIRUV callback
# ══════════════════════════════════════════════════════════════
@bot.callback_query_handler(func=lambda c: c.data == "check_sub")
def check_sub_callback(call):
    if check_subscription(call.from_user.id):
        bot.answer_callback_query(call.id, "✅ Rahmat! Obuna tasdiqlandi.")
        bot.delete_message(call.message.chat.id, call.message.message_id)
        # /start ga qayta yo'naltirish
        bot.send_message(call.message.chat.id,
            f"🩰 Salom, *{call.from_user.first_name}*!\n\n"
            f"*Noza | Study Blog* botiga xush kelibsiz ✨\n\n"
            f"Quyidagi menyudan tanlang 👇",
            parse_mode="Markdown", reply_markup=main_menu(call.from_user.id))
    else:
        bot.answer_callback_query(call.id, "❌ Siz hali obuna bo'lmagansiz!", show_alert=True)

# ══════════════════════════════════════════════════════════════
#  📚 STUDY CONTENT
# ══════════════════════════════════════════════════════════════
@bot.message_handler(func=lambda m: m.text == "📚 Study Content")
def study_content(msg):
    if not check_subscription(msg.from_user.id):
        bot.send_message(msg.chat.id, "❌ Avval kanalga obuna bo'ling!", reply_markup=sub_check_kb())
        return
    bot.send_message(msg.chat.id,
        "📚 *Study Content*\n\nQaysi turdagi materiallarni ko'rmoqchisiz?",
        parse_mode="Markdown", reply_markup=content_category_kb())

@bot.callback_query_handler(func=lambda c: c.data.startswith("cat_"))
def show_content(call):
    cat = call.data[4:]  # pdf, photo, link, all
    conn = get_conn()
    c = conn.cursor()
    if cat == "all":
        c.execute("SELECT id, title, category, content_type, description FROM content ORDER BY added_at DESC LIMIT 10")
    else:
        c.execute("SELECT id, title, category, content_type, description FROM content WHERE content_type=? ORDER BY added_at DESC LIMIT 10", (cat,))
    rows = c.fetchall()
    conn.close()

    if not rows:
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id,
            "📭 Hozircha bu kategoriyada kontent yo'q.\nTez orada qo'shiladi! ✨")
        return

    bot.answer_callback_query(call.id)
    kb = InlineKeyboardMarkup()
    for row in rows:
        icon = {"pdf": "📄", "photo": "🖼", "link": "🔗"}.get(row[3], "📎")
        kb.add(InlineKeyboardButton(f"{icon} {row[1]}", callback_data=f"content_{row[0]}"))
    bot.send_message(call.message.chat.id, "📋 Mavjud materiallar:", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("content_"))
def send_content(call):
    content_id = int(call.data[8:])
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM content WHERE id=?", (content_id,))
    row = c.fetchone()
    conn.close()

    if not row:
        bot.answer_callback_query(call.id, "❌ Kontent topilmadi")
        return

    _, title, category, ctype, file_id, desc, _ = row
    bot.answer_callback_query(call.id)

    caption = f"📌 *{title}*\n🏷 Kategoriya: {category}\n\n{desc or ''}"
    try:
        if ctype == "pdf":
            bot.send_document(call.message.chat.id, file_id, caption=caption, parse_mode="Markdown")
        elif ctype == "photo":
            bot.send_photo(call.message.chat.id, file_id, caption=caption, parse_mode="Markdown")
        elif ctype == "link":
            bot.send_message(call.message.chat.id, f"{caption}\n\n🔗 {file_id}", parse_mode="Markdown")
    except Exception as e:
        bot.send_message(call.message.chat.id, f"❌ Yuborishda xatolik: {e}")

# ══════════════════════════════════════════════════════════════
#  💡 KUNLIK IQTIBOS
# ══════════════════════════════════════════════════════════════
@bot.message_handler(func=lambda m: m.text == "💡 Kunlik Iqtibos")
def daily_quote(msg):
    quote, author = get_random_quote()
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🔄 Boshqa iqtibos", callback_data="new_quote"))
    bot.send_message(msg.chat.id,
        f"✨ *Kunlik Motivatsiya*\n\n"
        f"_{quote}_\n\n"
        f"— *{author}* 🩰",
        parse_mode="Markdown", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data == "new_quote")
def new_quote(call):
    quote, author = get_random_quote()
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🔄 Boshqa iqtibos", callback_data="new_quote"))
    bot.edit_message_text(
        f"✨ *Kunlik Motivatsiya*\n\n"
        f"_{quote}_\n\n"
        f"— *{author}* 🩰",
        call.message.chat.id, call.message.message_id,
        parse_mode="Markdown", reply_markup=kb)
    bot.answer_callback_query(call.id)

# ══════════════════════════════════════════════════════════════
#  👥 REFERRAL
# ══════════════════════════════════════════════════════════════
@bot.message_handler(func=lambda m: m.text == "👥 Referral")
def referral(msg):
    user = get_user(msg.from_user.id)
    if not user:
        register_user(msg.from_user)
        user = get_user(msg.from_user.id)

    ref_link = f"https://t.me/{bot.get_me().username}?start=ref_{msg.from_user.id}"
    count = user[5]  # referral_count
    badge = user[6] or "Hali yo'q"

    badge_info = (
        "🥉 *Starter* – 1+ do'st\n"
        "🥈 *Rising Star* – 5+ do'st\n"
        "🥇 *Pro* – 10+ do'st\n"
        "🏆 *Legend* – 20+ do'st"
    )

    bot.send_message(msg.chat.id,
        f"👥 *Referral Tizimi*\n\n"
        f"🔗 Sizning havolangiz:\n`{ref_link}`\n\n"
        f"📊 Taklif qilganlar: *{count}* kishi\n"
        f"🏅 Sizning badge'ingiz: *{badge}*\n\n"
        f"🎖 Badge darajalari:\n{badge_info}\n\n"
        f"_Do'stlaringizni taklif qiling va badge yig'ing!_ ✨",
        parse_mode="Markdown")

# ══════════════════════════════════════════════════════════════
#  👤 PROFIL
# ══════════════════════════════════════════════════════════════
@bot.message_handler(func=lambda m: m.text == "👤 Mening Profilim")
def my_profile(msg):
    user = get_user(msg.from_user.id)
    if not user:
        register_user(msg.from_user)
        user = get_user(msg.from_user.id)

    uid, uname, fname, joined, ref_by, ref_count, badge, is_sub = user
    sub_status = "✅ Obunachi" if check_subscription(uid) else "❌ Obuna emas"
    badge_display = badge or "Hali yo'q (do'st taklif qiling!)"

    bot.send_message(msg.chat.id,
        f"👤 *Mening Profilim*\n\n"
        f"📛 Ism: *{fname}*\n"
        f"🆔 ID: `{uid}`\n"
        f"📅 Qo'shilgan: {joined}\n"
        f"📢 Kanal: {sub_status}\n"
        f"👥 Taklif qilganlar: *{ref_count}* kishi\n"
        f"🏅 Badge: *{badge_display}*",
        parse_mode="Markdown")

# ══════════════════════════════════════════════════════════════
#  ℹ️ KANAL HAQIDA
# ══════════════════════════════════════════════════════════════
@bot.message_handler(func=lambda m: m.text == "ℹ️ Kanal Haqida")
def about(msg):
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("📢 Kanalga O'tish", url=f"https://t.me/{CHANNEL_ID.lstrip('@')}"))
    kb.add(InlineKeyboardButton("💬 Reklama uchun", url="https://t.me/imnozadan"))
    bot.send_message(msg.chat.id,
        "🩰 *Noza | Study Blog*\n\n"
        "_Nothing feel better than working on yourself!_\n\n"
        "👧 17 y.o | Polyglot qiz\n"
        "🇺🇸 English B2 | 🇺🇿 Uzbek B\n"
        "🇷🇺 Russian B2 | 🇹🇷 Turkish C1\n"
        "🇰🇷 Topik 4 | Loading ~ SAT, IELTS\n\n"
        "📚 Study maslahatlar\n"
        "🎬 Vloglar\n"
        "📝 Til o'rganish sirlari\n\n"
        "📩 Reklama: @imnozadan",
        parse_mode="Markdown", reply_markup=kb)

# ══════════════════════════════════════════════════════════════
#  ⚙️ ADMIN PANEL
# ══════════════════════════════════════════════════════════════
@bot.message_handler(func=lambda m: m.text == "⚙️ Admin Panel" and is_admin(m.from_user.id))
def admin_panel(msg):
    bot.send_message(msg.chat.id, "⚙️ *Admin Panel*\nXush kelibsiz!",
                     parse_mode="Markdown", reply_markup=admin_menu())

@bot.message_handler(func=lambda m: m.text == "🔙 Orqaga" and is_admin(m.from_user.id))
def back_to_main(msg):
    bot.send_message(msg.chat.id, "🏠 Bosh menyu", reply_markup=main_menu(msg.from_user.id))

# ── STATISTIKA ─────────────────────────────────────────────────
@bot.message_handler(func=lambda m: m.text == "📊 Statistika" and is_admin(m.from_user.id))
def statistics(msg):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM content")
    total_content = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM users WHERE referral_count > 0")
    active_refs = c.fetchone()[0]
    c.execute("SELECT full_name, referral_count, badge FROM users ORDER BY referral_count DESC LIMIT 5")
    top_refs = c.fetchall()
    conn.close()

    top_text = ""
    for i, (name, cnt, badge) in enumerate(top_refs, 1):
        b = badge or "—"
        top_text += f"{i}. {name} – {cnt} ta ({b})\n"

    bot.send_message(msg.chat.id,
        f"📊 *Bot Statistikasi*\n\n"
        f"👥 Jami foydalanuvchilar: *{total_users}*\n"
        f"📚 Jami kontent: *{total_content}*\n"
        f"🔗 Referral faol: *{active_refs}* kishi\n\n"
        f"🏆 *Top 5 Referral:*\n{top_text or 'Hali yo\'q'}",
        parse_mode="Markdown")

# ── FOYDALANUVCHILAR RO'YXATI ──────────────────────────────────
@bot.message_handler(func=lambda m: m.text == "👥 Foydalanuvchilar" and is_admin(m.from_user.id))
def list_users(msg):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT user_id, full_name, username, joined_at FROM users ORDER BY joined_at DESC LIMIT 20")
    rows = c.fetchall()
    conn.close()

    text = "👥 *So'nggi 20 foydalanuvchi:*\n\n"
    for uid, name, uname, joined in rows:
        uname_str = f"@{uname}" if uname else "—"
        text += f"• {name} ({uname_str})\n  🕐 {joined}\n"

    bot.send_message(msg.chat.id, text, parse_mode="Markdown")

# ── BROADCAST ─────────────────────────────────────────────────
user_states = {}  # user_id: state

@bot.message_handler(func=lambda m: m.text == "📢 Broadcast" and is_admin(m.from_user.id))
def broadcast_start(msg):
    user_states[msg.from_user.id] = "broadcast"
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("❌ Bekor qilish"))
    bot.send_message(msg.chat.id,
        "📢 *Broadcast*\n\nBarcha foydalanuvchilarga yuboriladigan xabarni yozing:\n"
        "(matn, rasm yoki fayl yuborishingiz mumkin)",
        parse_mode="Markdown", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == "💬 Iqtibos Qo'shish" and is_admin(m.from_user.id))
def add_quote_start(msg):
    user_states[msg.from_user.id] = "add_quote"
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton("❌ Bekor qilish"))
    bot.send_message(msg.chat.id,
        "💬 *Yangi iqtibos qo'shish*\n\nFormatda yozing:\n`Iqtibos matni | Muallif`\n\nMasalan:\n`Study hard, dream big! | Noza`",
        parse_mode="Markdown", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == "📤 Content Qo'shish" and is_admin(m.from_user.id))
def add_content_start(msg):
    user_states[msg.from_user.id] = "add_content_type"
    kb = InlineKeyboardMarkup()
    kb.row(InlineKeyboardButton("📄 PDF", callback_data="addtype_pdf"),
           InlineKeyboardButton("🖼 Rasm", callback_data="addtype_photo"))
    kb.add(InlineKeyboardButton("🔗 Havola", callback_data="addtype_link"))
    bot.send_message(msg.chat.id, "📤 *Kontent Qo'shish*\n\nTurini tanlang:",
                     parse_mode="Markdown", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("addtype_"))
def add_content_type(call):
    ctype = call.data[8:]
    user_states[call.from_user.id] = f"add_content_{ctype}"
    bot.answer_callback_query(call.id)
    if ctype == "link":
        bot.send_message(call.message.chat.id,
            "🔗 Format:\n`Sarlavha | Kategoriya | Havola | Tavsif`\n\nMasalan:\n`IELTS Resources | English | https://example.com | Foydali sayt`",
            parse_mode="Markdown")
    else:
        icon = "📄" if ctype == "pdf" else "🖼"
        bot.send_message(call.message.chat.id,
            f"{icon} Faylni yuboring va caption'ga yozing:\n`Sarlavha | Kategoriya | Tavsif`\n\nMasalan:\n`IELTS PDF | English | Foydali material`",
            parse_mode="Markdown")

# ── STATE HANDLER ──────────────────────────────────────────────
@bot.message_handler(func=lambda m: m.from_user.id in user_states,
                     content_types=["text","document","photo"])
def handle_state(msg):
    uid = msg.from_user.id
    state = user_states.get(uid)

    if msg.text == "❌ Bekor qilish":
        user_states.pop(uid, None)
        bot.send_message(msg.chat.id, "❌ Bekor qilindi.", reply_markup=admin_menu())
        return

    # BROADCAST
    if state == "broadcast":
        conn = get_conn()
        c = conn.cursor()
        c.execute("SELECT user_id FROM users")
        all_users = c.fetchall()
        conn.close()

        sent = 0
        for (u_id,) in all_users:
            try:
                if msg.content_type == "text":
                    bot.send_message(u_id, msg.text)
                elif msg.content_type == "document":
                    bot.send_document(u_id, msg.document.file_id,
                                      caption=msg.caption or "")
                elif msg.content_type == "photo":
                    bot.send_photo(u_id, msg.photo[-1].file_id,
                                   caption=msg.caption or "")
                sent += 1
            except:
                pass

        conn = get_conn()
        c = conn.cursor()
        c.execute("INSERT INTO broadcast_log (message, sent_at, sent_count) VALUES (?,?,?)",
                  (msg.text or msg.caption or "[media]",
                   datetime.now().strftime("%Y-%m-%d %H:%M"), sent))
        conn.commit()
        conn.close()

        user_states.pop(uid, None)
        bot.send_message(msg.chat.id,
            f"✅ Broadcast yuborildi!\n👥 Yetib bordi: *{sent}* ta foydalanuvchi",
            parse_mode="Markdown", reply_markup=admin_menu())
        return

    # ADD QUOTE
    if state == "add_quote":
        parts = msg.text.split("|")
        if len(parts) < 2:
            bot.send_message(msg.chat.id, "❌ Format noto'g'ri! `Iqtibos | Muallif` ko'rinishida yozing.")
            return
        quote_text = parts[0].strip()
        author = parts[1].strip()
        conn = get_conn()
        c = conn.cursor()
        c.execute("INSERT INTO quotes (text, author) VALUES (?,?)", (quote_text, author))
        conn.commit()
        conn.close()
        user_states.pop(uid, None)
        bot.send_message(msg.chat.id, f"✅ Iqtibos qo'shildi!\n\n_{quote_text}_\n— *{author}*",
                         parse_mode="Markdown", reply_markup=admin_menu())
        return

    # ADD CONTENT (link)
    if state == "add_content_link":
        parts = msg.text.split("|")
        if len(parts) < 3:
            bot.send_message(msg.chat.id, "❌ Format: `Sarlavha | Kategoriya | Havola | Tavsif`")
            return
        title = parts[0].strip()
        category = parts[1].strip()
        link = parts[2].strip()
        desc = parts[3].strip() if len(parts) > 3 else ""
        conn = get_conn()
        c = conn.cursor()
        c.execute("INSERT INTO content (title, category, content_type, file_id, description, added_at) VALUES (?,?,?,?,?,?)",
                  (title, category, "link", link, desc, datetime.now().strftime("%Y-%m-%d %H:%M")))
        conn.commit()
        conn.close()
        user_states.pop(uid, None)
        bot.send_message(msg.chat.id, f"✅ *{title}* qo'shildi!", parse_mode="Markdown",
                         reply_markup=admin_menu())
        return

    # ADD CONTENT (pdf / photo)
    for ctype in ["pdf", "photo"]:
        if state == f"add_content_{ctype}":
            caption = msg.caption or ""
            parts = caption.split("|")
            title = parts[0].strip() if parts else "Nomsiz"
            category = parts[1].strip() if len(parts) > 1 else "Umumiy"
            desc = parts[2].strip() if len(parts) > 2 else ""

            if ctype == "pdf" and msg.content_type == "document":
                file_id = msg.document.file_id
            elif ctype == "photo" and msg.content_type == "photo":
                file_id = msg.photo[-1].file_id
            else:
                bot.send_message(msg.chat.id, f"❌ {ctype.upper()} fayl yuboring!")
                return

            conn = get_conn()
            c = conn.cursor()
            c.execute("INSERT INTO content (title, category, content_type, file_id, description, added_at) VALUES (?,?,?,?,?,?)",
                      (title, category, ctype, file_id, desc, datetime.now().strftime("%Y-%m-%d %H:%M")))
            conn.commit()
            conn.close()
            user_states.pop(uid, None)
            bot.send_message(msg.chat.id, f"✅ *{title}* qo'shildi!",
                             parse_mode="Markdown", reply_markup=admin_menu())
            return

# ══════════════════════════════════════════════════════════════
#  START
# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("🩰 Noza Study Blog Bot ishga tushdi...")
    init_db()
    bot.infinity_polling(skip_pending=True)

import os
import sqlite3
import zipfile
import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, filters, CallbackQueryHandler, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN")
PASSWORD = "86532"

logging.basicConfig(level=logging.INFO)

conn = sqlite3.Connection('dasi.db', check_same_thread=False)
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    premium_until TEXT,
    referrer INTEGER,
    is_authorized INTEGER DEFAULT 0
)''')
c.execute('''CREATE TABLE IF NOT EXISTS messages (
    msg_id INTEGER, chat_id INTEGER, user_id INTEGER, username TEXT, first_name TEXT,
    text TEXT, caption TEXT, file_id TEXT, file_type TEXT,
    is_view_once INTEGER, timestamp TEXT, old_text TEXT, owner_id INTEGER,
    PRIMARY KEY (msg_id, chat_id, owner_id)
)''')
c.execute('''CREATE TABLE IF NOT EXISTS referals (
    referrer_id INTEGER, referred_id INTEGER, bonus_days INTEGER
)''')
conn.commit()

def save_message(msg, owner_id, is_view_once=False, is_edited=False, old_text=None):
    user = msg.from_user
    file_type = "text"
    file_id = None
    if msg.photo:
        file_type = "photo"
        file_id = msg.photo[-1].file_id
    elif msg.voice:
        file_type = "voice"
        file_id = msg.voice.file_id
    elif msg.video:
        file_type = "video"
        file_id = msg.video.file_id
    elif msg.video_note:
        file_type = "video_note"
        file_id = msg.video_note.file_id
    elif msg.text:
        file_type = "text"
    
    c.execute('INSERT OR REPLACE INTO messages VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
              (msg.message_id, msg.chat_id, user.id, user.username, user.first_name,
               msg.text, msg.caption, file_id, file_type, 1 if is_view_once else 0,
               datetime.now().isoformat(), old_text, owner_id))
    conn.commit()

def is_premium(user_id):
    c.execute('SELECT premium_until FROM users WHERE user_id=?', (user_id,))
    row = c.fetchone()
    if row and row[0]:
        return datetime.fromisoformat(row[0]) > datetime.now()
    return False

def is_authorized(user_id):
    c.execute('SELECT is_authorized FROM users WHERE user_id=?', (user_id,))
    row = c.fetchone()
    return row and row[0] == 1

def add_premium_days(user_id, days):
    c.execute('SELECT premium_until FROM users WHERE user_id=?', (user_id,))
    row = c.fetchone()
    if row and row[0]:
        new_date = datetime.fromisoformat(row[0]) + timedelta(days=days)
    else:
        new_date = datetime.now() + timedelta(days=days)
    c.execute('UPDATE users SET premium_until=? WHERE user_id=?', (new_date.isoformat(), user_id))
    conn.commit()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    c.execute('INSERT OR IGNORE INTO users (user_id, username, first_name, premium_until, is_authorized) VALUES (?,?,?,?,?)',
              (user.id, user.username, user.first_name, (datetime.now() + timedelta(days=7)).isoformat(), 0))
    conn.commit()
    
    # Проверяем реферальный код
    if context.args and context.args[0].startswith("ref_"):
        referrer_id = int(context.args[0].split("_")[1])
        if referrer_id != user.id:
            c.execute('INSERT OR IGNORE INTO referals (referrer_id, referred_id, bonus_days) VALUES (?,?,?)',
                      (referrer_id, user.id, 7))
            add_premium_days(referrer_id, 7)
            conn.commit()
    
    # Клавиатура для пароля
    keyboard = [
        [InlineKeyboardButton("7", c="7"), InlineKeyboardButton("8", c="8"), InlineKeyboardButton("9", c="9")],
        [InlineKeyboardButton("4", c="4"), InlineKeyboardButton("5", c="5"), InlineKeyboardButton("6", c="6")],
        [InlineKeyboardButton("1", c="1"), InlineKeyboardButton("2", c="2"), InlineKeyboardButton("3", c="3")],
        [InlineKeyboardButton("0", c="0"), InlineKeyboardButton("✅", c="submit"), InlineKeyboardButton("🗑", c="clear")]
    ]
    context.user_data['pwd'] = ""
    await update.message.reply_text("🔐 **DAsistent**\n\nВведите пароль для доступа:", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    data = q.data
    
    if data == "clear":
        context.user_data['pwd'] = ""
        await q.edit_message_text("🔐 Очищено", reply_markup=q.message.reply_markup)
    elif data == "submit":
        if context.user_data.get('pwd', "") == PASSWORD:
            c.execute('UPDATE users SET is_authorized=1 WHERE user_id=?', (user_id,))
            conn.commit()
            await q.edit_message_text(f"✅ Добро пожаловать, {q.from_user.first_name}!\n\nБот активирован.", reply_markup=await main_menu())
        else:
            context.user_data['pwd'] = ""
            await q.edit_message_text("❌ Неверный пароль", reply_markup=q.message.reply_markup)
    else:
        context.user_data['pwd'] = context.user_data.get('pwd', "") + data
        await q.edit_message_text(f"🔐 {'*' * len(context.user_data['pwd'])}", reply_markup=q.message.reply_markup)

async def main_menu():
    keyboard = [
        [InlineKeyboardButton("📦 Удалённые", callback_data="deleted"),
         InlineKeyboardButton("✏️ Изменённые", callback_data="edited")],
        [InlineKeyboardButton("👁 View Once", callback_data="viewonce"),
         InlineKeyboardButton("📤 Экспорт", callback_data="export")],
        [InlineKeyboardButton("⭐ Premium", callback_data="pricing"),
         InlineKeyboardButton("👥 Рефералы", callback_data="referrals")],
        [InlineKeyboardButton("🎁 7 дней бесплатно", callback_data="free_trial")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    data = q.data
    
    if not is_authorized(user_id):
        await q.edit_message_text("❌ Сначала авторизуйтесь через /start")
        return
    
    if data == "pricing":
        text = "⭐ **Тарифы DAsistent**\n\n"
        text += "🎁 7 дней бесплатно — для новых пользователей\n\n"
        text += "📆 Неделя — 50 ⭐\n"
        text += "📆 Месяц — 150 ⭐\n"
        text += "📆 Год — 550 ⭐\n\n"
        text += "🔒 Рефералы: +7 дней за каждого друга"
        await q.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Купить", callback_data="buy")]
        ]))
    elif data == "referrals":
        c.execute('SELECT COUNT(*) FROM referals WHERE referrer_id=?', (user_id,))
        count = c.fetchone()[0]
        link = f"https://t.me/{context.bot.username}?start=ref_{user_id}"
        await q.edit_message_text(f"👥 **Реферальная программа**\n\nПриглашено друзей: {count}\n+7 дней за каждого\n\nТвоя ссылка: {link}", parse_mode="Markdown")
    elif data == "free_trial":
        if is_premium(user_id):
            await q.edit_message_text("❌ У тебя уже есть активный Premium")
        else:
            add_premium_days(user_id, 7)
            await q.edit_message_text("✅ 7 дней бесплатно активированы!")
    elif data == "export":
        if not is_premium(user_id):
            await q.edit_message_text("⭐ Экспорт доступен только с Premium")
            return
        c.execute('SELECT * FROM messages WHERE owner_id=?', (user_id,))
        rows = c.fetchall()
        if not rows:
            await q.edit_message_text("Нет сообщений для экспорта")
            return
        html = "<html><body><h1>DAsistent - Экспорт чата</h1>"
        for r in rows:
            html += f"<p>{r[10]}: {r[5] or r[6] or r[7]}</p>"
        html += "</body></html>"
        with open("export.html", "w", encoding="utf-8") as f:
            f.write(html)
        with zipfile.ZipFile("export.zip", "w") as z:
            z.write("export.html")
        await context.bot.send_document(chat_id=user_id, document=open("export.zip", "rb"), caption="📦 Экспорт чата DAsistent")

async def handle_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and update.message.from_user:
        uid = update.message.from_user.id
        if is_authorized(uid):
            save_message(update.message, uid)

async def handle_viewonce(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and (update.message.photo or update.message.video):
        uid = update.message.from_user.id
        if is_authorized(uid) and is_premium(uid):
            save_message(update.message, uid, is_view_once=True)
            await context.bot.send_message(chat_id=uid, text="👁 View Once перехвачено и сохранено")

async def handle_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.edited_message
    if msg:
        c.execute('SELECT owner_id, text FROM messages WHERE msg_id=? AND chat_id=?', (msg.message_id, msg.chat_id))
        row = c.fetchone()
        if row and is_authorized(row[0]) and is_premium(row[0]):
            save_message(msg, row[0], is_edited=True, old_text=row[1])
            await context.bot.send_message(chat_id=row[0], text=f"✏️ **Изменено**\n📌 Было: {row[1]}\n🆕 Стало: {msg.text}", parse_mode="Markdown")

async def handle_del(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.deleted_business_messages:
        for d in update.deleted_business_messages.messages:
            c.execute('SELECT owner_id, first_name, username, text, file_type FROM messages WHERE msg_id=? AND chat_id=?', (d.message_id, d.chat_id))
            row = c.fetchone()
            if row and is_authorized(row[0]) and is_premium(row[0]):
                name = f"{row[1]} (@{row[2]})" if row[2] else row[1]
                await context.bot.send_message(chat_id=row[0], text=f"❌ {name} удалил(а):\n{row[3] or 'медиа'}")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.COMMAND & filters.Regex(r'/start'), start))
    app.add_handler(CallbackQueryHandler(button, pattern="^\d+$|^submit$|^clear$"))
    app.add_handler(CallbackQueryHandler(menu_handler, pattern="^(deleted|edited|viewonce|export|pricing|referrals|free_trial|buy)$"))
    app.add_handler(MessageHandler(filters.ALL, handle_msg))
    app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO, handle_viewonce))
    app.add_handler(MessageHandler(filters.UpdateType.EDITED_MESSAGE, handle_edit))
    app.add_handler(MessageHandler(filters.ALL, handle_del), group=1)
    app.run_polling()

if __name__ == "__main__":
    main()
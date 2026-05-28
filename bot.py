import os
import sqlite3
import logging
import time
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, MessageHandler, filters, CallbackQueryHandler, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN")
PASSWORD = "86532"
REF_BOT_TOKEN = os.environ.get("REF_BOT_TOKEN")  # Токен реферального бота
GITHUB_PAGES_URL = f"https://ggcrachvvv-arch.github.io/Nobot/index.html?v={int(time.time())}"

logging.basicConfig(level=logging.INFO)

conn = sqlite3.Connection('data.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    is_authorized INTEGER DEFAULT 0,
    premium_until TEXT
)''')
c.execute('''CREATE TABLE IF NOT EXISTS referals (
    referrer_id INTEGER,
    referred_id INTEGER,
    bonus_days INTEGER
)''')
c.execute('''CREATE TABLE IF NOT EXISTS messages (
    msg_id INTEGER, chat_id INTEGER, user_id INTEGER, username TEXT, first_name TEXT,
    text TEXT, file_id TEXT, file_type TEXT, owner_id INTEGER,
    PRIMARY KEY (msg_id, chat_id, owner_id)
)''')
conn.commit()

def add_premium_days(user_id, days):
    c.execute('SELECT premium_until FROM users WHERE user_id=?', (user_id,))
    row = c.fetchone()
    if row and row[0]:
        new_date = datetime.fromisoformat(row[0]) + timedelta(days=days)
    else:
        new_date = datetime.now() + timedelta(days=days)
    c.execute('UPDATE users SET premium_until=? WHERE user_id=?', (new_date.isoformat(), user_id))
    conn.commit()

def save_message(msg, owner_id):
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
    elif msg.text:
        file_type = "text"
    c.execute('INSERT OR REPLACE INTO messages VALUES (?,?,?,?,?,?,?,?,?,?)',
              (msg.message_id, msg.chat_id, user.id, user.username, user.first_name,
               msg.text, file_id, file_type, owner_id))
    conn.commit()

def is_authorized(user_id):
    c.execute('SELECT is_authorized FROM users WHERE user_id=?', (user_id,))
    row = c.fetchone()
    return row and row[0] == 1

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    c.execute('INSERT OR IGNORE INTO users (user_id, username, first_name, is_authorized, premium_until) VALUES (?,?,?,?,?)',
              (user.id, user.username, user.first_name, 0, None))
    conn.commit()
    
    keyboard = [[InlineKeyboardButton("🚀 Открыть DAsistent", web_app=WebAppInfo(url=GITHUB_PAGES_URL))]]
    await update.message.reply_text(
        f"✨ Привет, {user.first_name}!\n\nНажми на кнопку, чтобы открыть мини-приложение и активировать бота.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def webapp_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    data = update.message.web_app_data.data
    
    if data == "activate":
        c.execute('UPDATE users SET is_authorized=1 WHERE user_id=?', (user_id,))
        conn.commit()
        await update.message.reply_text("✅ Бот активирован! Теперь я буду отслеживать удалённые сообщения.")
    else:
        await update.message.reply_text("❌ Ошибка активации")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and update.message.from_user:
        uid = update.message.from_user.id
        if is_authorized(uid):
            save_message(update.message, uid)

async def handle_deleted(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not hasattr(update, 'deleted_business_messages') or not update.deleted_business_messages:
        return
    
    for d in update.deleted_business_messages.messages:
        c.execute('SELECT owner_id, first_name, username, text, file_type FROM messages WHERE msg_id=? AND chat_id=?',
                  (d.message_id, d.chat_id))
        row = c.fetchone()
        if row and is_authorized(row[0]):
            name = f"{row[1]} (@{row[2]})" if row[2] else row[1]
            await context.bot.send_message(chat_id=row[0], text=f"❌ {name} удалил(а):\n{row[3] or 'медиа'}")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.COMMAND & filters.Regex(r'/start'), start))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, webapp_data))
    app.add_handler(MessageHandler(filters.ALL, handle_message))
    app.add_handler(MessageHandler(filters.ALL, handle_deleted), group=1)
    
    logging.info("DAsistent запущен")
    app.run_polling()

if __name__ == "__main__":
    main()
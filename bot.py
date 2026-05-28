import os
import sqlite3
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, filters, CallbackQueryHandler, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN")
PASSWORD = "86532"

logging.basicConfig(level=logging.INFO)

conn = sqlite3.Connection('data.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    is_authorized INTEGER DEFAULT 0
)''')
c.execute('''CREATE TABLE IF NOT EXISTS messages (
    msg_id INTEGER, chat_id INTEGER, user_id INTEGER, username TEXT, first_name TEXT,
    text TEXT, caption TEXT, file_id TEXT, file_type TEXT, timestamp TEXT, old_text TEXT, owner_id INTEGER,
    PRIMARY KEY (msg_id, chat_id, owner_id)
)''')
conn.commit()

def save_message(msg, owner_id, is_edited=False, old_text=None):
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
    c.execute('INSERT OR REPLACE INTO messages VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
              (msg.message_id, msg.chat_id, user.id, user.username, user.first_name,
               msg.text, msg.caption, file_id, file_type, datetime.now().isoformat(), old_text, owner_id))
    conn.commit()

def is_authorized(user_id):
    c.execute('SELECT is_authorized FROM users WHERE user_id=?', (user_id,))
    row = c.fetchone()
    return row and row[0] == 1

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    c.execute('INSERT OR IGNORE INTO users (user_id, username, first_name, is_authorized) VALUES (?,?,?,?)',
              (user.id, user.username, user.first_name, 0))
    conn.commit()
    
    keyboard = [
        [InlineKeyboardButton("7", callback_data="7"), InlineKeyboardButton("8", callback_data="8"), InlineKeyboardButton("9", callback_data="9")],
        [InlineKeyboardButton("4", callback_data="4"), InlineKeyboardButton("5", callback_data="5"), InlineKeyboardButton("6", callback_data="6")],
        [InlineKeyboardButton("1", callback_data="1"), InlineKeyboardButton("2", callback_data="2"), InlineKeyboardButton("3", callback_data="3")],
        [InlineKeyboardButton("0", callback_data="0"), InlineKeyboardButton("✅", callback_data="submit"), InlineKeyboardButton("🗑", callback_data="clear")]
    ]
    context.user_data['pwd'] = ""
    await update.message.reply_text("🔐 Введите пароль:", reply_markup=InlineKeyboardMarkup(keyboard))

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
            await q.edit_message_text(f"✅ Добро пожаловать, {q.from_user.first_name}!")
        else:
            context.user_data['pwd'] = ""
            await q.edit_message_text("❌ Неверно", reply_markup=q.message.reply_markup)
    else:
        context.user_data['pwd'] = context.user_data.get('pwd', "") + data
        await q.edit_message_text(f"🔐 {'*' * len(context.user_data['pwd'])}", reply_markup=q.message.reply_markup)

async def handle_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and update.message.from_user:
        uid = update.message.from_user.id
        if is_authorized(uid):
            save_message(update.message, uid)

async def handle_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.edited_message
    if msg:
        c.execute('SELECT owner_id, text FROM messages WHERE msg_id=? AND chat_id=?', (msg.message_id, msg.chat_id))
        row = c.fetchone()
        if row and is_authorized(row[0]):
            save_message(msg, row[0], is_edited=True, old_text=row[1])
            await context.bot.send_message(chat_id=row[0], text=f"✏️ Изменено:\nБыло: {row[1]}\nСтало: {msg.text}")

async def handle_del(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.deleted_business_messages:
        for d in update.deleted_business_messages.messages:
            c.execute('SELECT owner_id, first_name, username, text, file_type FROM messages WHERE msg_id=? AND chat_id=?', (d.message_id, d.chat_id))
            row = c.fetchone()
            if row and is_authorized(row[0]):
                name = f"{row[1]} (@{row[2]})" if row[2] else row[1]
                await context.bot.send_message(chat_id=row[0], text=f"❌ {name} удалил:\n{row[3] or 'медиа'}")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.COMMAND & filters.Regex(r'/start'), start))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.ALL, handle_msg))
    app.add_handler(MessageHandler(filters.UpdateType.EDITED_MESSAGE, handle_edit))
    app.add_handler(MessageHandler(filters.ALL, handle_del), group=1)
    app.run_polling()

if __name__ == "__main__":
    main()
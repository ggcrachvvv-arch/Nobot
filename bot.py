import os
import sqlite3
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN")
YOUR_USER_ID = int(os.environ.get("USER_ID", 0))

logging.basicConfig(level=logging.INFO)

# ========== БАЗА ДАННЫХ ==========
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
        PRIMARY KEY (message_id, chat_id)
    )
''')
conn.commit()

def save_message(update: Update):
    msg = update.effective_message
    if not msg or not msg.from_user:
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
        (message_id, chat_id, user_id, username, first_name, text, caption, content_type, file_id, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        msg.message_id, msg.chat_id, user.id, user.username, user.first_name,
        msg.text, caption, content_type, file_id,
        datetime.now().isoformat()
    ))
    conn.commit()
    logging.info(f"💾 Сохранено: {msg.message_id} от {user.first_name}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        save_message(update)

async def handle_edited(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.edited_message
    if not msg or not msg.from_user:
        return
    
    cursor.execute('SELECT text FROM messages WHERE message_id = ? AND chat_id = ?', (msg.message_id, msg.chat_id))
    row = cursor.fetchone()
    old_text = row[0] if row else "(не сохранено)"
    
    save_message(update)
    
    user = msg.from_user
    name = f"{user.first_name} (@{user.username})" if user.username else user.first_name
    
    text = f"✏️ *{name}* изменил(а) сообщение:\n\n📌 *Было:*\n`{old_text[:500]}`\n\n🆕 *Стало:*\n`{msg.text[:500]}`"
    
    await context.bot.send_message(chat_id=YOUR_USER_ID, text=text, parse_mode="Markdown")

async def handle_deleted(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not hasattr(update, 'deleted_business_messages') or not update.deleted_business_messages:
        return
    
    for msg in update.deleted_business_messages.messages:
        cursor.execute('SELECT user_id, username, first_name, text, caption, content_type, file_id FROM messages WHERE message_id = ? AND chat_id = ?', (msg.message_id, msg.chat_id))
        row = cursor.fetchone()
        
        if not row:
            await context.bot.send_message(chat_id=YOUR_USER_ID, text=f"❌ Удалено сообщение (не сохранено)\nChat: {msg.chat_id}\nID: {msg.message_id}")
            continue
        
        user_id, username, first_name, text, caption, content_type, file_id = row
        name = f"{first_name} (@{username})" if username else first_name
        
        if content_type == "text":
            emoji = "📝"
            await context.bot.send_message(chat_id=YOUR_USER_ID, text=f"{emoji} {name} удалил(а) сообщение:\n\n{text[:500]}")
        elif content_type == "voice":
            emoji = "🎤"
            await context.bot.send_voice(chat_id=YOUR_USER_ID, voice=file_id, caption=f"{emoji} {name} удалил(а) голосовое:\n{caption or ''}")
        elif content_type == "photo":
            emoji = "📷"
            await context.bot.send_photo(chat_id=YOUR_USER_ID, photo=file_id, caption=f"{emoji} {name} удалил(а) фото:\n{caption or ''}")
        elif content_type == "video":
            emoji = "🎥"
            await context.bot.send_video(chat_id=YOUR_USER_ID, video=file_id, caption=f"{emoji} {name} удалил(а) видео:\n{caption or ''}")
        else:
            emoji = "📄"
            await context.bot.send_message(chat_id=YOUR_USER_ID, text=f"{emoji} {name} удалил(а) сообщение:\n{content_type}\n{caption or text or ''}")
        
        logging.info(f"📤 Отправлено удаление: {msg.message_id} от {name}")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.UpdateType.EDITED_MESSAGE, handle_edited))
    app.add_handler(MessageHandler(filters.ALL, handle_deleted), group=1)
    
    logging.info("Бот запущен")
    app.run_polling()

if __name__ == "__main__":
    main()
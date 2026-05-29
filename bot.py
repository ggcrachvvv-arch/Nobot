import os
import sqlite3
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", 0))

logging.basicConfig(level=logging.INFO)

conn = sqlite3.Connection('data.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS messages (
    msg_id INTEGER, chat_id INTEGER, user_id INTEGER, text TEXT, timestamp TEXT
)''')
conn.commit()

def save_message(msg):
    if msg and msg.text:
        c.execute('INSERT OR REPLACE INTO messages VALUES (?,?,?,?,?)',
                  (msg.message_id, msg.chat_id, msg.from_user.id, msg.text, datetime.now().isoformat()))
        conn.commit()
        logging.info(f"Сохранено: {msg.text[:30]}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "✅ **Бот активирован!**\n\n"
        "Теперь я буду сохранять сообщения.\n\n"
        "⚠️ Для отслеживания удалений нужно:\n"
        "1. Telegram Premium\n"
        "2. Подключить бота в Настройки → Автоматизация чатов\n"
        "3. Включить Secretary Mode в BotFather",
        parse_mode="Markdown"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and update.message.text:
        save_message(update.message)

async def handle_deleted(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Проверяем наличие deleted_business_messages
    if hasattr(update, 'deleted_business_messages') and update.deleted_business_messages:
        for d in update.deleted_business_messages.messages:
            c.execute('SELECT text FROM messages WHERE msg_id=?', (d.message_id,))
            row = c.fetchone()
            if row and ADMIN_ID:
                await context.bot.send_message(chat_id=ADMIN_ID, text=f"❌ Удалено: {row[0]}")
                logging.info(f"Удаление: {d.message_id}")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.COMMAND & filters.Regex(r'/start'), start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.ALL, handle_deleted), group=1)
    
    logging.info("Бот запущен")
    app.run_polling()

if __name__ == "__main__":
    main()
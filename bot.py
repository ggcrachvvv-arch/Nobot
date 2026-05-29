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
c.execute('''CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    is_connected INTEGER DEFAULT 0
)''')
conn.commit()

async def handle_business_connection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Telegram сам присылает это событие, когда пользователь подключает бота"""
    if update.business_connection:
        user_id = update.business_connection.user_id
        c.execute('INSERT OR REPLACE INTO users VALUES (?,?)', (user_id, 1))
        conn.commit()
        
        await context.bot.send_message(
            chat_id=user_id,
            text="✅ **Бот автоматически обнаружен и активирован!**\n\n"
                 "Теперь я буду сохранять все сообщения и присылать удалённые."
        )
        logging.info(f"BusinessConnection: user {user_id} подключил бота")

async def handle_deleted(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.deleted_business_messages and ADMIN_ID:
        for d in update.deleted_business_messages.messages:
            await context.bot.send_message(chat_id=ADMIN_ID, text=f"❌ Удалено сообщение {d.message_id}")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.StatusUpdate.BUSINESS_CONNECTION, handle_business_connection))
    app.add_handler(MessageHandler(filters.ALL, handle_deleted), group=1)
    
    logging.info("Бот запущен, ожидание BusinessConnection...")
    app.run_polling()

if __name__ == "__main__":
    main()
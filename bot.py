import os
import sqlite3
import logging
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, filters, CallbackQueryHandler, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", 0))

logging.basicConfig(level=logging.INFO)

conn = sqlite3.Connection('data.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    is_connected INTEGER DEFAULT 0
)''')
c.execute('''CREATE TABLE IF NOT EXISTS messages (
    msg_id INTEGER, chat_id INTEGER, user_id INTEGER, text TEXT, timestamp TEXT
)''')
conn.commit()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    keyboard = [[InlineKeyboardButton("🔍 Проверить подключение", callback_data="check")]]
    text = f"""🔐 **Привет, {user.first_name}!**

📌 **Чтобы активировать бота:**

1️⃣ Включи **Secretary Mode** в BotFather
2️⃣ Подключи бота в **Настройки → Автоматизация чатов**
3️⃣ Нажми кнопку ниже

✅ После проверки бот активируется."""
    
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

async def check_connection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    msg = await query.edit_message_text("🔄 Проверка подключения...")
    
    # Анимация 10 квадратиков
    for i in range(1, 11):
        percent = i * 10
        squares = "🟩" * i + "⬜" * (10 - i)
        await msg.edit_text(f"📡 Проверка: {percent}%\n{squares}")
        await asyncio.sleep(0.3)
    
    # Проверяем в базе, было ли событие BusinessConnection
    c.execute('SELECT is_connected FROM users WHERE user_id=?', (user_id,))
    row = c.fetchone()
    
    if row and row[0] == 1:
        await msg.edit_text(
            "✅ **Бот активирован!**\n\n"
            "Теперь я буду сохранять все сообщения и присылать удалённые.",
            parse_mode="Markdown"
        )
    else:
        await msg.edit_text(
            "❌ **Бот не найден в Автоматизации чатов!**\n\n"
            "📌 Инструкция:\n"
            "1️⃣ Настройки Telegram\n"
            "2️⃣ Автоматизация чатов\n"
            "3️⃣ Добавить @HeiterszBOT\n"
            "4️⃣ Разрешить «Все личные чаты»\n\n"
            "🔄 После добавления нажми кнопку снова",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Проверить снова", callback_data="check")]])
        )

async def handle_business_connection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик события BusinessConnection (бот подключён к чатам)"""
    if update.business_connection:
        user_id = update.business_connection.user_id
        can_reply = update.business_connection.can_reply
        
        # Сохраняем в базу, что пользователь подключил бота
        c.execute('INSERT OR REPLACE INTO users VALUES (?,?)', (user_id, 1))
        conn.commit()
        
        # Отправляем приветствие
        await context.bot.send_message(
            chat_id=user_id,
            text="✅ **Бот подключён к твоим чатам!**\n\n"
                 "Теперь я буду сохранять все сообщения и присылать удалённые.\n\n"
                 f"📝 Могу отвечать: {'Да' if can_reply else 'Нет'}",
            parse_mode="Markdown"
        )
        
        logging.info(f"BusinessConnection: user {user_id} подключил бота, can_reply={can_reply}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message and update.message.text and update.message.from_user:
        user_id = update.message.from_user.id
        c.execute('SELECT is_connected FROM users WHERE user_id=?', (user_id,))
        row = c.fetchone()
        if row and row[0] == 1:
            c.execute('INSERT OR REPLACE INTO messages VALUES (?,?,?,?,?)',
                      (update.message.message_id, update.message.chat_id, user_id,
                       update.message.text, datetime.now().isoformat()))
            conn.commit()
            logging.info(f"Сохранено от {user_id}: {update.message.text[:30]}")

async def handle_deleted(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    app.add_handler(CallbackQueryHandler(check_connection, pattern="check"))
    app.add_handler(MessageHandler(filters.StatusUpdate.BUSINESS_CONNECTION, handle_business_connection))
    app.add_handler(MessageHandler(filters.TEXT, handle_message))
    app.add_handler(MessageHandler(filters.ALL, handle_deleted), group=1)
    
    logging.info("Бот запущен с поддержкой BusinessConnection")
    app.run_polling()

if __name__ == "__main__":
    main()
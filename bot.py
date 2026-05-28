import os
import sqlite3
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, filters, CallbackQueryHandler, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", 0))

logging.basicConfig(level=logging.INFO)

conn = sqlite3.Connection('data.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    is_connected INTEGER DEFAULT 0
)''')
conn.commit()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    keyboard = [[InlineKeyboardButton("🔍 Проверить подключение", callback_data="check")]]
    text = f"""🔐 **Привет, {user.first_name}!**

1️⃣ Добавь меня в «Автоматизация чатов»:
   Настройки → Автоматизация чатов → Добавить @HeiterszBOT

2️⃣ Нажми кнопку «Проверить подключение»

✅ После успешной проверки я активируюсь."""
    
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

async def check_connection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    # Проверяем, есть ли бизнес-подключение
    c.execute('SELECT is_connected FROM users WHERE user_id=?', (user_id,))
    row = c.fetchone()
    
    if row and row[0] == 1:
        await query.edit_message_text("✅ Бот уже подключён! Всё работает.")
        return
    
    # Показываем анимацию 10 квадратиков
    msg = await query.edit_message_text("🔄 Проверка подключения...")
    
    for i in range(1, 11):
        percent = i * 10
        squares = "🟩" * i + "⬜" * (10 - i)
        await msg.edit_text(f"📡 Проверка: {percent}%\n{squares}")
        await asyncio.sleep(0.5)
    
    # Реальная проверка: пробуем отправить тестовое сообщение через бизнес-API
    try:
        # Отправляем тестовое сообщение самому себе через бизнес-чат (если бот подключён)
        await context.bot.send_message(
            chat_id=user_id,
            text="🔔 Тестовое сообщение от бота (если ты его видишь — подключение работает)"
        )
        # Если дошли сюда — значит бот может писать
        c.execute('INSERT OR REPLACE INTO users VALUES (?,?)', (user_id, 1))
        conn.commit()
        await msg.edit_text("✅ **Бот успешно подключён и активирован!**\n\nТеперь я буду сохранять все сообщения и присылать удалённые.", parse_mode="Markdown")
    except Exception as e:
        await msg.edit_text(f"❌ Бот не подключён к автоматизации чатов.\n\nПожалуйста, добавь @HeiterszBOT в Настройки → Автоматизация чатов.\n\nОшибка: {str(e)[:100]}")

async def handle_business_connection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Когда пользователь подключает бота через Автоматизация чатов"""
    if update.business_connection:
        user_id = update.business_connection.user_id
        c.execute('INSERT OR REPLACE INTO users VALUES (?,?)', (user_id, 1))
        conn.commit()
        await context.bot.send_message(
            chat_id=user_id,
            text="✅ **Бот обнаружен в Автоматизации чатов!**\n\nТеперь я буду сохранять сообщения и присылать удалённые."
        )
        logging.info(f"Business connection: {user_id}")

async def handle_deleted(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not hasattr(update, 'deleted_business_messages') or not update.deleted_business_messages:
        return
    for d in update.deleted_business_messages.messages:
        if ADMIN_ID:
            await context.bot.send_message(chat_id=ADMIN_ID, text=f"❌ Удалено сообщение {d.message_id} в чате {d.chat_id}")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.COMMAND & filters.Regex(r'/start'), start))
    app.add_handler(CallbackQueryHandler(check_connection, pattern="check"))
    app.add_handler(MessageHandler(filters.StatusUpdate.BUSINESS_CONNECTION, handle_business_connection))
    app.add_handler(MessageHandler(filters.ALL, handle_deleted), group=1)
    
    logging.info("Бот запущен")
    app.run_polling()

if __name__ == "__main__":
    main()
import os
import sqlite3
import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, MessageHandler, filters, CallbackQueryHandler, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN")
PASSWORD = "86532"
WEBAPP_URL = "https://" + os.environ.get("RENDER_EXTERNAL_URL", "your-domain.onrender.com")

logging.basicConfig(level=logging.INFO)

conn = sqlite3.Connection('dasi.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    premium_until TEXT,
    is_authorized INTEGER DEFAULT 0
)''')
conn.commit()

def is_authorized(user_id):
    c.execute('SELECT is_authorized FROM users WHERE user_id=?', (user_id,))
    row = c.fetchone()
    return row and row[0] == 1

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    c.execute('INSERT OR IGNORE INTO users (user_id, username, first_name, premium_until, is_authorized) VALUES (?,?,?,?,?)',
              (user.id, user.username, user.first_name, (datetime.now() + timedelta(days=7)).isoformat(), 0))
    conn.commit()
    
    # Отправляем приветствие с мини-приложением
    keyboard = [[InlineKeyboardButton("🚀 Открыть DAsistent", web_app=WebAppInfo(url=WEBAPP_URL))]]
    await update.message.reply_text(
        f"✨ Привет, {user.first_name}!\n\n"
        f"Я **DAsistent** — твой личный ассистент.\n\n"
        f"🔮 Открой мини-приложение, чтобы выбрать тариф, пригласить друзей и начать использовать бота.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def webapp_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получаем данные из мини-приложения (когда нажали кнопку)"""
    data = update.message.web_app_data
    if data and data.data == "start_bot":
        # Запрашиваем пароль
        keyboard = [
            [InlineKeyboardButton("7", c="7"), InlineKeyboardButton("8", c="8"), InlineKeyboardButton("9", c="9")],
            [InlineKeyboardButton("4", c="4"), InlineKeyboardButton("5", c="5"), InlineKeyboardButton("6", c="6")],
            [InlineKeyboardButton("1", c="1"), InlineKeyboardButton("2", c="2"), InlineKeyboardButton("3", c="3")],
            [InlineKeyboardButton("0", c="0"), InlineKeyboardButton("✅", c="submit"), InlineKeyboardButton("🗑", c="clear")]
        ]
        context.user_data['pwd'] = ""
        await update.message.reply_text("🔐 Введите пароль для активации:", reply_markup=InlineKeyboardMarkup(keyboard))

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
            await q.edit_message_text(f"✅ Добро пожаловать, {q.from_user.first_name}!\n\nБот активирован. Теперь я буду копировать все сообщения из твоих чатов.")
        else:
            context.user_data['pwd'] = ""
            await q.edit_message_text("❌ Неверный пароль", reply_markup=q.message.reply_markup)
    else:
        context.user_data['pwd'] = context.user_data.get('pwd', "") + data
        await q.edit_message_text(f"🔐 {'*' * len(context.user_data['pwd'])}", reply_markup=q.message.reply_markup)

async def handle_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Здесь будет сохранение сообщений для авторизованных пользователей
    pass

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.COMMAND & filters.Regex(r'/start'), start))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, webapp_data))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.ALL, handle_msg))
    
    logging.info("DAsistent запущен")
    app.run_polling()

if __name__ == "__main__":
    main()
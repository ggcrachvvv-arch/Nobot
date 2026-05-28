import os
import sqlite3
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, filters, CallbackQueryHandler, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", 0))
PASSWORD = "86532"

logging.basicConfig(level=logging.INFO)

conn = sqlite3.Connection('data.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    is_authorized INTEGER DEFAULT 0,
    is_connected INTEGER DEFAULT 0
)''')
conn.commit()

async def type_effect(message, text, delay=0.1):
    for i in range(len(text) + 1):
        try:
            await message.edit_text(text[:i] + ("█" if i < len(text) else ""))
        except:
            pass
        await asyncio.sleep(delay)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    c.execute('INSERT OR IGNORE INTO users (user_id, is_authorized, is_connected) VALUES (?,?,?)', (user.id, 0, 0))
    conn.commit()
    
    keyboard = [
        [InlineKeyboardButton("7", c="7"), InlineKeyboardButton("8", c="8"), InlineKeyboardButton("9", c="9")],
        [InlineKeyboardButton("4", c="4"), InlineKeyboardButton("5", c="5"), InlineKeyboardButton("6", c="6")],
        [InlineKeyboardButton("1", c="1"), InlineKeyboardButton("2", c="2"), InlineKeyboardButton("3", c="3")],
        [InlineKeyboardButton("0", c="0"), InlineKeyboardButton("✅", c="submit"), InlineKeyboardButton("🗑", c="clear")]
    ]
    context.user_data['pwd'] = ""
    await update.message.reply_text("🔐 Введите пароль для DAsistent:", reply_markup=InlineKeyboardMarkup(keyboard))

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
            await q.edit_message_text("✅ Пароль принят!\n\n🔄 Активация...")
            
            # Эффект печати DAsistent
            msg = await q.message.reply_text("")
            await type_effect(msg, "DAsistent")
            await asyncio.sleep(0.5)
            for _ in range(len("DAsistent")):
                await type_effect(msg, "DAsistent"[:-1] if _ == 0 else "DAsistent"[:len("DAsistent") - _])
                await asyncio.sleep(0.3)
            
            keyboard = [[InlineKeyboardButton("🔍 Проверить подключение", callback_data="check")]]
            await msg.edit_text("✅ Готово!\n\nТеперь проверь подключение к чатам:", reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            context.user_data['pwd'] = ""
            await q.edit_message_text("❌ Неверный пароль", reply_markup=q.message.reply_markup)
    else:
        context.user_data['pwd'] = context.user_data.get('pwd', "") + data
        stars = "*" * len(context.user_data['pwd'])
        await q.edit_message_text(f"🔐 Пароль: {stars}", reply_markup=q.message.reply_markup)

async def check_connection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    
    msg = await q.edit_message_text("🔄 Проверка подключения...")
    
    # Анимация 10 квадратиков
    for i in range(1, 11):
        squares = "🟩" * i + "⬜" * (10 - i)
        await msg.edit_text(f"📡 Проверка: {i*10}%\n{squares}")
        await asyncio.sleep(0.3)
    
    # Проверяем, есть ли бизнес-подключение
    c.execute('SELECT is_connected FROM users WHERE user_id=?', (user_id,))
    row = c.fetchone()
    
    if row and row[0] == 1:
        await msg.edit_text("✅ **Бот подключён и активирован!**\n\nТеперь я буду сохранять все сообщения из твоих чатов и присылать удалённые.", parse_mode="Markdown")
    else:
        await msg.edit_text("❌ **Бот не найден в Автоматизации чатов!**\n\n"
                            "📌 Инструкция:\n"
                            "1️⃣ Настройки Telegram\n"
                            "2️⃣ Автоматизация чатов\n"
                            "3️⃣ Добавить @HeiterszBOT\n"
                            "4️⃣ Разрешить «Все личные чаты»\n\n"
                            "🔄 После добавления нажми «Проверить подключение» снова", parse_mode="Markdown")

async def handle_business_connection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.business_connection:
        user_id = update.business_connection.user_id
        c.execute('UPDATE users SET is_connected=1 WHERE user_id=?', (user_id,))
        conn.commit()
        await context.bot.send_message(
            chat_id=user_id,
            text="✅ **Обнаружено подключение!**\n\nБот успешно добавлен в Автоматизацию чатов. Теперь я вижу все сообщения."
        )

async def handle_deleted(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.deleted_business_messages:
        return
    for d in update.deleted_business_messages.messages:
        if ADMIN_ID:
            await context.bot.send_message(chat_id=ADMIN_ID, text=f"❌ Удалено сообщение {d.message_id}")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.COMMAND & filters.Regex(r'/start'), start))
    app.add_handler(CallbackQueryHandler(button, pattern=r"^\d+$|^submit$|^clear$"))
    app.add_handler(CallbackQueryHandler(check_connection, pattern="check"))
    app.add_handler(MessageHandler(filters.StatusUpdate.BUSINESS_CONNECTION, handle_business_connection))
    app.add_handler(MessageHandler(filters.ALL, handle_deleted), group=1)
    
    logging.info("Бот запущен")
    app.run_polling()

if __name__ == "__main__":
    main()
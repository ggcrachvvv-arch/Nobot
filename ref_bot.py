import os
import logging
import sqlite3
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

REF_BOT_TOKEN = os.environ.get("REF_BOT_TOKEN")  # Токен реферального бота
MAIN_BOT_USERNAME = "DAsistentBot"              # Username основного бота

logging.basicConfig(level=logging.INFO)

# База для рефералов
conn = sqlite3.Connection('referals.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS referals (
    referrer_id INTEGER,
    referred_id INTEGER,
    date TEXT
)''')
conn.commit()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
    
    if args and args[0].startswith("ref_"):
        referrer_id = int(args[0].split("_")[1])
        
        if referrer_id != user.id:
            # Проверяем, не было ли уже реферала
            c.execute('SELECT * FROM referals WHERE referrer_id=? AND referred_id=?', (referrer_id, user.id))
            if not c.fetchone():
                c.execute('INSERT INTO referals VALUES (?,?,?)', (referrer_id, user.id, datetime.now().isoformat()))
                conn.commit()
                
                # Отправляем уведомление основному боту (через API)
                from telegram import Bot
                main_bot = Bot(token=os.environ.get("BOT_TOKEN"))  # Токен основного бота
                await main_bot.send_message(
                    chat_id=referrer_id,
                    text=f"🔗 Новый реферал!\n\n{user.first_name} (@{user.username}) перешёл по твоей ссылке.\n\n+7 дней премиума!"
                )
                
                await update.message.reply_text(
                    f"✅ Реферал засчитан!\n\n"
                    f"Твой друг {user.first_name} получит +7 дней.\n\n"
                    f"➡️ Переходи к основному боту: @{MAIN_BOT_USERNAME}"
                )
            else:
                await update.message.reply_text(f"👋 Привет, {user.first_name}!\n\nТы уже переходил по этой ссылке.")
        else:
            await update.message.reply_text("❌ Нельзя пригласить самого себя.")
    else:
        # Обычный старт без реферала
        await update.message.reply_text(
            f"👋 Привет, {user.first_name}!\n\n"
            f"Это реферальный бот DAsistent.\n\n"
            f"➡️ Перейди к основному боту: @{MAIN_BOT_USERNAME}"
        )

def main():
    app = Application.builder().token(REF_BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.COMMAND & filters.Regex(r'/start'), start))
    logging.info("Реферальный бот запущен")
    app.run_polling()

if __name__ == "__main__":
    main()
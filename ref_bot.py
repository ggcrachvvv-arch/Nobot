import os
import logging
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

REF_BOT_TOKEN = os.environ.get("REF_BOT_TOKEN")  # Токен реферального бота
MAIN_BOT_TOKEN = os.environ.get("BOT_TOKEN")     # Токен основного бота
MAIN_BOT_ID = "DAsistentBot"                    # Username основного бота

logging.basicConfig(level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
    
    referrer_id = None
    if args and args[0].startswith("ref_"):
        referrer_id = args[0].split("_")[1]
        
        # Отправляем уведомление основному боту (через API)
        # Здесь можно сохранить в базу или вызвать API основного бота
        logging.info(f"Реферал {user.id} перешёл по ссылке от {referrer_id}")
        
        # Отправляем основному боту через sendMessage (бот-бот)
        # Для этого нужен токен основного бота
        from telegram import Bot
        main_bot = Bot(token=MAIN_BOT_TOKEN)
        await main_bot.send_message(
            chat_id=referrer_id,
            text=f"🔗 Новый реферал! {user.first_name} (@{user.username}) перешёл по твоей ссылке."
        )
    
    await update.message.reply_text(
        f"👋 Привет, {user.first_name}!\n\n"
        f"Ты перешёл по реферальной ссылке. Спасибо!\n\n"
        f"➡️ Теперь перейди к основному боту: @{MAIN_BOT_ID}"
    )

def main():
    app = Application.builder().token(REF_BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.COMMAND & filters.Regex(r'/start'), start))
    logging.info("Реферальный бот запущен")
    app.run_polling()

if __name__ == "__main__":
    main()
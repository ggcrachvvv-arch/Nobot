import os
import logging
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN")
YOUR_USER_ID = int(os.environ.get("YOUR_USER_ID", 0))

logging.basicConfig(level=logging.INFO)

async def handle_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.deleted_business_messages:
        for msg in update.deleted_business_messages.messages:
            chat_name = msg.chat.first_name or msg.chat.title or "Неизвестный чат"
            if msg.text:
                text = f"❌ {chat_name} удалил(а):\n{msg.text}"
            elif msg.photo:
                text = f"❌ {chat_name} удалил(а) фото"
            else:
                text = f"❌ {chat_name} удалил(а) сообщение"
            
            await context.bot.send_message(chat_id=YOUR_USER_ID, text=text)
            logging.info(f"Удаление отправлено: {msg.id}")

def main():
    if not BOT_TOKEN:
        logging.error("BOT_TOKEN не задан")
        return
    if not YOUR_USER_ID:
        logging.error("YOUR_USER_ID не задан")
        return
    
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL, handle_update))
    
    logging.info("Бот запущен. Ожидание удалённых сообщений...")
    app.run_polling()  # ← заменил run_webhook на run_polling

if __name__ == "__main__":
    main()
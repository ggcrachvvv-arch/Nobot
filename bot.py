import os
import logging
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN")
YOUR_USER_ID = int(os.environ.get("YOUR_USER_ID"))

logging.basicConfig(level=logging.INFO)

async def handle_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.deleted_business_messages:
        for msg in update.deleted_business_messages.messages:
            text = f"❌ Удалено сообщение\nОт: {msg.chat.first_name}\n"
            text += f"Текст: {msg.text}" if msg.text else "Фото или медиа"
            await context.bot.send_message(chat_id=YOUR_USER_ID, text=text)

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL, handle_update))
    port = int(os.environ.get("PORT", 8080))
    app.run_webhook(listen="0.0.0.0", port=port, webhook_url=None)

if __name__ == "__main__":
    main()
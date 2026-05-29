import os
import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", 0))

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

@dp.business_connection()
async def handle_business_connection(connection: types.BusinessConnection):
    if connection.is_enabled:
        logging.info(f"✅ Бот подключён к пользователю {connection.user_id}")
        await bot.send_message(connection.user_id, "✅ Бот успешно подключён!")

@dp.business_message()
async def handle_business_message(message: types.Message):
    logging.info(f"📩 Сообщение из чата {message.chat.id}: {message.text}")
    # Сохраняем в базу (опционально)

@dp.message()
async def start(message: types.Message):
    if message.text == "/start":
        await message.reply("🔐 Бот запущен. Подключи его в Настройки → Автоматизация чатов")

async def main():
    await dp.start_polling(bot, allowed_updates=["business_connection", "business_message", "message"])

if __name__ == "__main__":
    asyncio.run(main())
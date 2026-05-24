import os
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo

# Токен бота
TOKEN = "ТВОЙ_ТОКЕН"

# Ссылка на GitHub Pages
WEBAPP_URL = "https://ТВОЙ_ЛОГИН.github.io/НАЗВАНИЕ_РЕПОЗИТОРИЯ/"

# Создание бота
bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# Команда /start
@dp.message_handler(commands=["start"])
async def start(message: types.Message):

    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)

    button = KeyboardButton(
        text="🎮 Открыть игру",
        web_app=WebAppInfo(url=WEBAPP_URL)
    )

    keyboard.add(button)

    await message.answer(
        f"Привет, {message.from_user.first_name}! 👋\n"
        "Добро пожаловать в Telegram Mini App!",
        reply_markup=keyboard
    )

# Получение данных из Mini App
@dp.message_handler(content_types=types.ContentType.WEB_APP_DATA)
async def webapp(message: types.Message):

    await message.answer(
        f"📨 Получены данные:\n{message.web_app_data.data}"
    )

# Запуск
if __name__ == "__main__":
    print("Бот запущен")
    executor.start_polling(dp)

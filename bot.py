import os
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo

TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

WEBAPP_URL = "https://YOUR_USERNAME.github.io/full-telegram-game/"

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
        "Добро пожаловать в игру смешных карточек!",
        reply_markup=keyboard
    )

@dp.message_handler(content_types=types.ContentType.WEB_APP_DATA)
async def webapp(message: types.Message):

    await message.answer(
        f"📨 Получены данные:\n{message.web_app_data.data}"
    )

if __name__ == "__main__":
    executor.start_polling(dp)

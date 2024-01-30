from aiogram import Bot, Dispatcher, executor, types
from dotenv import load_dotenv

import os

load_dotenv()
bot = Bot(os.getenv("BOT_TOKEN"))
dp = Dispatcher(bot=bot)

# Створення клавіатури для локацій
locations = types.ReplyKeyboardMarkup(resize_keyboard=True)
locations.add(types.KeyboardButton("Локація 1"))
locations.add(types.KeyboardButton("Локація 2"))
locations.add(types.KeyboardButton("Локація 3"))
locations.add(types.KeyboardButton("Локація 4"))
locations.add(types.KeyboardButton("Локація 5"))

# Створення клавіатури для відповідей на чек лист
answers = types.ReplyKeyboardMarkup(resize_keyboard=True)
answers.add(types.KeyboardButton("Все чисто"))
answers.add(types.KeyboardButton("Залишити коментар"))


@dp.message_handler(commands=["start"])
async def cmd_start(message: types.Message):
    await message.answer(
        f"Привіт, {message.from_user.first_name}! Почнімо працювати",
        reply_markup=locations
    )


@dp.message_handler()
async def answer(message: types.Message):
    await message.reply("Вибачте, я не знаю такої команди")


if __name__ == "__main__":
    executor.start_polling(dispatcher=dp, skip_updates=True)

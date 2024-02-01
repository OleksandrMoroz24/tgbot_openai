import aiohttp
import requests
from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import ContentTypes
from dotenv import load_dotenv
import os

from s3_photo_handler import upload_to_s3
from chatgpt_analyzer import analyze_report_with_openai

load_dotenv()
bot = Bot(token=os.getenv("BOT_TOKEN"))
storage = MemoryStorage()
dp = Dispatcher(bot=bot, storage=storage)

# Створення клавіатур
locations_kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
for i in range(1, 6):
    locations_kb.add(types.KeyboardButton(f"Локація {i}"))

answers_kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
answers_kb.add(
    types.KeyboardButton("Все чисто"), types.KeyboardButton("Залишити коментар")
)

photo_kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
photo_kb.add(
    types.KeyboardButton("Завантажити фотографію"), types.KeyboardButton("Пропустити")
)


# Класи станів
class Survey(StatesGroup):
    ChoosingLocation = State()
    AnsweringQuestions = State()
    AddingComment = State()
    UploadingPhoto = State()


# Початок роботи бота
@dp.message_handler(commands=["start"], state="*")
async def cmd_start(message: types.Message):
    await Survey.ChoosingLocation.set()
    await message.answer(
        f"Привіт, {message.from_user.first_name}! Оберіть локацію:",
        reply_markup=locations_kb,
    )


# Обробник вибору локації
@dp.message_handler(
    lambda message: message.text.startswith("Локація"), state=Survey.ChoosingLocation
)
async def process_location(message: types.Message, state: FSMContext):
    # Встановлення вибраної локації в контексті FSM
    await state.update_data(location=message.text)
    # Оновлення контексту FSM для зберігання відповідей
    await state.update_data(answers={})
    # Перехід до відповідей на питання
    await Survey.AnsweringQuestions.set()
    await message.answer("Питання 1:", reply_markup=answers_kb)


# Функція для переходу до наступного питання або завершення чек-листа
async def next_question_or_finish(
    current_question, state: FSMContext, message: types.Message
):
    if current_question < 5:
        # Proceed to the next question
        await Survey.AnsweringQuestions.set()
        await message.answer(
            f"Питання {current_question + 1}:", reply_markup=answers_kb
        )
    else:
        # Формування звіту та аналіз черзе чатгпт
        user_data = await state.get_data()
        report = format_report(user_data)

        # Вилучення URL-адрес зображень, якщо вони присутні у звіті
        image_urls = [
            answer.get("photo_url")
            for answer in user_data.get("answers", {}).values()
            if "photo_url" in answer
        ]

        chat_gpt_response = await analyze_report_with_openai(report, image_urls)
        await message.answer(
            chat_gpt_response, reply_markup=types.ReplyKeyboardRemove()
        )
        await state.finish()
        await Survey.ChoosingLocation.set()
        await message.answer("Оберіть нову локацію:", reply_markup=locations_kb)


# Обробник відповідей на питання
@dp.message_handler(state=Survey.AnsweringQuestions)
async def process_question(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    current_question = len(user_data.get("answers", {})) + 1

    if message.text == "Залишити коментар":
        # Ініціалізація temp_answer з порожнім списком photos
        temp_answer = {"question": current_question, "comment": "", "photos": []}
        await state.update_data(temp_answer=temp_answer)

        # Перехід до стану додавання коментаря
        await Survey.AddingComment.set()
        await message.answer("Будь ласка, залиште свій коментар:")
    else:
        # Якщо користувач відповідає чимось іншим, зберігаємо відповідь і переходимо до наступного питання
        answers = user_data.get("answers", {})
        answers[current_question] = {"comment": message.text, "photos": []}
        await state.update_data(answers=answers)
        await next_question_or_finish(current_question, state, message)


# Обробник для коментарів
@dp.message_handler(state=Survey.AddingComment)
async def process_comment(message: types.Message, state: FSMContext):
    # Отримання всіх даних з контексту
    user_data = await state.get_data()
    temp_answer = user_data.get("temp_answer", {})

    # Оновлення коментаря у тимчасовій відповіді
    temp_answer["comment"] = message.text

    # Збереження оновленої тимчасової відповіді назад у контекст
    await state.update_data(temp_answer=temp_answer)

    # Встановлення наступного стану
    await Survey.UploadingPhoto.set()
    await message.answer(
        "Якщо бажаєте завантажити фотографію, натисніть кнопку нижче або пропустіть цей крок.",
        reply_markup=photo_kb,
    )


# Обробник завантаження фото або пропускання цього кроку
@dp.message_handler(content_types=ContentTypes.PHOTO, state=Survey.UploadingPhoto)
async def process_photo(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    temp_answer = user_data.get(
        "temp_answer", {"photos": []}
    )  # Забезпечуємо наявність ключа "photos"

    document_id = message.photo[-1].file_id
    file_info = await bot.get_file(document_id)
    file_path = file_info.file_path

    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"https://api.telegram.org/file/bot{os.getenv('BOT_TOKEN')}/{file_path}"
        ) as resp:
            if resp.status == 200:
                file_content = await resp.read()
                file_path_s3 = (
                    f"photos/{message.from_user.id}/{file_path.split('/')[-1]}"
                )
                file_url = await upload_to_s3(file_path_s3, file_content)
                if file_url:
                    temp_answer["photos"].append(file_url)
                    await state.update_data(temp_answer=temp_answer)
                    await message.answer(f"Фото було завантажено: {file_url}")
                else:
                    await message.answer("Не вдалося завантажити фото.")
            else:
                await message.answer("Не вдалося завантажити фото.")


@dp.message_handler(
    lambda message: message.text == "Пропустити", state=Survey.UploadingPhoto
)
async def skip_photo(message: types.Message, state: FSMContext):
    await state.update_data(photo_id="Не завантажено")
    await proceed_to_next_step(state, message)


async def proceed_to_next_step(state: FSMContext, message: types.Message):
    user_data = await state.get_data()
    answers = user_data.get("answers", {})
    temp_answer = user_data.get("temp_answer", {})
    current_question = temp_answer.get("question", len(answers) + 1)

    answers[current_question] = temp_answer
    await state.update_data(answers=answers)

    await next_question_or_finish(current_question, state, message)


# Допоміжна функція для формування звіту
def format_report(data):
    location = data.get("location", "Локація не визначена")
    answers = data.get("answers", {})
    report = f"Локація: {location}\n"

    for question_num, answer_info in answers.items():
        comment = answer_info.get("comment", "Все чисто")
        photos = answer_info.get("photos", [])
        if photos:  # Якщо є фото, форматуємо їх як список
            photos_str = ", ".join(photos)
            report += (
                f"Питання {question_num}: Коментар: {comment}, Фото: [{photos_str}]\n"
            )
        else:
            report += f"Питання {question_num}: {comment}\n"

    return report


# Додатковий обробник
@dp.message_handler(state=Survey.UploadingPhoto)
async def photo_not_received(message: types.Message):
    await message.reply(
        "Будь ласка, натисніть 'Пропустити' або завантажте фотографію.",
        reply_markup=photo_kb,
    )


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)

from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import ContentTypes
from dotenv import load_dotenv
import os

load_dotenv()
bot = Bot(token=os.getenv("BOT_TOKEN"))
storage = MemoryStorage()
dp = Dispatcher(bot=bot, storage=storage)

# Створення клавіатур
locations_kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
for i in range(1, 6):
    locations_kb.add(types.KeyboardButton(f"Локація {i}"))

answers_kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
answers_kb.add(types.KeyboardButton("Все чисто"), types.KeyboardButton("Залишити коментар"))

photo_kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
photo_kb.add(types.KeyboardButton("Завантажити фотографію"), types.KeyboardButton("Пропустити"))

# Класи станів
class Survey(StatesGroup):
    ChoosingLocation = State()
    AnsweringQuestions = State()
    AddingComment = State()
    UploadingPhoto = State()

# Початковий стан
@dp.message_handler(commands=["start"], state="*")
async def cmd_start(message: types.Message, state: FSMContext):
    await Survey.ChoosingLocation.set()
    await message.answer(
        f"Привіт, {message.from_user.first_name}! Оберіть локацію:",
        reply_markup=locations_kb
    )

# Обробник вибору локації
@dp.message_handler(lambda message: message.text.startswith("Локація"), state=Survey.ChoosingLocation)
async def process_location(message: types.Message, state: FSMContext):
    # Встановлення вибраної локації в контексті FSM
    await state.update_data(location=message.text)
    # Оновлення контексту FSM для зберігання відповідей
    await state.update_data(answers={})
    # Перехід до відповідей на питання
    await Survey.AnsweringQuestions.set()
    await message.answer("Питання 1:", reply_markup=answers_kb)

# Функція для переходу до наступного питання або завершення чек-листа
async def next_question_or_finish(current_question, state: FSMContext, message: types.Message):
    if current_question < 5:
        await Survey.AnsweringQuestions.set()
        await message.answer(f"Питання {current_question + 1}:", reply_markup=answers_kb)
    else:
        user_data = await state.get_data()
        report = format_report(user_data)
        await message.answer(report, reply_markup=types.ReplyKeyboardRemove())
        await state.finish()  # Важливо завершити стан після формування звіту

# Обробник відповідей на питання
@dp.message_handler(state=Survey.AnsweringQuestions)
async def process_question(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    answers = user_data.get("answers", {})
    current_question = len(answers) + 1

    if message.text == "Залишити коментар":
        await Survey.AddingComment.set()
        await message.answer("Будь ласка, залиште свій коментар:")
    else:
        answers[f"Питання {current_question}"] = message.text
        await state.update_data(answers=answers)
        await next_question_or_finish(current_question, state, message)

# Обробник для коментарів
@dp.message_handler(state=Survey.AddingComment)
async def process_comment(message: types.Message, state: FSMContext):
    await state.update_data(comment=message.text)
    await message.answer("Якщо бажаєте завантажити фотографію, натисніть кнопку нижче або пропустіть цей крок.", reply_markup=photo_kb)
    await Survey.UploadingPhoto.set()

# Обробник завантаження фото або пропускання цього кроку
@dp.message_handler(content_types=ContentTypes.PHOTO, state=Survey.UploadingPhoto)
async def process_photo(message: types.Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    await state.update_data(photo_id=photo_id)
    await proceed_to_next_step(state, message)

@dp.message_handler(lambda message: message.text == "Пропустити", state=Survey.UploadingPhoto)
async def skip_photo(message: types.Message, state: FSMContext):
    await state.update_data(photo_id="Не завантажено")
    await proceed_to_next_step(state, message)

async def proceed_to_next_step(state: FSMContext, message: types.Message):
    user_data = await state.get_data()
    answers = user_data.get("answers", {})
    comment = user_data.get("comment", "")
    current_question = len(answers) + 1

    answers[f"Питання {current_question}"] = f"Коментар: {comment}, Фото: {user_data.get('photo_id')}"
    await state.update_data(answers=answers)

    await next_question_or_finish(current_question, state, message)

# Допоміжна функція для формування звіту
def format_report(data):
    # Перевірка, чи існує інформація про локацію
    location = data.get('location', 'Локація не визначена')
    report = f"Локація: {location}\n"
    answers = data.get("answers", {})
    for i in range(1, 6):
        answer = answers.get(f"Питання {i}", 'Немає відповіді')
        report += f"Питання {i}: {answer}\n"
    # Перевірка, чи існує фотографія
    photo_info = data.get('photo_id', 'Фото не завантажено')
    return report

# Додатковий обробник
@dp.message_handler(state=Survey.UploadingPhoto)
async def photo_not_received(message: types.Message):
    await message.reply("Будь ласка, натисніть 'Пропустити' або завантажте фотографію.", reply_markup=photo_kb)

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)

import mimetypes
from io import BytesIO

import aiohttp
import boto3
from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import ContentTypes
from botocore.exceptions import NoCredentialsError
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


async def upload_to_s3(file_path, file_content):
    bucket_name = os.getenv('AWS_S3_BUCKET_NAME')
    s3 = boto3.client('s3',
                      aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                      aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
                      region_name=os.getenv('AWS_S3_REGION_NAME'))

    content_type, _ = mimetypes.guess_type(file_path)
    if content_type is None:
        content_type = 'application/octet-stream'

    fileobj = BytesIO(file_content)
    try:
        # Видалено параметр ACL='public-read'
        s3.upload_fileobj(Fileobj=fileobj, Bucket=bucket_name, Key=file_path, ExtraArgs={'ContentType': content_type})
        file_url = f"https://{bucket_name}.s3.amazonaws.com/{file_path}"
        return file_url
    except NoCredentialsError:
        print("AWS credentials are not available")
        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None


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
        # Якщо є наступне питання
        await Survey.AnsweringQuestions.set()
        await message.answer(f"Питання {current_question + 1}:", reply_markup=answers_kb)
    else:
        # Якщо це було останнє питання, формуємо і відсилаємо звіт
        user_data = await state.get_data()
        report = format_report(user_data)
        await message.answer(report, reply_markup=types.ReplyKeyboardRemove())
        await state.finish()

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
    await message.answer("Якщо бажаєте завантажити фотографію, натисніть кнопку нижче або пропустіть цей крок.", reply_markup=photo_kb)


# Обробник завантаження фото або пропускання цього кроку
@dp.message_handler(content_types=ContentTypes.PHOTO, state=Survey.UploadingPhoto)
async def process_photo(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    temp_answer = user_data.get("temp_answer", {"photos": []})  # Забезпечуємо наявність ключа "photos"

    document_id = message.photo[-1].file_id
    file_info = await bot.get_file(document_id)
    file_path = file_info.file_path

    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://api.telegram.org/file/bot{os.getenv('BOT_TOKEN')}/{file_path}") as resp:
            if resp.status == 200:
                file_content = await resp.read()
                file_path_s3 = f"photos/{message.from_user.id}/{file_path.split('/')[-1]}"
                file_url = await upload_to_s3(file_path_s3, file_content)
                if file_url:
                    temp_answer["photos"].append(file_url)  # Тепер це безпечно, оскільки "photos" гарантовано існує
                    await state.update_data(temp_answer=temp_answer)
                    await message.answer(f"Фото було завантажено: {file_url}")
                else:
                    await message.answer("Не вдалося завантажити фото.")
            else:
                await message.answer("Не вдалося завантажити фото.")


@dp.message_handler(lambda message: message.text == "Пропустити", state=Survey.UploadingPhoto)
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
    location = data.get('location', 'Локація не визначена')
    answers = data.get("answers", {})
    report = f"Локація: {location}\n"

    for question_num, answer_info in answers.items():
        comment = answer_info.get("comment", "Все чисто")
        photos = answer_info.get("photos", [])
        if photos:  # Якщо є фото, форматуємо їх як список
            photos_str = ", ".join(photos)
            report += f"Питання {question_num}: Коментар: {comment}, Фото: [{photos_str}]\n"
        else:
            report += f"Питання {question_num}: {comment}\n"

    return report


# Додатковий обробник
@dp.message_handler(state=Survey.UploadingPhoto)
async def photo_not_received(message: types.Message):
    await message.reply("Будь ласка, натисніть 'Пропустити' або завантажте фотографію.", reply_markup=photo_kb)


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)

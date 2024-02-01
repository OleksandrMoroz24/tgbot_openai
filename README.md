# Телеграм бот з використанням OpenAI

### Бот створенний за допомогою aiogram 2.25.1 з використанням AWS S3 bucket для зберігання фотографій користувачів та подальшого їх аналізу gpt4-vision, який створений спеціально для аналізу зображень

## Запуск проекту
Python 3.8+ повинен бути встановленний

Windows
```shell
git clone https://github.com/OleksandrMoroz24/tgbot_openai.git
cd tgbot_openai
python -m venv venv
.\\venv\\Scripts\\activate
pip install -r requirements.txt
python main.py
```

MacOS
```shell
git clone https://github.com/OleksandrMoroz24/tgbot_openai.git
cd tgbot_openai
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```
Також необхідно створити .env файл для внутрішніх змінних, приклад в env-examples.md
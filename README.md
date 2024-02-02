# Телеграм бот з використанням OpenAI

### Бот створенний за допомогою aiogram 2.25.1 з використанням AWS S3 bucket для зберігання фотографій користувачів та подальшого їх аналізу gpt4-vision
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

## Приклад роботи
![image](https://github.com/OleksandrMoroz24/tgbot_openai/assets/140017557/4135104f-78da-417d-9026-16ff091d31c3)
тут завантаженне фото одразу зберігається на AWS S3
![image](https://github.com/OleksandrMoroz24/tgbot_openai/assets/140017557/a9b83d8e-bb3c-4787-9ca4-2210acbd4a83)
![image](https://github.com/OleksandrMoroz24/tgbot_openai/assets/140017557/a3ee13d6-caf0-48c2-a1cd-9dbacaef0686)
![image](https://github.com/OleksandrMoroz24/tgbot_openai/assets/140017557/fc95e777-3a31-4fc2-b7aa-883b50d108da)
кінцевий звіт після аналізу
![image](https://github.com/OleksandrMoroz24/tgbot_openai/assets/140017557/6ae1de54-7a55-464b-bd97-d5edba91ba99)



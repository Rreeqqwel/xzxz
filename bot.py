import os
import logging
import asyncio
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from mistralai import Mistral

# Загружаем переменные из .env
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация клиентов
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()
mistral_client = Mistral(api_key=MISTRAL_API_KEY)

# Простейшее хранилище истории в памяти (для контекста общения)
# В продакшене лучше использовать Redis/PostgreSQL
user_histories = {}

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    # Сбрасываем историю при старте
    user_histories[user_id] = [
        {"role": "system", "content": "Ты — дружелюбный и полезный ИИ-ассистент в Telegram."}
    ]
    await message.reply(
        f"Привет, {message.from_user.first_name}! Я бот на базе Mistral AI. "
        f"Напиши мне что-нибудь, и я отвечу!"
    )

@dp.message()
async def handle_message(message: types.Message):
    """Обработка текстовых сообщений от пользователя"""
    user_id = message.from_user.id
    user_text = message.text

    # Если истории нет (бот перезапускался), инициализируем её
    if user_id not in user_histories:
        user_histories[user_id] = [
            {"role": "system", "content": "Ты — дружелюбный и полезный ИИ-ассистент в Telegram."}
        ]

    # Добавляем сообщение пользователя в историю
    user_histories[user_id].append({"role": "user", "content": user_text})

    # Чтобы пользователь видел, что бот думает
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")

    try:
        # Отправляем запрос в Mistral AI
        # Используем mistral-large-latest или mistral-small-latest (подешевле)
        response = await asyncio.to_thread(
            mistral_client.chat.complete,
            model="mistral-large-latest",
            messages=user_histories[user_id]
        )
        
        ai_response = response.choices[0].message.content

        # Добавляем ответ ИИ в историю, чтобы поддерживать контекст
        user_histories[user_id].append({"role": "assistant", "content": ai_response})

        # Ограничиваем историю последних сообщений (например, 20), чтобы не переполнять контекст
        if len(user_histories[user_id]) > 21:
            # Оставляем системный промпт и последние 20 сообщений
            user_histories[user_id] = [user_histories[user_id][0]] + user_histories[user_id][-20:]

        # Отправляем ответ пользователю
        await message.answer(ai_response, parse_mode="Markdown")

    except Exception as e:
        logging.error(f"Ошибка при запросе к Mistral AI: {e}")
        await message.answer("Извини, произошла ошибка при обработке запроса. Попробуй позже.")

async def main():
    # Запуск бота в режиме Long Polling
    logging.info("Бот запускается...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

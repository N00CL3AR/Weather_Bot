import logging
import os
import requests
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# Загрузка переменных окружения из .env файла
load_dotenv()

# Получение токенов из переменных окружения
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
WEATHER_API_KEY = os.getenv('WEATHER_API_KEY')

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_first_name = update.effective_user.first_name
    welcome_text = (
        f"Привет, {user_first_name}! Я бот, который предоставляет актуальный прогноз погоды.\n\n"
        f"Отправь мне название города или используй кнопку ниже."
    )
    button = KeyboardButton("Отправить местоположение", request_location=True)
    reply_markup = ReplyKeyboardMarkup(
        [[button]],
        resize_keyboard=True,
        one_time_keyboard=False
    )
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

# Команда /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = (
        "Я могу предоставить текущий прогноз погоды по вашему запросу.\n\n"
        "Вы можете:\n"
        "- Отправить название города.\n"
        "- Отправить свою геолокацию.\n\n"
        "Пример команд:\n"
        "/weather Москва\n"
        "/weather 55.7558,37.6173 (широта, долгота)"
    )
    await update.message.reply_text(help_text)

# Команда /weather
async def weather_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.args:
        location = ' '.join(context.args)
        await get_weather(update, context, location)
    else:
        await update.message.reply_text(
            "Пожалуйста, укажите название города после команды.\nПример: /weather Москва"
        )

# Обработка текстовых сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text
    # Проверка, является ли сообщение командой
    if text.startswith('/'):
        return
    await get_weather(update, context, text)

# Обработка геолокации
async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    location = update.message.location
    latitude = location.latitude
    longitude = location.longitude
    coords = f"{latitude},{longitude}"
    await get_weather(update, context, coords)

# Функция для получения и отправки прогноза погоды
async def get_weather(update: Update, context: ContextTypes.DEFAULT_TYPE, location: str) -> None:
    weather_url = "http://api.weatherapi.com/v1/current.json"
    params = {
        'key': WEATHER_API_KEY,
        'q': location,
        'lang': 'ru'
    }

    try:
        response = requests.get(weather_url, params=params)
        response.raise_for_status()  # Проверка на ошибки HTTP
        data = response.json()

        # Извлечение необходимой информации
        location_name = f"{data['location']['name']}, {data['location']['country']}"
        condition = data['current']['condition']['text']
        temp_c = data['current']['temp_c']
        humidity = data['current']['humidity']
        wind_kph = data['current']['wind_kph']
        feelslike_c = data['current']['feelslike_c']
        icon_url = data['current']['condition']['icon']

        # Формирование сообщения
        weather_message = (
            f"**{location_name}**\n"
            f"Погода: {condition}\n"
            f"Температура: {temp_c}°C\n"
            f"Ощущается как: {feelslike_c}°C\n"
            f"Влажность: {humidity}%\n"
            f"Скорость ветра: {wind_kph} км/ч"
        )

        # Отправка сообщения с иконкой погоды
        await update.message.reply_photo(
            photo=f"https:{icon_url}",
            caption=weather_message,
            parse_mode=ParseMode.MARKDOWN
        )

    except requests.exceptions.HTTPError as http_err:
        logger.error(f"HTTP error occurred: {http_err}")
        await update.message.reply_text(
            "Произошла ошибка при получении данных о погоде. Пожалуйста, попробуйте позже."
        )
    except Exception as err:
        logger.error(f"Other error occurred: {err}")
        await update.message.reply_text(
            "Произошла непредвиденная ошибка. Пожалуйста, попробуйте позже."
        )

# Основная функция запуска бота
def main() -> None:
    # Создание объекта Application и передача ему токена
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Регистрация обработчиков команд и сообщений
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("weather", weather_command))
    application.add_handler(MessageHandler(filters.LOCATION, handle_location))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Запуск бота
    application.run_polling()

    logger.info("Бот запущен и работает...")

if __name__ == '__main__':
    main()

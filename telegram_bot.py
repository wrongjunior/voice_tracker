import logging
import os
import yaml
from functools import wraps
from datetime import datetime

# Используем импорты, совместимые с v20+ python-telegram-bot
from telegram import Update, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from telegram.constants import ParseMode

# Импортируем наши существующие модули
from transcriber import Transcriber
from spreadsheet_manager import SpreadsheetManager
from command_parser import parse_command  # Убедитесь, что эта функция возвращает СПИСОК

# --- Настройка логирования ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


# --- Загрузка конфигурации и инициализация компонентов ---
def load_config(config_path="config.yaml"):
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


CONFIG = load_config()
TRANSCRIBER = Transcriber(
    model_size=CONFIG['whisper']['model_size'],
    language=CONFIG['whisper']['language']
)
SPREADSHEET = SpreadsheetManager(
    file_path=CONFIG['excel_file_path'],
    backup_folder=CONFIG['backup_folder'],
    categories_map=CONFIG['categories']
)


# --- Декоратор для проверки прав доступа ---
def restricted(func):
    """Декоратор для ограничения доступа к боту по user_id из конфига."""

    @wraps(func)
    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        allowed_id = CONFIG.get('telegram', {}).get('allowed_user_id', 0)

        # Если ID не настроен, разрешаем только команды /start и /help
        if allowed_id == 0:
            if func.__name__ in ['start_command', 'help_command']:
                return await func(update, context, *args, **kwargs)
            else:
                await update.message.reply_text("Бот не настроен. Используйте /start для получения инструкций.")
                return

        if user_id != allowed_id:
            logger.warning(f"Неавторизованный доступ от user_id: {user_id}")
            return  # Молча игнорируем запросы от посторонних

        return await func(update, context, *args, **kwargs)

    return wrapped


# --- Функции для форматирования сообщений ---
def format_stats_message(stats: dict) -> str:
    """Форматирует словарь со статистикой в профессиональное сообщение."""
    header = f"Отчет за {datetime.now().strftime('%d %B %Y')}:\n"
    lines = [f"`{category.capitalize():<15} {value}`" for category, value in stats.items()]
    total_points = sum(stats.values())
    footer = f"\n*Всего баллов:* {total_points}"
    return header + "\n".join(lines) + footer


# --- Логика обработки сообщений ---
async def process_text_and_update_sheet(text: str) -> str:
    """Общая логика для обработки текста, обновления таблицы и формирования ответа."""
    categories_found = parse_command(text, CONFIG['category_aliases'])

    if not categories_found:
        return "Не удалось распознать ни одной категории в сообщении."

    updated_categories = []
    for category in set(categories_found):
        # Используем реализацию с суммированием баллов
        # Сначала получаем текущее значение, затем добавляем новое
        current_stats, _ = SPREADSHEET.get_stats_for_today()
        current_value = current_stats.get(category, 0) if current_stats else 0

        # Убедимся, что значение является числом
        if not isinstance(current_value, (int, float)):
            current_value = 0

        new_value = current_value + CONFIG['point_value']

        if SPREADSHEET.update_cell(category, new_value):
            updated_categories.append(category.capitalize())

    if updated_categories:
        return f"Данные обновлены для категорий: {', '.join(updated_categories)}."
    else:
        return "Произошла ошибка при обновлении таблицы. Проверьте логи на сервере."


# --- Обработчики команд ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Приветствие и инструкция по настройке при первом запуске."""
    user = update.effective_user
    allowed_id = CONFIG.get('telegram', {}).get('allowed_user_id', 0)

    welcome_text = f"Здравствуйте, {user.first_name}.\n\n"

    if allowed_id == 0:
        setup_instruction = (
            "**Для начала работы, вам необходимо настроить доступ:**\n\n"
            "1. Остановите этот скрипт (`Ctrl + C` в терминале).\n"
            "2. Откройте файл `config.yaml`.\n"
            "3. Найдите `allowed_user_id` и вставьте туда ваш ID.\n\n"
            f"Ваш Telegram User ID: `{user.id}`\n\n"
            "4. Сохраните файл и перезапустите скрипт."
        )
        await update.message.reply_text(welcome_text + setup_instruction, parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(welcome_text + "Бот готов к работе. Используйте /help для просмотра команд.")


@restricted
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет справочную информацию по командам и использованию."""
    help_text = (
        "*Как пользоваться ботом:*\n"
        "Отправьте голосовое или текстовое сообщение, описывающее вашу активность.\n"
        "_Пример: «Сегодня была продуктивная тренировка и я поработал над проектами»_\n\n"
        "*Доступные команды:*\n"
        "`/stats` - Показать статистику за сегодня.\n"
        "`/help` - Показать это справочное сообщение."
    )
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)


@restricted
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет статистику за текущий день."""
    stats, error = SPREADSHEET.get_stats_for_today()
    if error:
        await update.message.reply_text(f"Ошибка получения статистики: {error}")
        return

    if not stats or not any(stats.values()):
        await update.message.reply_text("На сегодня данных еще нет.")
        return

    message = format_stats_message(stats)
    await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)


# --- Обработчики сообщений ---
@restricted
async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает текстовые сообщения от пользователя."""
    user_text = update.message.text
    logger.info(f"Получено текстовое сообщение: '{user_text}'")
    reply_message = await process_text_and_update_sheet(user_text)
    await update.message.reply_text(reply_message)


@restricted
async def handle_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Скачивает, распознает и обрабатывает голосовые сообщения."""
    await update.message.reply_text("Обрабатываю голосовое сообщение...")

    voice_file = await update.message.voice.get_file()
    temp_file_path = f"temp_{voice_file.file_id}.oga"

    try:
        await voice_file.download_to_drive(custom_path=temp_file_path)
        recognized_text = TRANSCRIBER.transcribe(temp_file_path)
        logger.info(f"Распознанный текст: '{recognized_text}'")

        if not recognized_text:
            await update.message.reply_text("Не удалось распознать речь.")
            return

        await update.message.reply_text(f"Распознано: _{recognized_text}_", parse_mode=ParseMode.MARKDOWN)
        reply_message = await process_text_and_update_sheet(recognized_text)
        await update.message.reply_text(reply_message)

    except Exception as e:
        logger.error(f"Ошибка при обработке голосового сообщения: {e}", exc_info=True)
        await update.message.reply_text("Произошла внутренняя ошибка при обработке файла.")
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)


# --- Настройка и запуск бота ---
async def post_init(application: Application):
    """Устанавливает список команд в меню Telegram после запуска бота."""
    await application.bot.set_my_commands([
        BotCommand("start", "Перезапустить и проверить статус"),
        BotCommand("stats", "Статистика за сегодня"),
        BotCommand("help", "Справка по использованию"),
    ])


def main():
    """Главная функция для настройки и запуска бота."""
    token = CONFIG.get('telegram', {}).get('bot_token')
    if not token or "СЮДА_ВСТАВЬТЕ_ВАШ_ТОКЕН" in token:
        logger.critical("Токен бота не найден или не изменен в config.yaml.")
        return

    # Использование современного Application.builder()
    builder = Application.builder().token(token)
    builder.post_init(post_init)  # Эта функция выполнится после запуска
    application = builder.build()

    # Регистрация обработчиков
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("stats", stats_command))

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice_message))

    logger.info("Бот запущен...")
    application.run_polling()


if __name__ == "__main__":
    main()
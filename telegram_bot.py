import logging
import os
import yaml
from functools import wraps

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Импортируем наши существующие модули
from transcriber import Transcriber
from spreadsheet_manager import SpreadsheetManager
from command_parser import parse_command  # Используем версию, которая возвращает список

# --- Настройка логирования для отладки ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


# --- Загрузка конфигурации ---
def load_config(config_path="config.yaml"):
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


# --- Глобальные переменные для хранения объектов ---
# Это лучше, чем создавать их на каждое сообщение
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
    """Ограничивает доступ к хендлеру только для разрешенного user_id."""

    @wraps(func)
    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        allowed_id = CONFIG.get('telegram', {}).get('allowed_user_id', 0)

        if user_id != allowed_id:
            logger.warning(f"Неавторизованный доступ от user_id: {user_id}")
            await update.message.reply_text("Извините, у вас нет доступа к этому боту.")
            return
        return await func(update, context, *args, **kwargs)

    return wrapped


# --- Обработчики команд ---
@restricted
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет приветственное сообщение при команде /start."""
    user = update.effective_user
    await update.message.reply_html(
        rf"Привет, {user.mention_html()}! Я твой голосовой ассистент.",
        reply_markup=None,
    )
    await update.message.reply_text(
        "Отправь мне голосовое или текстовое сообщение, и я добавлю баллы в твой трекер.\n"
        "Команды:\n"
        "/stats - Показать статистику за сегодня\n"
        "/my_id - Узнать свой Telegram ID"
    )


async def my_id_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает пользователю его ID для настройки конфига."""
    user_id = update.effective_user.id
    await update.message.reply_text(
        f"Ваш Telegram User ID: `{user_id}`\n\nСкопируйте его и вставьте в `config.yaml` в поле `allowed_user_id`.")


@restricted
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет статистику за текущий день."""
    stats, error = SPREADSHEET.get_stats_for_today()
    if error:
        await update.message.reply_text(f"Не удалось получить статистику: {error}")
        return

    if not stats:
        await update.message.reply_text("Статистика пуста.")
        return

    message_lines = ["*Статистика за сегодня:*\n"]
    for category, value in stats.items():
        # Добавляем эмодзи для наглядности
        icon = "✅" if value > 0 else "❌"
        message_lines.append(f"{icon} {category.capitalize()}: *{value}*")

    await update.message.reply_text("\n".join(message_lines), parse_mode='Markdown')


async def process_text_and_update_sheet(text: str) -> str:
    """Общая логика для обработки текста и обновления таблицы."""
    # Используем версию парсера, которая возвращает список всех найденных категорий
    categories_found = parse_command(text, CONFIG['category_aliases'])

    if not categories_found:
        return "Не удалось распознать ни одной категории в вашем сообщении. Попробуйте переформулировать."

    updated_categories = []
    for category in set(categories_found):  # Используем set для уникальности
        success = SPREADSHEET.update_cell(category, CONFIG['point_value'])
        if success:
            updated_categories.append(category.capitalize())

    if updated_categories:
        return f"Успешно добавлено в категории: {', '.join(updated_categories)}."
    else:
        return "Произошла ошибка при обновлении таблицы. Проверьте логи на сервере."


@restricted
async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает обычные текстовые сообщения."""
    user_text = update.message.text
    logger.info(f"Получено текстовое сообщение: {user_text}")

    reply_message = await process_text_and_update_sheet(user_text)
    await update.message.reply_text(reply_message)


@restricted
async def handle_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает голосовые сообщения."""
    await update.message.reply_text("Получил голосовое, начинаю обработку...")

    file_id = update.message.voice.file_id
    voice_file = await context.bot.get_file(file_id)

    # Скачиваем файл во временную папку
    temp_file_path = f"temp_{file_id}.oga"
    await voice_file.download_to_drive(temp_file_path)

    try:
        # Распознаем речь
        recognized_text = TRANSCRIBER.transcribe(temp_file_path)
        logger.info(f"Распознанный текст: {recognized_text}")
        if not recognized_text:
            await update.message.reply_text("Не удалось распознать речь в сообщении.")
            return

        await update.message.reply_text(f"Распознал: \"{recognized_text}\"")

        # Обрабатываем и обновляем
        reply_message = await process_text_and_update_sheet(recognized_text)
        await update.message.reply_text(reply_message)

    except Exception as e:
        logger.error(f"Ошибка при обработке голосового сообщения: {e}")
        await update.message.reply_text("Произошла внутренняя ошибка. Попробуйте позже.")
    finally:
        # Удаляем временный файл
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)


def main():
    """Запуск бота."""
    # Проверка конфигурации
    token = CONFIG.get('telegram', {}).get('bot_token')
    if not token or token == "СЮДА_ВСТАВЬТЕ_ВАШ_ТОКЕН_ОТ_BOTFATHER":
        logger.critical("Токен бота не найден в config.yaml. Завершение работы.")
        return

    # Создание приложения
    application = Application.builder().token(token).build()

    # Регистрация обработчиков
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("my_id", my_id_command))

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice_message))

    # Запуск бота
    logger.info("Бот запущен и готов к работе...")
    application.run_polling()


if __name__ == "__main__":
    main()
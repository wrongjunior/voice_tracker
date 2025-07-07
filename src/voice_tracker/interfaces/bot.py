import logging
import os
import yaml
import locale  # <--- Добавлен импорт для установки локали
from functools import wraps
from datetime import datetime

from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode

from voice_tracker.core.transcriber import Transcriber
from voice_tracker.core.spreadsheet import SpreadsheetManager
from voice_tracker.utils.command_parser import parse_command
from voice_tracker.utils.config_loader import load_config

# --- Настройка локали для корректного отображения месяцев на русском ---
try:
    locale.setlocale(locale.LC_TIME, 'ru_RU.UTF-8')
except locale.Error:
    logger.warning("Русская локаль 'ru_RU.UTF-8' не найдена. Месяцы будут на английском.")
    # На Windows может потребоваться другой формат, например 'russian'
    try:
        locale.setlocale(locale.LC_TIME, 'russian')
    except locale.Error:
        logger.warning("Локаль 'russian' для Windows также не найдена.")


logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

def restricted(func):
    @wraps(func)
    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        config = context.bot_data['config']
        allowed_id = config.get('telegram', {}).get('allowed_user_id')
        if allowed_id == 0 or not allowed_id:
            if func.__name__ in ['start_command', 'help_command']: return await func(update, context, *args, **kwargs)
            else: await update.message.reply_text("Бот не настроен. Используйте /start для получения инструкций."); return
        if user_id != allowed_id: logger.warning(f"Неавторизованный доступ от user_id: {user_id}"); return
        return await func(update, context, *args, **kwargs)
    return wrapped

def format_stats_message(stats: dict) -> str:
    # --- Ключевое изменение в этой функции ---
    # '%B' теперь будет выводить русское название месяца благодаря locale.setlocale
    header = f"Отчет за {datetime.now().strftime('%d %B %Y г')}:\n"
    lines = [f"`{category.capitalize():<15} {value}`" for category, value in stats.items()]
    total_points = sum(stats.values()); footer = f"\n*Всего баллов:* {total_points}"
    return header + "\n".join(lines) + footer

async def process_text_and_update_sheet(text: str, context: ContextTypes.DEFAULT_TYPE) -> str:
    config = context.bot_data['config']
    spreadsheet = context.bot_data['spreadsheet']
    categories_found = parse_command(text, config['category_aliases'])
    if not categories_found: return "Не удалось распознать ни одной категории в сообщении."
    updated_categories = []
    for category in set(categories_found):
        current_stats, _ = spreadsheet.get_stats_for_today()
        current_value = current_stats.get(category, 0) if current_stats else 0
        if not isinstance(current_value, (int, float)): current_value = 0
        new_value = current_value + config['point_value']
        if spreadsheet.update_cell(category, new_value): updated_categories.append(category.capitalize())
    if updated_categories: return f"Данные обновлены для категорий: {', '.join(updated_categories)}."
    else: return "Произошла ошибка при обновлении таблицы. Проверьте логи на сервере."

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    config = context.bot_data['config']
    allowed_id = config.get('telegram', {}).get('allowed_user_id')
    welcome_text = f"Здравствуйте, {user.first_name}.\nЯ ваш персональный ассистент для трекинга задач.\n\n"
    if not allowed_id:
        setup_instruction = ("**Для начала работы, вам необходимо настроить доступ:**\n\n"
                             "1. Остановите этот скрипт (`Ctrl + C` в терминале).\n"
                             "2. Откройте файл `config/config.yaml`.\n"
                             "3. Найдите `allowed_user_id` и вставьте туда ваш ID.\n\n"
                             f"Ваш Telegram User ID: `{user.id}`\n\n"
                             "4. Сохраните файл и перезапустите скрипт.")
        await update.message.reply_text(welcome_text + setup_instruction, parse_mode=ParseMode.MARKDOWN)
    else: await update.message.reply_text(welcome_text + "Бот готов к работе. Используйте /help для просмотра команд.")

@restricted
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = ("*Как пользоваться ботом:*\n"
                 "Отправьте голосовое или текстовое сообщение, описывающее вашу активность.\n"
                 "_Пример: «Сегодня была продуктивная тренировка и я поработал над проектами»_\n\n"
                 "*Доступные команды:*\n"
                 "`/stats` - Показать статистику за сегодня.\n"
                 "`/help` - Показать это справочное сообщение.")
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

@restricted
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    spreadsheet = context.bot_data['spreadsheet']
    stats, error = spreadsheet.get_stats_for_today()
    if error: await update.message.reply_text(f"Ошибка получения статистики: {error}"); return
    if not stats or not any(stats.values()): await update.message.reply_text("На сегодня данных еще нет."); return
    message = format_stats_message(stats)
    await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)

@restricted
async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text; logger.info(f"Получено текстовое сообщение: '{user_text}'")
    reply_message = await process_text_and_update_sheet(user_text, context)
    await update.message.reply_text(reply_message)

@restricted
async def handle_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Обрабатываю голосовое сообщение...")
    transcriber = context.bot_data['transcriber']
    voice_file = await update.message.voice.get_file()
    temp_file_path = f"temp_{voice_file.file_id}.oga"
    try:
        await voice_file.download_to_drive(custom_path=temp_file_path)
        recognized_text = transcriber.transcribe(temp_file_path)
        logger.info(f"Распознанный текст: '{recognized_text}'")
        if not recognized_text: await update.message.reply_text("Не удалось распознать речь."); return
        await update.message.reply_text(f"Распознано: _{recognized_text}_", parse_mode=ParseMode.MARKDOWN)
        reply_message = await process_text_and_update_sheet(recognized_text, context)
        await update.message.reply_text(reply_message)
    except Exception as e:
        logger.error(f"Ошибка при обработке голосового сообщения: {e}", exc_info=True)
        await update.message.reply_text("Произошла внутренняя ошибка при обработке файла.")
    finally:
        if os.path.exists(temp_file_path): os.remove(temp_file_path)

async def post_init(application: Application):
    await application.bot.set_my_commands([
        BotCommand("start", "Перезапустить и проверить статус"),
        BotCommand("stats", "Статистика за сегодня"),
        BotCommand("help", "Справка по использованию"),
    ])

def run(config_path: str):
    config = load_config(config_path)
    token = config.get('telegram', {}).get('bot_token')
    if not token or "ВАШ_ТОКЕН" in token:
        logger.critical("Токен бота не найден или не изменен в config.yaml.")
        return
    builder = Application.builder().token(token)
    builder.post_init(post_init)
    application = builder.build()
    application.bot_data['config'] = config
    application.bot_data['spreadsheet'] = SpreadsheetManager(config)
    application.bot_data['transcriber'] = Transcriber(config['whisper'])
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice_message))
    logger.info("Бот запущен...")
    application.run_polling()
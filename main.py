import argparse
import sys
import os

# Добавляем папку src в путь, чтобы можно было импортировать voice_tracker
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

# Теперь импортируем из нашего пакета
from voice_tracker.interfaces import cli, bot
from voice_tracker.utils.config_loader import get_config_path


def main():
    """Главная точка входа, управляющая режимами запуска."""
    parser = argparse.ArgumentParser(
        description="Voice Tracker: Отслеживайте задачи голосом или через Telegram.",
        formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument(
        "mode",
        choices=["cli", "bot"],
        nargs='?',
        default="cli",
        help="Режим запуска приложения:\n"
             "  cli - запуск в режиме командной строки (по умолчанию).\n"
             "  bot - запуск Telegram-бота."
    )

    args = parser.parse_args()
    config_path = get_config_path()

    if args.mode == "cli":
        print("Запуск в режиме командной строки (CLI)...")
        cli.run(config_path)
    elif args.mode == "bot":
        print("Запуск Telegram-бота...")
        bot.run(config_path)


if __name__ == "__main__":
    main()
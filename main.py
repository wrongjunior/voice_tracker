import yaml
from spreadsheet_manager import SpreadsheetManager
from audio_handler import record_audio, cleanup_audio_file
from transcriber import Transcriber
from command_parser import parse_command


def load_config(config_path="config.yaml"):
    """Загружает конфигурацию из YAML файла."""
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def main():
    try:
        # 1. Загрузка конфигурации
        config = load_config()

        # 2. Инициализация менеджеров
        spreadsheet = SpreadsheetManager(
            file_path=config['excel_file_path'],
            backup_folder=config['backup_folder'],
            categories_map=config['categories']
        )
        transcriber = Transcriber(
            model_size=config['whisper']['model_size'],
            language=config['whisper']['language']
        )

        # 3. Основной цикл программы
        while True:
            print("\n" + "=" * 40)
            print("Готов к работе. Нажмите Enter, чтобы начать запись голоса.")
            input()  # Ждем нажатия Enter для начала

            audio_file = None
            try:
                # 4. Запись и распознавание
                audio_file = record_audio()
                recognized_text = transcriber.transcribe(audio_file)

                if not recognized_text:
                    print("Не удалось распознать речь. Попробуйте еще раз.")
                    continue

                print(f"Распознано: '{recognized_text}'")

                # 5. Анализ команды
                category = parse_command(recognized_text, config['category_aliases'])

                # 6. Обновление таблицы
                if category:
                    spreadsheet.update_cell(category, config['point_value'])
                else:
                    print("Команда не выполнена. Не удалось определить категорию.")

            except FileNotFoundError as e:
                print(f"Критическая ошибка: {e}")
                print("Проверьте путь к файлу в config.yaml и наличие самого файла.")
                break
            except Exception as e:
                print(f"Произошла непредвиденная ошибка: {e}")
            finally:
                # Очищаем временный аудиофайл
                if audio_file:
                    cleanup_audio_file(audio_file)

    except KeyboardInterrupt:
        print("\nПрограмма завершена пользователем.")
    except Exception as e:
        print(f"\nКритическая ошибка при запуске: {e}")


if __name__ == "__main__":
    main()
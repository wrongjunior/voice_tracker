from voice_tracker.utils.audio import record_audio, cleanup_audio_file
from voice_tracker.core.transcriber import Transcriber
from voice_tracker.utils.command_parser import parse_command
from voice_tracker.core.spreadsheet import SpreadsheetManager
from voice_tracker.utils.config_loader import load_config


def run(config_path: str):
    config = load_config(config_path)
    spreadsheet = SpreadsheetManager(config)
    transcriber = Transcriber(config['whisper'])

    try:
        while True:
            print("\n" + "=" * 40)
            print("Готов к работе. Нажмите Enter, чтобы начать запись голоса.")
            input()

            audio_file = None
            try:
                audio_file = record_audio()
                text = transcriber.transcribe(audio_file)
                if not text:
                    print("Не удалось распознать речь.")
                    continue
                print(f"Распознано: '{text}'")

                categories = parse_command(text, config['category_aliases'])
                if not categories:
                    print("Категории не найдены.")
                    continue

                for category in set(categories):
                    current_stats, _ = spreadsheet.get_stats_for_today()
                    current_value = current_stats.get(category, 0) if current_stats else 0
                    if not isinstance(current_value, (int, float)): current_value = 0
                    new_value = current_value + config['point_value']
                    spreadsheet.update_cell(category, new_value)

            except Exception as e:
                print(f"Произошла ошибка в цикле: {e}")
            finally:
                if audio_file:
                    cleanup_audio_file(audio_file)
    except KeyboardInterrupt:
        print("\nПрограмма завершена.")
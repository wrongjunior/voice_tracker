import whisper

class Transcriber:
    def __init__(self, model_size="base", language="ru"):
        print(f"Загрузка модели Whisper '{model_size}'... Это может занять некоторое время.")
        self.model = whisper.load_model(model_size)
        self.language = language
        print("Модель загружена.")

    def transcribe(self, audio_path):
        """Распознает текст из аудиофайла."""
        try:
            result = self.model.transcribe(audio_path, language=self.language, fp16=False) # fp16=False для лучшей совместимости с CPU
            return result['text'].strip()
        except Exception as e:
            print(f"Ошибка при распознавании речи: {e}")
            return ""
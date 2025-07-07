import whisper

class Transcriber:
    def __init__(self, config: dict):
        model_size = config.get('model_size', 'base')
        print(f"Загрузка модели Whisper '{model_size}'... Это может занять некоторое время.")
        self.model = whisper.load_model(model_size)
        self.language = config.get('language', 'ru')
        print("Модель загружена.")

    def transcribe(self, audio_path: str) -> str:
        try:
            result = self.model.transcribe(audio_path, language=self.language, fp16=False)
            return result['text'].strip()
        except Exception as e:
            print(f"Ошибка при распознавании речи: {e}")
            return ""
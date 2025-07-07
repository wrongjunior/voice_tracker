import sounddevice as sd
import numpy as np
import scipy.io.wavfile as wav
import tempfile
import os


def record_audio(samplerate=16000):
    """
    Записывает аудио с микрофона до нажатия Enter и сохраняет во временный WAV файл.
    """
    print("Нажмите Enter, чтобы остановить запись...")

    # Мы будем записывать аудио в список чанков (кусков)
    recording = []

    def callback(indata, frames, time, status):
        if status:
            print(status)
        recording.append(indata.copy())

    # Начинаем запись в фоновом режиме
    stream = sd.InputStream(callback=callback, samplerate=samplerate, channels=1, dtype='int16')
    with stream:
        input()  # Ждем, пока пользователь нажмет Enter

    # Объединяем все чанки в один numpy массив
    full_recording = np.concatenate(recording, axis=0)

    # Сохраняем во временный файл
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav', prefix='recorded_')
    wav.write(temp_file.name, samplerate, full_recording)

    print(f"Запись сохранена в: {temp_file.name}")
    return temp_file.name


def cleanup_audio_file(file_path):
    """Удаляет временный аудиофайл."""
    try:
        os.remove(file_path)
        print(f"Временный файл {file_path} удален.")
    except OSError as e:
        print(f"Ошибка при удалении файла {file_path}: {e}")
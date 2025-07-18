# Voice Tracker

Voice Tracker переводит ваши голосовые заметки в конкретные баллы в Excel, автоматически определяя ключевые действия из вашей речи.

---

## Что важно знать?

1.  Чтобы зафиксировать событие, не нужно искать нужную строку или открывать таблицу вручную. Просто произнесите вслух, что сделали.
2.  Вы сами решаете, какие категории отслеживать и какие слова будут ключевыми. Все параметры задаются в одном файле - `config/config.yaml`.
3.  Перед каждым изменением автоматически создаётся резервная копия. Вы можете спокойно экспериментировать с настройками, не переживая за свои записи.

## Как это работает?

`Запускаете → записываете аудио → трекер распознаёт фразы (Whisper) → определяет категории → обновляет таблицу`

## Быстрый старт

#### Требования к системе

-   Python 3.8+
-   FFmpeg (стандартная библиотека для работы с медиа)

#### Установка

1.  **Установите FFmpeg:**
    -   На macOS: `brew install ffmpeg`
    -   На других ОС следуйте официальной инструкции с сайта ffmpeg.org.

2.  **Разверните проект:**
    ```bash
    git clone https://github.com/wrongjunior/voice_tracker.git
    cd voice_tracker
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```

3.  **Настройте конфигурацию:**
    ```bash
    # Создайте свой файл конфигурации из примера
    cp config/config.example.yaml config/config.yaml
    mkdir backups
    ```
    Откройте `config/config.yaml` и укажите путь к вашему Excel-файлу, токен для Telegram и другие параметры.

4.  В вашем Excel-файле первая строка должна содержать даты (числа месяца), а первый столбец - названия ваших категорий.

## Использование

Приложение имеет два режима работы, которые указываются при запуске.

### 1. Командная строка (CLI)

Использует микрофон вашего компьютера.
```bash
# Запустите скрипт (режим 'cli' используется по умолчанию)
python3 main.py
```
Нажмите `Enter`, проговорите, что сделали, и снова нажмите `Enter`. Запись автоматически появится в Excel.

### 2. Telegram-бот

Запускает бота для удаленного взаимодействия.
```bash
python3 main.py bot
```
При первом запуске отправьте боту команду `/start`, чтобы узнать свой `user_id` и завершить настройку в `config/config.yaml`.

## Что дальше?

-   [ ] Синхронизация с Google Sheets.
-   [ ] Анализ итогов дня с помощью локальной LLM.
-   [ ] Написание автоматизированных тестов для обеспечения стабильности.

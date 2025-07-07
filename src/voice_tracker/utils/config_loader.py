import yaml
import os

DEFAULT_CONFIG_PATH = "config/config.yaml"

def get_config_path() -> str:
    return DEFAULT_CONFIG_PATH

def load_config(config_path: str) -> dict:
    if not os.path.exists(config_path):
        print(f"Ошибка: Файл конфигурации не найден по пути '{config_path}'")
        print(f"Пожалуйста, скопируйте 'config/config.example.yaml' в '{config_path}' и настройте его.")
        exit(1)
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Ошибка при чтении файла конфигурации: {e}")
        exit(1)
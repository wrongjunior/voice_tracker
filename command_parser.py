def parse_command(text, category_aliases):
    """
    Анализирует текст и ищет первое совпадение с алиасами категорий.
    """
    text_lower = text.lower()
    print(f"Анализ текста: '{text_lower}'")

    for category, aliases in category_aliases.items():
        for alias in aliases:
            if alias.lower() in text_lower:
                print(f"Найдена категория: '{category}' по ключевому слову '{alias}'")
                return category

    print("В команде не найдено ни одной известной категории.")
    return None
def parse_command(text: str, category_aliases: dict) -> list:
    text_lower = text.lower()
    found_categories = []
    print(f"Анализ текста: '{text_lower}'")
    for category, aliases in category_aliases.items():
        for alias in aliases:
            if alias.lower() in text_lower:
                print(f"Найдена категория: '{category}' по ключевому слову '{alias}'")
                found_categories.append(category)
                break
    if not found_categories:
        print("В команде не найдено ни одной известной категории.")
    return found_categories
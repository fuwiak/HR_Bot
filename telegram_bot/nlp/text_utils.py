"""
Утилиты для работы с текстом
"""
import re
import logging

log = logging.getLogger(__name__)


def init_fuzzy_matcher():
    """Инициализация нечеткого поиска"""
    try:
        from fuzzywuzzy import fuzz, process
        return True
    except ImportError:
        log.warning("fuzzywuzzy not available, using basic parsing")
        return False


# Глобальный флаг доступности fuzzywuzzy
fuzzy_available = init_fuzzy_matcher()


def find_best_match(word: str, choices: list, threshold: int = 80) -> str:
    """Находит лучшее совпадение с помощью нечеткого поиска"""
    if not fuzzy_available:
        return None
    
    try:
        from fuzzywuzzy import process, fuzz
        result = process.extractOne(word, choices, scorer=fuzz.ratio)
        if result and result[1] >= threshold:
            return result[0]
    except Exception as e:
        log.debug(f"Error in fuzzy matching '{word}': {e}")
    
    return None


def remove_markdown(text: str) -> str:
    """Удаляет Markdown форматирование из текста (более агрессивная версия)"""
    if not text:
        return text
    
    # Убираем множественные звездочки (***текст***, **текст**, *текст*)
    text = re.sub(r'\*{3,}([^*]+)\*{3,}', r'\1', text)  # ***текст***
    text = re.sub(r'\*{2}([^*]+)\*{2}', r'\1', text)  # **текст**
    text = re.sub(r'\*{1}([^*\s]+[^*]*?)\*{1}(?=\s|$|[.,!?;:])', r'\1', text)  # *текст* (но не в начале строки)
    text = re.sub(r'(?<!\*)\*([^*\s]+[^*]*?)\*(?!\*)', r'\1', text)  # *текст* (одиночные звездочки)
    
    # Убираем подчеркивания
    text = re.sub(r'__([^_]+)__', r'\1', text)  # __текст__
    text = re.sub(r'_([^_]+)_', r'\1', text)  # _текст_
    
    # Убираем заголовки
    text = re.sub(r'###+\s*', '', text)  # ### заголовок
    text = re.sub(r'##+\s*', '', text)  # ## заголовок
    text = re.sub(r'#+\s*', '', text)  # # заголовок
    
    # Убираем код
    text = re.sub(r'`([^`]+)`', r'\1', text)  # `код`
    
    # Убираем зачеркивание
    text = re.sub(r'~~([^~]+)~~', r'\1', text)  # ~~текст~~
    
    # Убираем лишние пробелы после удаления форматирования
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()

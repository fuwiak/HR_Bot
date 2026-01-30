"""
Парсер для извлечения метаданных из новостей HR Time
Извлекает: заголовок, автора, категорию, метрики, дату, URL
"""
import logging
import re
from typing import Dict, Optional
from datetime import datetime

log = logging.getLogger(__name__)


class HRTimeNewsParser:
    """Парсер для новостей HR Time"""
    
    def __init__(self):
        # Паттерны для извлечения данных
        self.category_patterns = {
            "Вопросы и ответы": ["вопрос", "ответ", "q&a", "qa"],
            "HR-КЛУБ": ["клуб", "club", "материал", "статья"],
            "Отзывы": ["отзыв", "review", "рейтинг"],
            "Запросы": ["запрос", "заказ", "request", "order", "проект"]
        }
    
    def parse_news(self, text: str, raw_data: Optional[Dict] = None) -> Dict:
        """
        Парсит новость и извлекает метаданные
        
        Args:
            text: Текст новости
            raw_data: Дополнительные данные (date, chat_username и т.д.)
        
        Returns:
            Словарь с распарсенными данными
        """
        if not raw_data:
            raw_data = {}
        
        # Извлекаем заголовок (первая строка или до первого переноса)
        title = self._extract_title(text)
        
        # Извлекаем автора
        author = self._extract_author(text, raw_data)
        
        # Определяем категорию
        category = self._extract_category(text)
        
        # Извлекаем метрики
        metrics = self._extract_metrics(text)
        
        # Извлекаем дату
        date = self._extract_date(raw_data.get("date"))
        
        # Извлекаем URL (если есть)
        url = self._extract_url(text, raw_data)
        
        # Определяем тип контента
        content_type = self._determine_content_type(text, category)
        
        return {
            "id": raw_data.get("message_id", ""),
            "title": title,
            "content": self._extract_content(text),
            "author": author,
            "date": date,
            "type": content_type,
            "url": url,
            "category": category,
            "metrics": metrics
        }
    
    def _extract_title(self, text: str) -> str:
        """Извлекает заголовок из текста"""
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        if not lines:
            return "Новость из HR Time"
        
        # Первая строка часто является заголовком
        first_line = lines[0]
        
        # Если первая строка слишком длинная, берем первые слова
        if len(first_line) > 100:
            words = first_line.split()
            title = " ".join(words[:15])
            if len(title) > 100:
                title = title[:97] + "..."
            return title
        
        return first_line
    
    def _extract_content(self, text: str) -> str:
        """Извлекает краткое содержание (2-3 строки)"""
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        if len(lines) <= 1:
            # Если одна строка, берем первые 200 символов
            return text[:200] + ("..." if len(text) > 200 else "")
        
        # Берем первые 2-3 строки
        content_lines = lines[1:4]  # Пропускаем первую (заголовок)
        content = "\n".join(content_lines)
        
        if len(content) > 300:
            content = content[:297] + "..."
        
        return content
    
    def _extract_author(self, text: str, raw_data: Dict) -> Dict:
        """Извлекает информацию об авторе"""
        author_name = raw_data.get("chat_username", "HR Time")
        
        # Пытаемся найти имя автора в тексте
        author_patterns = [
            r'автор[:\s]+([^\n]+)',
            r'от[:\s]+([^\n]+)',
            r'👤\s*([^\n]+)',
            r'Автор[:\s]+([^\n]+)'
        ]
        
        for pattern in author_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                author_name = match.group(1).strip()
                break
        
        # Пытаемся определить статус автора
        status = self._extract_author_status(text, author_name)
        
        return {
            "name": author_name,
            "status": status,
            "reviews_count": 0  # По умолчанию, можно улучшить
        }
    
    def _extract_author_status(self, text: str, author_name: str) -> str:
        """Извлекает статус автора"""
        text_lower = text.lower()
        author_lower = author_name.lower()
        
        status_keywords = {
            "топ-30": ["топ-30", "top-30", "top30"],
            "топ-100": ["топ-100", "top-100", "top100"],
            "спецназ": ["спецназ", "spetsnaz"],
            "hr-клуб": ["hr-клуб", "hr-club", "hr клуб"],
            "pro": ["pro", "про"]
        }
        
        for status, keywords in status_keywords.items():
            if any(keyword in text_lower or keyword in author_lower for keyword in keywords):
                return status
        
        return ""
    
    def _extract_category(self, text: str) -> str:
        """Определяет категорию новости"""
        text_lower = text.lower()
        
        for category, keywords in self.category_patterns.items():
            if any(keyword in text_lower for keyword in keywords):
                return category
        
        return "Общее"
    
    def _extract_metrics(self, text: str) -> Dict:
        """Извлекает метрики из текста"""
        metrics = {
            "views": 0,
            "comments": 0,
            "rating": 0
        }
        
        # Просмотры
        views_patterns = [
            r'просмотр[ов]*[:\s]*(\d+)',
            r'👁[️\s]*(\d+)',
            r'views?[:\s]*(\d+)'
        ]
        for pattern in views_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    metrics["views"] = int(match.group(1))
                    break
                except:
                    pass
        
        # Комментарии
        comments_patterns = [
            r'комментари[евя]*[:\s]*(\d+)',
            r'💬[️\s]*(\d+)',
            r'comments?[:\s]*(\d+)'
        ]
        for pattern in comments_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    metrics["comments"] = int(match.group(1))
                    break
                except:
                    pass
        
        # Рейтинг
        rating_patterns = [
            r'рейтинг[:\s]*([\d.]+)',
            r'⭐[️\s]*([\d.]+)',
            r'rating[:\s]*([\d.]+)'
        ]
        for pattern in rating_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    metrics["rating"] = float(match.group(1))
                    break
                except:
                    pass
        
        return metrics
    
    def _extract_date(self, date_value) -> Optional[datetime]:
        """Извлекает и парсит дату"""
        if not date_value:
            return datetime.now()
        
        if isinstance(date_value, datetime):
            return date_value
        
        if isinstance(date_value, str):
            try:
                # Пробуем разные форматы
                formats = [
                    "%Y-%m-%d %H:%M:%S",
                    "%Y-%m-%dT%H:%M:%S",
                    "%Y-%m-%dT%H:%M:%SZ",
                    "%d.%m.%Y %H:%M",
                    "%d/%m/%Y %H:%M"
                ]
                
                for fmt in formats:
                    try:
                        return datetime.strptime(date_value, fmt)
                    except:
                        continue
                
                # Если ничего не подошло, пробуем ISO формат
                if "T" in date_value:
                    return datetime.fromisoformat(date_value.replace("Z", "+00:00"))
            except:
                pass
        
        return datetime.now()
    
    def _extract_url(self, text: str, raw_data: Dict) -> str:
        """Извлекает URL из текста или данных"""
        # Ищем URL в тексте
        url_pattern = r'https?://[^\s]+'
        match = re.search(url_pattern, text)
        if match:
            return match.group(0)
        
        # Пробуем получить из raw_data
        raw = raw_data.get("raw", {})
        if isinstance(raw, dict):
            entities = raw.get("entities", [])
            for entity in entities:
                if entity.get("type") == "url":
                    return entity.get("url", "")
        
        return ""
    
    def _determine_content_type(self, text: str, category: str) -> str:
        """Определяет тип контента"""
        text_lower = text.lower()
        
        if "вопрос" in text_lower or "ответ" in text_lower:
            return "discussion"
        elif "материал" in text_lower or "статья" in text_lower:
            return "material"
        elif "отзыв" in text_lower or "review" in text_lower:
            return "review"
        elif "запрос" in text_lower or "заказ" in text_lower or "проект" in text_lower:
            return "request"
        else:
            return "general"

"""
Система оценки новостей HR Time (как Yandex Mail)
Оценивает новости от 1 до 5 звезд на основе 5 критериев
"""
import logging
import re
from typing import Dict, Optional
from datetime import datetime, timedelta

log = logging.getLogger(__name__)

# Ключевые слова для определения релевантности
HR_KEYWORDS = [
    "рекрутинг", "подбор", "управление", "мотивация", "hr-процессы",
    "hr", "персонал", "кадры", "сотрудники", "найм", "отбор",
    "интервью", "оценка", "развитие", "обучение", "адаптация",
    "компенсация", "бонусы", "kpi", "цели", "проект", "заказ"
]

# Статусы авторов (приоритет)
AUTHOR_STATUSES = {
    "топ-30": 5,
    "top-30": 5,
    "топ-100": 4,
    "top-100": 4,
    "спецназ": 4,
    "spetsnaz": 4,
    "hr-клуб": 3,
    "hr-club": 3,
    "pro": 3,
    "про": 2
}


class HRTimeNewsScorer:
    """Система оценки новостей HR Time"""
    
    def __init__(self):
        self.weights = {
            "relevance": 0.30,      # Релевантность (30%)
            "popularity": 0.25,    # Популярность (25%)
            "freshness": 0.20,      # Свежесть (20%)
            "authority": 0.15,      # Авторитет источника (15%)
            "interactivity": 0.10   # Интерактивность (10%)
        }
    
    def calculate_relevance_score(self, text: str, title: str = "") -> float:
        """
        Оценивает релевантность контента (0.0-1.0)
        
        Критерии:
        - Наличие ключевых слов HR/рекрутинга
        - Соответствие профилю пользователя
        """
        full_text = f"{title} {text}".lower()
        
        # Подсчитываем количество ключевых слов
        keyword_count = sum(1 for keyword in HR_KEYWORDS if keyword in full_text)
        
        # Нормализуем (максимум 10 ключевых слов = 1.0)
        relevance = min(keyword_count / 10.0, 1.0)
        
        # Бонус за наличие нескольких ключевых слов
        if keyword_count >= 5:
            relevance = min(relevance + 0.2, 1.0)
        elif keyword_count >= 3:
            relevance = min(relevance + 0.1, 1.0)
        
        return relevance
    
    def calculate_popularity_score(self, metrics: Dict) -> float:
        """
        Оценивает популярность контента (0.0-1.0)
        
        Критерии:
        - Количество комментариев (более 20 = 1.0)
        - Количество просмотров (более 500 = 1.0)
        - Рейтинг материала
        """
        comments = metrics.get("comments", 0)
        views = metrics.get("views", 0)
        rating = metrics.get("rating", 0)
        
        # Оценка по комментариям (0-1.0)
        comments_score = min(comments / 20.0, 1.0) if comments else 0.0
        
        # Оценка по просмотрам (0-1.0)
        views_score = min(views / 500.0, 1.0) if views else 0.0
        
        # Оценка по рейтингу (0-1.0, предполагаем шкалу 0-5)
        rating_score = min(rating / 5.0, 1.0) if rating else 0.0
        
        # Взвешенная сумма
        popularity = (
            comments_score * 0.4 +
            views_score * 0.4 +
            rating_score * 0.2
        )
        
        return min(popularity, 1.0)
    
    def calculate_freshness_score(self, date: Optional[datetime]) -> float:
        """
        Оценивает свежесть контента (0.0-1.0)
        
        Критерии:
        - Новые (менее 1 часа) = 1.0
        - Свежие (1-6 часов) = 0.8
        - Средние (6-24 часов) = 0.6
        - Старые (24-48 часов) = 0.4
        - Очень старые (более 48 часов) = 0.2
        """
        if not date:
            return 0.5  # Средняя оценка, если дата неизвестна
        
        now = datetime.now()
        if isinstance(date, str):
            # Пытаемся распарсить строку
            try:
                if "T" in date:
                    date = datetime.fromisoformat(date.replace("Z", "+00:00"))
                else:
                    date = datetime.strptime(date, "%Y-%m-%d %H:%M:%S")
            except:
                return 0.5
        
        time_diff = now - date if isinstance(date, datetime) else timedelta(hours=24)
        hours = time_diff.total_seconds() / 3600
        
        if hours < 1:
            return 1.0  # Менее 1 часа
        elif hours < 6:
            return 0.8  # 1-6 часов
        elif hours < 24:
            return 0.6  # 6-24 часа
        elif hours < 48:
            return 0.4  # 24-48 часов
        else:
            return 0.2  # Более 48 часов
    
    def calculate_authority_score(self, author: Dict) -> float:
        """
        Оценивает авторитет источника (0.0-1.0)
        
        Критерии:
        - Статус автора (ТОП-30, ТОП-100, СПЕЦНАЗ, HR-КЛУБ, PRO)
        - Количество отзывов
        - История взаимодействия
        """
        author_name = author.get("name", "").lower()
        author_status = author.get("status", "").lower()
        reviews_count = author.get("reviews_count", 0)
        
        # Оценка по статусу
        status_score = 0.5  # Базовая оценка
        for status, score in AUTHOR_STATUSES.items():
            if status in author_status or status in author_name:
                status_score = score / 5.0
                break
        
        # Оценка по количеству отзывов
        reviews_score = min(reviews_count / 50.0, 1.0) if reviews_count else 0.0
        
        # Комбинированная оценка
        authority = status_score * 0.7 + reviews_score * 0.3
        
        return min(authority, 1.0)
    
    def calculate_interactivity_score(self, metrics: Dict, text: str) -> float:
        """
        Оценивает интерактивность (0.0-1.0)
        
        Критерии:
        - Есть ли прямые вопросы в тексте
        - Количество комментариев
        - Активность дискуссии
        """
        # Проверяем наличие вопросов в тексте
        question_patterns = [
            r'\?',  # Вопросительный знак
            r'как\s+', r'что\s+', r'где\s+', r'когда\s+', r'почему\s+',
            r'помогите', r'подскажите', r'нужна\s+помощь'
        ]
        
        has_questions = any(re.search(pattern, text.lower()) for pattern in question_patterns)
        question_score = 0.5 if has_questions else 0.0
        
        # Оценка по комментариям
        comments = metrics.get("comments", 0)
        comments_score = min(comments / 10.0, 1.0) if comments else 0.0
        
        # Комбинированная оценка
        interactivity = question_score * 0.6 + comments_score * 0.4
        
        return min(interactivity, 1.0)
    
    def calculate_total_score(self, news_data: Dict) -> Dict:
        """
        Рассчитывает общую оценку новости (1-5 звезд)
        
        Args:
            news_data: Словарь с данными новости:
                - text: текст новости
                - title: заголовок
                - date: дата публикации
                - author: информация об авторе
                - metrics: метрики (views, comments, rating)
        
        Returns:
            Словарь с оценками:
                - total_score: общая оценка (0.0-1.0)
                - stars: количество звезд (1-5)
                - urgency: уровень срочности
                - breakdown: детализация по критериям
        """
        text = news_data.get("text", "")
        title = news_data.get("title", "")
        date = news_data.get("date")
        author = news_data.get("author", {})
        metrics = news_data.get("metrics", {})
        
        # Рассчитываем оценки по каждому критерию
        relevance = self.calculate_relevance_score(text, title)
        popularity = self.calculate_popularity_score(metrics)
        freshness = self.calculate_freshness_score(date)
        authority = self.calculate_authority_score(author)
        interactivity = self.calculate_interactivity_score(metrics, text)
        
        # Взвешенная сумма
        total_score = (
            relevance * self.weights["relevance"] +
            popularity * self.weights["popularity"] +
            freshness * self.weights["freshness"] +
            authority * self.weights["authority"] +
            interactivity * self.weights["interactivity"]
        )
        
        # Преобразуем в звезды (1-5)
        stars = self._score_to_stars(total_score)
        
        # Определяем уровень срочности
        urgency = self._get_urgency_level(stars)
        
        return {
            "total_score": total_score,
            "stars": stars,
            "urgency": urgency,
            "breakdown": {
                "relevance": relevance,
                "popularity": popularity,
                "freshness": freshness,
                "authority": authority,
                "interactivity": interactivity
            }
        }
    
    def _score_to_stars(self, score: float) -> int:
        """Преобразует оценку (0.0-1.0) в звезды (1-5)"""
        if score >= 0.9:
            return 5
        elif score >= 0.7:
            return 4
        elif score >= 0.5:
            return 3
        elif score >= 0.3:
            return 2
        else:
            return 1
    
    def _get_urgency_level(self, stars: int) -> str:
        """Определяет уровень срочности на основе звезд"""
        urgency_map = {
            5: "КРИТИЧНО",
            4: "ВЫСОКО",
            3: "НОРМАЛЬНО",
            2: "НИЗКО",
            1: "ОЧЕНЬ НИЗКО"
        }
        return urgency_map.get(stars, "НОРМАЛЬНО")
    
    def should_publish(self, news_data: Dict, min_stars: int = 2) -> bool:
        """
        Определяет, нужно ли публиковать новость
        
        Args:
            news_data: Данные новости
            min_stars: Минимальное количество звезд для публикации
        
        Returns:
            True если новость нужно опубликовать
        """
        score_result = self.calculate_total_score(news_data)
        stars = score_result["stars"]
        
        # Проверяем минимальный порог
        if stars < min_stars:
            return False
        
        # Исключаем старый контент (более 7 дней)
        date = news_data.get("date")
        if date:
            if isinstance(date, str):
                try:
                    if "T" in date:
                        date = datetime.fromisoformat(date.replace("Z", "+00:00"))
                    else:
                        date = datetime.strptime(date, "%Y-%m-%d %H:%M:%S")
                except:
                    return True  # Если не удалось распарсить, публикуем
            
            if isinstance(date, datetime):
                days_old = (datetime.now() - date).days
                if days_old > 7:
                    return False
        
        return True

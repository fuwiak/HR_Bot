"""
Тесты для системы оценки новостей HR Time
"""
import unittest
from datetime import datetime, timedelta
from services.services.hrtime_news_scorer import HRTimeNewsScorer
from services.services.hrtime_news_parser import HRTimeNewsParser


class TestHRTimeNewsScorer(unittest.TestCase):
    """Тесты для системы оценки новостей"""
    
    def setUp(self):
        """Инициализация перед каждым тестом"""
        self.scorer = HRTimeNewsScorer()
        self.parser = HRTimeNewsParser()
    
    def test_relevance_score_high(self):
        """Тест оценки релевантности для высокорелевантного контента"""
        text = "Вопрос по рекрутингу персонала. Нужна помощь с подбором HR-специалистов. Как провести интервью?"
        title = "Рекрутинг и подбор персонала"
        
        score = self.scorer.calculate_relevance_score(text, title)
        self.assertGreaterEqual(score, 0.7, "Высокорелевантный контент должен иметь оценку >= 0.7")
    
    def test_relevance_score_low(self):
        """Тест оценки релевантности для низкорелевантного контента"""
        text = "Обычное сообщение без ключевых слов"
        title = "Заголовок"
        
        score = self.scorer.calculate_relevance_score(text, title)
        self.assertLessEqual(score, 0.3, "Низкорелевантный контент должен иметь оценку <= 0.3")
    
    def test_popularity_score_high(self):
        """Тест оценки популярности для популярного контента"""
        metrics = {
            "views": 1000,
            "comments": 50,
            "rating": 4.8
        }
        
        score = self.scorer.calculate_popularity_score(metrics)
        self.assertGreaterEqual(score, 0.8, "Популярный контент должен иметь оценку >= 0.8")
    
    def test_popularity_score_low(self):
        """Тест оценки популярности для непопулярного контента"""
        metrics = {
            "views": 10,
            "comments": 0,
            "rating": 0
        }
        
        score = self.scorer.calculate_popularity_score(metrics)
        self.assertLessEqual(score, 0.3, "Непопулярный контент должен иметь оценку <= 0.3")
    
    def test_freshness_score_new(self):
        """Тест оценки свежести для нового контента"""
        date = datetime.now() - timedelta(minutes=30)  # 30 минут назад
        
        score = self.scorer.calculate_freshness_score(date)
        self.assertEqual(score, 1.0, "Новый контент (менее 1 часа) должен иметь оценку 1.0")
    
    def test_freshness_score_old(self):
        """Тест оценки свежести для старого контента"""
        date = datetime.now() - timedelta(days=3)  # 3 дня назад
        
        score = self.scorer.calculate_freshness_score(date)
        self.assertLessEqual(score, 0.3, "Старый контент должен иметь оценку <= 0.3")
    
    def test_authority_score_top30(self):
        """Тест оценки авторитета для ТОП-30 автора"""
        author = {
            "name": "Иван Иванов ТОП-30",
            "status": "топ-30",
            "reviews_count": 100
        }
        
        score = self.scorer.calculate_authority_score(author)
        self.assertGreaterEqual(score, 0.8, "ТОП-30 автор должен иметь оценку >= 0.8")
    
    def test_authority_score_regular(self):
        """Тест оценки авторитета для обычного автора"""
        author = {
            "name": "Обычный автор",
            "status": "",
            "reviews_count": 5
        }
        
        score = self.scorer.calculate_authority_score(author)
        self.assertLessEqual(score, 0.6, "Обычный автор должен иметь оценку <= 0.6")
    
    def test_interactivity_score_with_questions(self):
        """Тест оценки интерактивности для контента с вопросами"""
        text = "Как правильно провести интервью? Подскажите, пожалуйста. Нужна помощь!"
        metrics = {
            "comments": 15
        }
        
        score = self.scorer.calculate_interactivity_score(metrics, text)
        self.assertGreaterEqual(score, 0.5, "Контент с вопросами должен иметь оценку >= 0.5")
    
    def test_total_score_high_quality(self):
        """Тест общей оценки для высококачественной новости"""
        news_data = {
            "text": "Вопрос по рекрутингу персонала. Нужна помощь с подбором HR-специалистов. Как провести интервью?",
            "title": "Рекрутинг и подбор персонала",
            "date": datetime.now() - timedelta(minutes=30),
            "author": {
                "name": "Иван Иванов ТОП-30",
                "status": "топ-30",
                "reviews_count": 100
            },
            "metrics": {
                "views": 1000,
                "comments": 50,
                "rating": 4.8
            }
        }
        
        result = self.scorer.calculate_total_score(news_data)
        self.assertGreaterEqual(result["stars"], 4, "Высококачественная новость должна иметь >= 4 звезд")
        self.assertEqual(result["urgency"], "ВЫСОКО", "Высококачественная новость должна иметь высокую срочность")
    
    def test_total_score_low_quality(self):
        """Тест общей оценки для низкокачественной новости"""
        news_data = {
            "text": "Обычное сообщение без ключевых слов",
            "title": "Заголовок",
            "date": datetime.now() - timedelta(days=3),
            "author": {
                "name": "Обычный автор",
                "status": "",
                "reviews_count": 0
            },
            "metrics": {
                "views": 5,
                "comments": 0,
                "rating": 0
            }
        }
        
        result = self.scorer.calculate_total_score(news_data)
        self.assertLessEqual(result["stars"], 2, "Низкокачественная новость должна иметь <= 2 звезд")
    
    def test_should_publish_high_score(self):
        """Тест решения о публикации для высокооцененной новости"""
        news_data = {
            "text": "Вопрос по рекрутингу персонала",
            "title": "Рекрутинг",
            "date": datetime.now() - timedelta(hours=2),
            "author": {"name": "Автор", "status": "", "reviews_count": 10},
            "metrics": {"views": 100, "comments": 10, "rating": 4.0}
        }
        
        should_publish = self.scorer.should_publish(news_data, min_stars=2)
        self.assertTrue(should_publish, "Высокооцененная новость должна быть опубликована")
    
    def test_should_publish_low_score(self):
        """Тест решения о публикации для низкооцененной новости"""
        news_data = {
            "text": "Обычное сообщение",
            "title": "Заголовок",
            "date": datetime.now() - timedelta(days=1),
            "author": {"name": "Автор", "status": "", "reviews_count": 0},
            "metrics": {"views": 5, "comments": 0, "rating": 0}
        }
        
        should_publish = self.scorer.should_publish(news_data, min_stars=2)
        self.assertFalse(should_publish, "Низкооцененная новость не должна быть опубликована")
    
    def test_should_publish_old_content(self):
        """Тест решения о публикации для старого контента"""
        news_data = {
            "text": "Вопрос по рекрутингу",
            "title": "Рекрутинг",
            "date": datetime.now() - timedelta(days=10),  # 10 дней назад
            "author": {"name": "Автор", "status": "", "reviews_count": 10},
            "metrics": {"views": 100, "comments": 10, "rating": 4.0}
        }
        
        should_publish = self.scorer.should_publish(news_data, min_stars=2)
        self.assertFalse(should_publish, "Старый контент (более 7 дней) не должен быть опубликован")


class TestHRTimeNewsParser(unittest.TestCase):
    """Тесты для парсера новостей HR Time"""
    
    def setUp(self):
        """Инициализация перед каждым тестом"""
        self.parser = HRTimeNewsParser()
    
    def test_parse_title(self):
        """Тест извлечения заголовка"""
        text = "Заголовок новости\n\nОсновной текст новости"
        parsed = self.parser.parse_news(text)
        
        self.assertEqual(parsed["title"], "Заголовок новости")
    
    def test_parse_author(self):
        """Тест извлечения автора"""
        text = "Автор: Иван Иванов\n\nТекст новости"
        raw_data = {"chat_username": "test_user"}
        parsed = self.parser.parse_news(text, raw_data)
        
        self.assertIn("Иван", parsed["author"]["name"] or "")
    
    def test_parse_metrics(self):
        """Тест извлечения метрик"""
        text = "Текст новости\n\n👁️ 150\n💬 12\n⭐ 4.8"
        parsed = self.parser.parse_news(text)
        
        self.assertGreater(parsed["metrics"]["views"], 0)
        self.assertGreater(parsed["metrics"]["comments"], 0)
        self.assertGreater(parsed["metrics"]["rating"], 0)
    
    def test_parse_category(self):
        """Тест определения категории"""
        text = "Вопрос по рекрутингу персонала"
        parsed = self.parser.parse_news(text)
        
        self.assertEqual(parsed["category"], "Вопросы и ответы")
    
    def test_parse_content_type(self):
        """Тест определения типа контента"""
        text = "Новый запрос на услуги рекрутинга"
        parsed = self.parser.parse_news(text)
        
        self.assertEqual(parsed["type"], "request")


class TestIntegration(unittest.TestCase):
    """Интеграционные тесты для системы оценки и парсинга"""
    
    def setUp(self):
        """Инициализация перед каждым тестом"""
        self.scorer = HRTimeNewsScorer()
        self.parser = HRTimeNewsParser()
    
    def test_full_workflow(self):
        """Тест полного workflow: парсинг -> оценка -> решение о публикации"""
        text = """
        Вопрос по рекрутингу персонала
        
        Нужна помощь с подбором HR-специалистов. Как правильно провести интервью?
        
        👁️ 500
        💬 25
        ⭐ 4.5
        """
        
        raw_data = {
            "message_id": "123",
            "date": datetime.now() - timedelta(hours=2),
            "chat_username": "Иван Иванов ТОП-30"
        }
        
        # Парсим новость
        parsed_news = self.parser.parse_news(text, raw_data)
        
        # Проверяем, что парсинг прошел успешно
        self.assertIsNotNone(parsed_news)
        self.assertIn("title", parsed_news)
        self.assertIn("metrics", parsed_news)
        
        # Оцениваем новость
        score_result = self.scorer.calculate_total_score(parsed_news)
        
        # Проверяем, что оценка прошла успешно
        self.assertIsNotNone(score_result)
        self.assertIn("stars", score_result)
        self.assertIn("urgency", score_result)
        self.assertGreaterEqual(score_result["stars"], 1)
        self.assertLessEqual(score_result["stars"], 5)
        
        # Проверяем решение о публикации
        should_publish = self.scorer.should_publish(parsed_news, min_stars=2)
        self.assertIsInstance(should_publish, bool)


if __name__ == "__main__":
    unittest.main()

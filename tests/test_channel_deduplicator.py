"""
Тесты для механизма предотвращения дубликатов в канале
"""
import unittest
from services.helpers.channel_deduplicator import (
    generate_message_id,
    generate_content_hash,
    is_duplicate,
    mark_as_sent,
    reset,
    get_stats
)


class TestChannelDeduplicator(unittest.TestCase):
    """Тесты для механизма дедупликации"""
    
    def setUp(self):
        """Сброс перед каждым тестом"""
        reset()
    
    def test_generate_message_id_with_email(self):
        """Тест генерации ID для сообщения с email"""
        lead_info = {
            "source": "📧 Email",
            "title": "Тестовое письмо",
            "client_email": "test@example.com",
            "message": "Содержимое"
        }
        
        message_id = generate_message_id(lead_info)
        self.assertIn("📧 Email", message_id)
        self.assertIn("test@example.com", message_id)
        self.assertIn("Тестовое письмо", message_id)
    
    def test_generate_message_id_with_phone(self):
        """Тест генерации ID для сообщения с телефоном"""
        lead_info = {
            "source": "📢 HRTIME",
            "title": "Заказ",
            "client_phone": "+79001234567",
            "message": "Содержимое"
        }
        
        message_id = generate_message_id(lead_info)
        self.assertIn("📢 HRTIME", message_id)
        self.assertIn("+79001234567", message_id)
    
    def test_generate_content_hash(self):
        """Тест генерации хеша содержимого"""
        lead_info = {
            "title": "Тестовое сообщение",
            "message": "Это тестовое содержимое сообщения"
        }
        
        hash1 = generate_content_hash(lead_info)
        hash2 = generate_content_hash(lead_info)
        
        # Одинаковое содержимое должно давать одинаковый хеш
        self.assertEqual(hash1, hash2)
        
        # Разное содержимое должно давать разный хеш
        lead_info2 = {
            "title": "Другое сообщение",
            "message": "Другое содержимое"
        }
        hash3 = generate_content_hash(lead_info2)
        self.assertNotEqual(hash1, hash3)
    
    def test_is_duplicate_new_message(self):
        """Тест проверки нового сообщения (не дубликат)"""
        lead_info = {
            "source": "📧 Email",
            "title": "Новое письмо",
            "client_email": "new@example.com",
            "message": "Новое содержимое"
        }
        
        is_dup, reason = is_duplicate(lead_info)
        self.assertFalse(is_dup)
        self.assertIsNone(reason)
    
    def test_is_duplicate_after_mark_as_sent(self):
        """Тест проверки дубликата после пометки как отправленного"""
        lead_info = {
            "source": "📧 Email",
            "title": "Тестовое письмо",
            "client_email": "test@example.com",
            "message": "Содержимое"
        }
        
        # Первая проверка - не дубликат
        is_dup1, _ = is_duplicate(lead_info)
        self.assertFalse(is_dup1)
        
        # Помечаем как отправленное
        mark_as_sent(lead_info)
        
        # Вторая проверка - дубликат
        is_dup2, reason = is_duplicate(lead_info)
        self.assertTrue(is_dup2)
        self.assertIsNotNone(reason)
    
    def test_is_duplicate_similar_content(self):
        """Тест обнаружения похожего содержимого"""
        lead_info1 = {
            "source": "📧 Email",
            "title": "Вопрос по рекрутингу",
            "message": "Нужна помощь с подбором персонала"
        }
        
        lead_info2 = {
            "source": "📧 Email",
            "title": "Вопрос по рекрутингу",
            "message": "Нужна помощь с подбором персонала"  # То же самое содержимое
        }
        
        # Первое сообщение - не дубликат
        is_dup1, _ = is_duplicate(lead_info1, check_content=True)
        self.assertFalse(is_dup1)
        
        # Помечаем первое как отправленное
        mark_as_sent(lead_info1)
        
        # Второе сообщение с таким же содержимым - дубликат
        # (может быть обнаружен по ID или по хешу)
        is_dup2, reason = is_duplicate(lead_info2, check_content=True)
        self.assertTrue(is_dup2)
        # Причина может быть либо по ID, либо по хешу
        self.assertTrue("уже было отправлено" in reason or "Похожее сообщение" in reason)
    
    def test_different_sources_same_content(self):
        """Тест: разные источники с одинаковым содержимым - не дубликаты"""
        lead_info1 = {
            "source": "📧 Email",
            "title": "Вопрос",
            "message": "Одинаковое содержимое"
        }
        
        lead_info2 = {
            "source": "📢 HRTIME",
            "title": "Вопрос",
            "message": "Одинаковое содержимое"
        }
        
        mark_as_sent(lead_info1)
        
        # Разные источники - не дубликаты
        is_dup, _ = is_duplicate(lead_info2, check_content=True)
        self.assertFalse(is_dup)
    
    def test_get_stats(self):
        """Тест получения статистики"""
        stats = get_stats()
        self.assertIn("total_sent", stats)
        self.assertIn("total_hashes", stats)
        self.assertIn("max_stored", stats)
        
        # Отправляем несколько сообщений
        for i in range(5):
            lead_info = {
                "source": "📧 Email",
                "title": f"Письмо {i}",
                "client_email": f"test{i}@example.com",
                "message": f"Содержимое {i}"
            }
            mark_as_sent(lead_info)
        
        stats_after = get_stats()
        self.assertEqual(stats_after["total_sent"], 5)
        self.assertEqual(stats_after["total_hashes"], 5)


if __name__ == "__main__":
    unittest.main()

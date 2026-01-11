"""
RAG Intent Classifier Service
Сервис для определения необходимости использования RAG поиска на основе намерения пользователя
"""
import logging
from typing import Dict, Optional
import asyncio

log = logging.getLogger(__name__)


class RAGIntentClassifier:
    """Сервис для классификации намерений и определения необходимости RAG"""
    
    def __init__(self):
        self._cache = {}  # Простой кэш для часто используемых запросов
    
    async def _generate_with_llm(self, prompt: str, system_prompt: str = "", max_tokens: int = 150, temperature: float = 0.3) -> Optional[str]:
        """Генерация ответа через LLM"""
        try:
            from services.helpers.llm_helper import deepseek_chat
            
            messages = [{"role": "user", "content": prompt}]
            response = await deepseek_chat(
                messages=messages,
                use_system_message=bool(system_prompt),
                system_content=system_prompt,
                max_tokens=max_tokens,
                temperature=temperature
            )
            return response
        except Exception as e:
            log.warning(f"⚠️ [RAG Intent] Ошибка LLM генерации: {e}")
            return None
    
    async def should_use_rag(self, message: str, context: Optional[Dict] = None) -> Dict[str, any]:
        """
        Определяет, нужно ли использовать RAG поиск для данного сообщения.
        
        Args:
            message: Сообщение пользователя
            context: Дополнительный контекст (история, метаданные)
        
        Returns:
            Dict с полями:
            - use_rag: bool - нужно ли использовать RAG
            - confidence: float - уверенность (0.0-1.0)
            - reason: str - причина решения
            - intent: str - тип намерения (greeting, question, command, etc.)
        """
        message_lower = message.lower().strip()
        
        # Проверяем кэш
        cache_key = message_lower[:50]  # Первые 50 символов как ключ
        if cache_key in self._cache:
            cached_result = self._cache[cache_key]
            log.debug(f"📦 [RAG Intent] Использован кэш для: '{message[:50]}'")
            return cached_result
        
        # Быстрая проверка очевидных случаев (без LLM)
        quick_check = self._quick_check(message_lower)
        if quick_check is not None:
            result = quick_check
            self._cache[cache_key] = result
            return result
        
        # Для неочевидных случаев используем LLM классификацию
        try:
            llm_result = await self._classify_with_llm(message, context)
            if llm_result:
                self._cache[cache_key] = llm_result
                return llm_result
        except Exception as e:
            log.warning(f"⚠️ [RAG Intent] Ошибка LLM классификации: {e}")
        
        # Fallback на простую логику
        fallback_result = self._fallback_classification(message_lower)
        self._cache[cache_key] = fallback_result
        return fallback_result
    
    def _quick_check(self, message_lower: str) -> Optional[Dict]:
        """Быстрая проверка очевидных случаев без LLM"""
        words = message_lower.split()
        
        # Очевидные приветствия - не используем RAG
        obvious_greetings = [
            "привет", "здравствуй", "здравствуйте", "добрый день", "добрый вечер", 
            "доброе утро", "hi", "hello", "hey", "приветик", "салют"
        ]
        
        if any(greeting in message_lower for greeting in obvious_greetings):
            # Но если после приветствия есть вопрос - проверяем дальше
            if len(words) <= 3:
                return {
                    "use_rag": False,
                    "confidence": 0.95,
                    "reason": "Очевидное приветствие без вопроса",
                    "intent": "greeting"
                }
        
        # Очевидные простые ответы - не используем RAG
        simple_responses = [
            "спасибо", "благодарю", "ок", "окей", "понял", "ясно", 
            "хорошо", "ладно", "да", "нет", "пока", "до свидания"
        ]
        
        if any(response in message_lower for response in simple_responses) and len(words) <= 2:
            return {
                "use_rag": False,
                "confidence": 0.9,
                "reason": "Простой ответ без вопроса",
                "intent": "simple_response"
            }
        
        # Очевидные вопросы о знаниях - используем RAG
        knowledge_questions = [
            "что такое", "что это", "расскажи о", "расскажи про", 
            "информация о", "как работает", "как сделать", "методика",
            "кейс", "пример", "опыт", "проект"
        ]
        
        if any(question in message_lower for question in knowledge_questions):
            return {
                "use_rag": True,
                "confidence": 0.95,
                "reason": "Вопрос о знаниях/методиках",
                "intent": "knowledge_question"
            }
        
        # Очевидные вопросы о услугах/ценах - используем RAG
        service_questions = [
            "цена", "стоимость", "сколько стоит", "прайс", "расценки",
            "услуга", "услуги", "что предлагаете", "консультация"
        ]
        
        if any(question in message_lower for question in service_questions):
            return {
                "use_rag": True,
                "confidence": 0.9,
                "reason": "Вопрос об услугах/ценах",
                "intent": "service_question"
            }
        
        return None  # Неочевидный случай - нужна LLM классификация
    
    async def _classify_with_llm(self, message: str, context: Optional[Dict] = None) -> Optional[Dict]:
        """Классификация намерения с помощью LLM"""
        try:
            # Формируем промпт для классификации
            prompt = f"""Проанализируй сообщение пользователя и определи, нужно ли искать информацию в базе знаний (RAG).

Сообщение пользователя: "{message}"

Определи:
1. Тип намерения (greeting, question, command, simple_response, knowledge_question, service_question)
2. Нужно ли использовать RAG поиск (true/false)
3. Уверенность в решении (0.0-1.0)
4. Краткая причина решения

Правила:
- Приветствия без вопросов → use_rag: false
- Простые ответы ("спасибо", "ок") → use_rag: false
- Вопросы о знаниях, услугах, методиках, кейсах → use_rag: true
- Вопросы о ценах, стоимости → use_rag: true
- Общие вопросы без конкретной темы → use_rag: false
- Команды → use_rag: false

Ответь ТОЛЬКО в формате JSON:
{{
    "intent": "тип_намерения",
    "use_rag": true/false,
    "confidence": 0.0-1.0,
    "reason": "краткая причина"
}}"""

            # Используем быстрый LLM для классификации
            response = await self._generate_with_llm(
                prompt=prompt,
                system_prompt="Ты помощник для классификации намерений пользователей. Отвечай только в формате JSON.",
                max_tokens=150,
                temperature=0.3  # Низкая температура для более детерминированных ответов
            )
            
            if not response:
                return None
            
            # Парсим JSON ответ
            import json
            import re
            
            # Извлекаем JSON из ответа
            json_match = re.search(r'\{[^}]+\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                result = json.loads(json_str)
                
                return {
                    "use_rag": bool(result.get("use_rag", False)),
                    "confidence": float(result.get("confidence", 0.5)),
                    "reason": result.get("reason", "LLM классификация"),
                    "intent": result.get("intent", "unknown")
                }
            
            return None
            
        except Exception as e:
            log.warning(f"⚠️ [RAG Intent] Ошибка LLM классификации: {e}")
            return None
    
    def _fallback_classification(self, message_lower: str) -> Dict:
        """Fallback классификация на основе простых правил"""
        words = message_lower.split()
        
        # Вопросы с вопросительными словами и достаточной длиной
        question_words = ["что", "как", "когда", "где", "почему", "кто", "какой", "какая", "какое"]
        has_question_word = any(qw in message_lower for qw in question_words)
        has_question_mark = "?" in message_lower
        
        if (has_question_word or has_question_mark) and len(words) >= 4:
            return {
                "use_rag": True,
                "confidence": 0.6,
                "reason": "Вопрос с вопросительными словами",
                "intent": "question"
            }
        
        # Длинные сообщения (>= 5 слов) - вероятно нужен RAG
        if len(words) >= 5:
            return {
                "use_rag": True,
                "confidence": 0.5,
                "reason": "Длинное сообщение",
                "intent": "long_message"
            }
        
        # Короткие сообщения без вопросов - не используем RAG
        return {
            "use_rag": False,
            "confidence": 0.7,
            "reason": "Короткое сообщение без явного вопроса",
            "intent": "short_message"
        }
    
    def clear_cache(self):
        """Очистка кэша"""
        self._cache.clear()
        log.info("🧹 [RAG Intent] Кэш очищен")


# Singleton instance
_classifier_instance = None


def get_rag_intent_classifier() -> RAGIntentClassifier:
    """Получить singleton экземпляр классификатора"""
    global _classifier_instance
    if _classifier_instance is None:
        _classifier_instance = RAGIntentClassifier()
    return _classifier_instance

"""
Классификатор намерений для распознавания запросов на запись
Использует русскоязычные модели BERT для лучшего понимания намерений пользователя
"""
import os
import logging
from typing import Dict, Tuple, Optional
import re

log = logging.getLogger(__name__)

# Попытка импорта библиотек для классификации
try:
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    import torch
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    log.warning("⚠️ transformers не установлен. Установите: pip install transformers torch")

# Попытка импорта sentence-transformers для легких эмбеддингов
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

# Глобальные переменные
_intent_model = None
_intent_tokenizer = None
_embedding_model_light = None

# Легкая русскоязычная модель для эмбеддингов (быстрее и меньше)
LIGHT_EMBEDDING_MODEL = "cointegrated/rubert-tiny2"  # Очень легкая модель для русского
# Альтернативы:
# "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"  # Мультиязычная, легкая
# "intfloat/multilingual-e5-small"  # Мультиязычная, средняя

def get_light_embedding_model():
    """Получить легкую модель для эмбеддингов"""
    global _embedding_model_light
    
    if not SENTENCE_TRANSFORMERS_AVAILABLE:
        return None
    
    if _embedding_model_light is not None:
        return _embedding_model_light
    
    try:
        log.info(f"🔄 Загрузка легкой модели для эмбеддингов: {LIGHT_EMBEDDING_MODEL}...")
        _embedding_model_light = SentenceTransformer(LIGHT_EMBEDDING_MODEL)
        log.info("✅ Легкая модель для эмбеддингов загружена")
        return _embedding_model_light
    except Exception as e:
        log.error(f"❌ Ошибка загрузки легкой модели: {e}")
        return None

def classify_intent_with_embeddings(text: str, services: list, masters: list) -> Tuple[float, Dict]:
    """
    Классификация намерения с использованием эмбеддингов
    Возвращает (confidence_score, details)
    """
    if not SENTENCE_TRANSFORMERS_AVAILABLE:
        return 0.0, {"method": "fallback", "reason": "sentence-transformers недоступен"}
    
    model = get_light_embedding_model()
    if not model:
        return 0.0, {"method": "fallback", "reason": "модель не загружена"}
    
    try:
        # Генерируем эмбеддинг для текста пользователя
        text_embedding = model.encode(text, normalize_embeddings=True)
        
        # Создаем эталонные эмбеддинги для запросов на запись
        booking_examples = [
            "хочу записаться",
            "записаться на услугу",
            "нужна запись",
            "когда можно записаться",
            "забронировать время",
            "хочу записаться к мастеру",
            "запись на завтра",
            "записаться на стрижку",
            "нужна запись на маникюр",
            "когда свободно",
            "можно записаться",
            "хочу записаться на бритье",
            "запись на сегодня",
            "записаться на завтра в 8 утра"
        ]
        
        booking_embeddings = model.encode(booking_examples, normalize_embeddings=True)
        
        # Вычисляем косинусное сходство с эталонными запросами
        import numpy as np
        similarities = np.dot(booking_embeddings, text_embedding)
        max_similarity = float(np.max(similarities))
        
        # Проверяем сходство с услугами
        if services:
            service_titles = [s.get("title", "") for s in services[:20]]  # Берем первые 20
            service_embeddings = model.encode(service_titles, normalize_embeddings=True)
            service_similarities = np.dot(service_embeddings, text_embedding)
            max_service_similarity = float(np.max(service_similarities))
        else:
            max_service_similarity = 0.0
        
        # Комбинируем результаты
        confidence = max(max_similarity, max_service_similarity * 0.8)
        
        details = {
            "method": "embedding",
            "booking_similarity": max_similarity,
            "service_similarity": max_service_similarity,
            "confidence": confidence
        }
        
        return confidence, details
        
    except Exception as e:
        log.error(f"❌ Ошибка классификации с эмбеддингами: {e}")
        return 0.0, {"method": "error", "error": str(e)}

def classify_intent_hybrid(text: str, services: list, masters: list) -> Tuple[float, Dict]:
    """
    Гибридная классификация намерения:
    1. Использует эмбеддинги для семантического понимания
    2. Использует ключевые слова как fallback
    3. Учитывает контекст (услуги, мастера, время)
    """
    text_lower = text.lower().strip()
    
    # 1. Попытка классификации с эмбеддингами
    embedding_score, embedding_details = classify_intent_with_embeddings(text, services, masters)
    
    # 2. Проверка ключевых слов (fallback)
    keyword_score = 0.0
    booking_keywords = [
        "запись", "записаться", "записать", "забронировать",
        "когда можно", "свободное время", "расписание",
        "записаться на", "хочу записаться", "нужна запись"
    ]
    
    for keyword in booking_keywords:
        if keyword in text_lower:
            keyword_score = 0.7
            break
    
    # 3. Проверка упоминания услуг
    service_score = 0.0
    if services:
        for service in services[:20]:
            service_title = service.get("title", "").lower()
            if service_title and service_title in text_lower:
                service_score = 0.6
                break
    
    # 4. Проверка временных маркеров
    time_score = 0.0
    time_markers = [
        "завтра", "сегодня", "послезавтра", "в ", "на ", "часов", ":",
        "утра", "утром", "вечера", "вечером", "дня", "днем"
    ]
    time_markers_found = sum(1 for marker in time_markers if marker in text_lower)
    if time_markers_found >= 2:
        time_score = 0.8
    elif time_markers_found >= 1:
        time_score = 0.5
    
    # 5. Комбинируем все оценки
    final_score = max(
        embedding_score * 0.5,  # Эмбеддинги - 50% веса
        keyword_score * 0.3,    # Ключевые слова - 30%
        service_score * 0.1,    # Услуги - 10%
        time_score * 0.1        # Время - 10%
    )
    
    # Если есть несколько признаков, увеличиваем score
    indicators_count = sum([
        embedding_score > 0.5,
        keyword_score > 0,
        service_score > 0,
        time_score > 0
    ])
    
    if indicators_count >= 2:
        final_score = min(1.0, final_score * 1.2)
    
    details = {
        "method": "hybrid",
        "embedding": embedding_details,
        "keyword_score": keyword_score,
        "service_score": service_score,
        "time_score": time_score,
        "indicators_count": indicators_count,
        "final_score": final_score
    }
    
    return final_score, details

def classify_intent_with_llm(text: str, openrouter_api_key: str = None, openrouter_url: str = None) -> Tuple[float, Dict]:
    """
    Классификация намерения с использованием LLM (multi-agent подход)
    Использует OpenRouter API для понимания намерения пользователя
    """
    if not openrouter_api_key:
        return 0.0, {"method": "llm", "reason": "OpenRouter API key не указан"}
    
    try:
        import requests
        
        # Промпт для классификации намерения
        classification_prompt = f"""Ты помощник салона красоты. Определи, является ли следующее сообщение запросом на запись к мастеру.

Сообщение пользователя: "{text}"

Ответь ТОЛЬКО числом от 0.0 до 1.0, где:
- 1.0 = точно запрос на запись (например: "хочу записаться", "запись на завтра", "можно записаться")
- 0.5-0.9 = вероятно запрос на запись (например: "когда свободно", "нужна стрижка")
- 0.0-0.4 = не запрос на запись (например: "привет", "как дела", "спасибо")

Учитывай опечатки и разные варианты написания. Число:"""
        
        headers = {
            "Authorization": f"Bearer {openrouter_api_key}",
            "Content-Type": "application/json",
        }
        
        data = {
            "model": "x-ai/grok-4.1-fast:free",  # Легкая модель для быстрой классификации
            "messages": [{"role": "user", "content": classification_prompt}],
            "temperature": 0.1,  # Низкая температура для более детерминированных ответов
            "max_tokens": 10
        }
        
        response = requests.post(
            openrouter_url or "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=5
        )
        
        if response.status_code == 200:
            result = response.json()
            answer = result.get("choices", [{}])[0].get("message", {}).get("content", "0.0").strip()
            
            # Парсим число из ответа
            import re
            numbers = re.findall(r'\d+\.?\d*', answer)
            if numbers:
                score = float(numbers[0])
                score = max(0.0, min(1.0, score))  # Ограничиваем от 0 до 1
                return score, {"method": "llm", "score": score, "raw_answer": answer}
        
        return 0.0, {"method": "llm", "reason": f"Ошибка API: {response.status_code}"}
        
    except Exception as e:
        log.error(f"❌ Ошибка LLM классификации: {e}")
        return 0.0, {"method": "llm", "error": str(e)}

def is_booking_intent(text: str, services: list = None, masters: list = None, threshold: float = 0.5, 
                       use_llm: bool = False, openrouter_api_key: str = None, openrouter_url: str = None) -> Tuple[bool, Dict]:
    """
    Определяет, является ли текст запросом на запись
    Использует гибридный подход с эмбеддингами и опционально LLM
    
    Args:
        text: Текст сообщения пользователя
        services: Список услуг (опционально)
        masters: Список мастеров (опционально)
        threshold: Порог уверенности (по умолчанию 0.5)
        use_llm: Использовать ли LLM для классификации (multi-agent подход)
        openrouter_api_key: API ключ OpenRouter (если use_llm=True)
        openrouter_url: URL OpenRouter API (если use_llm=True)
    
    Returns:
        (is_booking, details) - является ли запросом на запись и детали классификации
    """
    if not services:
        services = []
    if not masters:
        masters = []
    
    # Если включен LLM, используем его как основной метод
    if use_llm and openrouter_api_key:
        llm_score, llm_details = classify_intent_with_llm(text, openrouter_api_key, openrouter_url)
        
        # Комбинируем с гибридным методом
        hybrid_score, hybrid_details = classify_intent_hybrid(text, services, masters)
        
        # Взвешенное среднее: LLM 60%, гибридный 40%
        final_score = llm_score * 0.6 + hybrid_score * 0.4
        
        details = {
            "method": "llm+hybrid",
            "llm_score": llm_score,
            "hybrid_score": hybrid_score,
            "final_score": final_score,
            "llm_details": llm_details,
            "hybrid_details": hybrid_details
        }
    else:
        # Используем только гибридную классификацию
        final_score, details = classify_intent_hybrid(text, services, masters)
        details["final_score"] = final_score
    
    is_booking = final_score >= threshold
    
    log.info(f"🎯 INTENT CLASSIFICATION: '{text[:50]}...' -> score={final_score:.3f}, is_booking={is_booking}, method={details.get('method', 'unknown')}")
    
    return is_booking, details

# Экспорт для использования в других модулях
__all__ = [
    'is_booking_intent',
    'classify_intent_hybrid',
    'classify_intent_with_embeddings',
    'get_light_embedding_model',
    'TRANSFORMERS_AVAILABLE',
    'SENTENCE_TRANSFORMERS_AVAILABLE'
]


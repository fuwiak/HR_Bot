"""
Lead Processor Module
Обработка лидов: валидация, классификация, генерация КП и гипотез
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime

log = logging.getLogger()

# Импорты для LLM и RAG
try:
    from llm_helper import generate_with_fallback
    from qdrant_helper import search_service
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False
    log.warning("⚠️ LLM или RAG модули недоступны")

# ===================== PROMPTS =====================

LEAD_VALIDATION_PROMPT = """
Ты AI-ассистент для консалтинговой практики. Твоя задача - оценить перспективность лида (запроса клиента).

Критерии оценки (каждый 0-1, итоговый score 0-1):
1. Четкость ТЗ (0.3) - есть ли конкретная задача, проблема, требования
2. Наличие бюджета/сроков (0.3) - указан ли бюджет или примерные сроки
3. Релевантность экспертизе (0.4) - подходит ли запрос под наши услуги (HR-консалтинг, подбор персонала, автоматизация, бизнес-анализ)

Ответь ТОЛЬКО в формате JSON:
{
    "score": 0.0-1.0,
    "status": "warm" | "cold" | "rejected",
    "reason": "краткое обоснование",
    "criteria": {
        "clarity": 0.0-1.0,
        "budget": 0.0-1.0,
        "relevance": 0.0-1.0
    }
}

Запрос лида: {{request}}
"""

CLASSIFICATION_PROMPT = """
Ты AI-ассистент для консалтинговой практики. Классифицируй запрос клиента по категориям.

Категории:
- "подбор" - подбор персонала, рекрутинг
- "автоматизация" - автоматизация HR-процессов, внедрение систем
- "бизнес-анализ" - анализ бизнес-процессов, консалтинг
- "другое" - не подходит под основные категории

Ответь ТОЛЬКО в формате JSON:
{
    "category": "подбор" | "автоматизация" | "бизнес-анализ" | "другое",
    "confidence": 0.0-1.0,
    "keywords": ["ключевое слово 1", "ключевое слово 2"]
}

Запрос: {{request}}
"""

PROPOSAL_GENERATION_PROMPT = """
Ты AI-ассистент консультанта Анастасии Новосёловой. Сгенерируй коммерческое предложение (КП) на основе запроса клиента и релевантной информации из базы знаний.

СТИЛЬ:
- Деловой, но дружелюбный
- Показывай понимание проблемы клиента
- Используй списки и структурированный формат
- Предлагай конкретные этапы работ
- Указывай предварительную оценку сроков и стоимости (если возможно)

СТРУКТУРА КП:
1. Приветствие и благодарность за обращение
2. Краткий анализ задачи клиента
3. Предлагаемое решение (с опорой на базу знаний)
4. Этапы работ
5. Предварительные сроки
6. Предварительная стоимость (или запрос на уточнение)
7. Призыв к действию

ВАЖНО: Используй ТОЛЬКО информацию из базы знаний. Не выдумывай кейсы или методики.

Запрос клиента: {{request}}

Релевантная информация из базы знаний:
{{rag_context}}
"""

HYPOTHESIS_GENERATION_PROMPT = """
Ты AI-ассистент консультанта. На основе запроса клиента и похожих кейсов из базы знаний сформируй консалтинговые гипотезы.

Формат:
1. Основная гипотеза решения
2. Аналогичные кейсы из практики (если есть)
3. Рекомендуемые методики (если есть)
4. Риски и ограничения

Запрос клиента: {{request}}

Похожие кейсы из базы знаний:
{{rag_context}}
"""

# ===================== VALIDATION =====================

async def validate_lead(lead_request: str) -> Dict:
    """
    Валидация лида с оценкой перспективности
    
    Args:
        lead_request: Текст запроса от лида
    
    Returns:
        Словарь с результатами валидации
    """
    if not LLM_AVAILABLE:
        return {
            "score": 0.5,
            "status": "unknown",
            "reason": "LLM недоступен"
        }
    
    try:
        prompt = LEAD_VALIDATION_PROMPT.replace("{{request}}", lead_request)
        
        messages = [{"role": "user", "content": prompt}]
        response = await generate_with_fallback(messages, use_system_message=True, system_content="Ты помощник для оценки лидов. Отвечай только в формате JSON.")
        
        # Парсинг JSON ответа
        import json
        # Попытка извлечь JSON из ответа
        if "{" in response and "}" in response:
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            json_str = response[json_start:json_end]
            result = json.loads(json_str)
        else:
            # Fallback при ошибке парсинга
            result = {
                "score": 0.5,
                "status": "warm",
                "reason": "Ошибка парсинга ответа LLM",
                "criteria": {
                    "clarity": 0.5,
                    "budget": 0.5,
                    "relevance": 0.5
                }
            }
        
        log.info(f"✅ Лид валидирован: score={result.get('score')}, status={result.get('status')}")
        return result
    except Exception as e:
        log.error(f"❌ Ошибка валидации лида: {e}")
        import traceback
        log.error(f"❌ Traceback: {traceback.format_exc()}")
        return {
            "score": 0.5,
            "status": "unknown",
            "reason": f"Ошибка: {str(e)}"
        }

async def classify_request(request: str) -> Dict:
    """
    Классификация запроса по категориям экспертизы
    
    Args:
        request: Текст запроса
    
    Returns:
        Словарь с категорией и уверенностью
    """
    if not LLM_AVAILABLE:
        return {
            "category": "другое",
            "confidence": 0.0,
            "keywords": []
        }
    
    try:
        prompt = CLASSIFICATION_PROMPT.replace("{{request}}", request)
        
        messages = [{"role": "user", "content": prompt}]
        response = await generate_with_fallback(messages, use_system_message=True, system_content="Ты помощник для классификации запросов. Отвечай только в формате JSON.")
        
        # Парсинг JSON ответа
        import json
        if "{" in response and "}" in response:
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            json_str = response[json_start:json_end]
            result = json.loads(json_str)
        else:
            result = {
                "category": "другое",
                "confidence": 0.0,
                "keywords": []
            }
        
        log.info(f"✅ Запрос классифицирован: {result.get('category')} (confidence: {result.get('confidence')})")
        return result
    except Exception as e:
        log.error(f"❌ Ошибка классификации запроса: {e}")
        return {
            "category": "другое",
            "confidence": 0.0,
            "keywords": []
        }

# ===================== PROPOSAL GENERATION =====================

async def generate_proposal(lead_request: str, lead_contact: Dict, rag_results: Optional[List[Dict]] = None) -> str:
    """
    Генерация коммерческого предложения с использованием RAG
    
    Args:
        lead_request: Текст запроса от лида
        lead_contact: Контактная информация лида
        rag_results: Результаты поиска в RAG базе (опционально)
    
    Returns:
        Текст коммерческого предложения
    """
    if not LLM_AVAILABLE:
        return "Извините, сервис временно недоступен."
    
    try:
        # Если RAG результаты не предоставлены, ищем их
        if rag_results is None:
            rag_results = search_service(lead_request, limit=5)
        
        # Формируем контекст из RAG результатов
        rag_context = ""
        if rag_results:
            rag_context = "Релевантная информация из базы знаний:\n\n"
            for i, result in enumerate(rag_results, 1):
                title = result.get("title", "Документ")
                text = result.get("text", result.get("content", ""))[:500]  # Первые 500 символов
                score = result.get("score", 0)
                rag_context += f"{i}. {title} (релевантность: {score:.2f})\n{text}\n\n"
        else:
            rag_context = "В базе знаний не найдено релевантной информации для данного запроса."
        
        prompt = PROPOSAL_GENERATION_PROMPT.replace("{{request}}", lead_request).replace("{{rag_context}}", rag_context)
        
        messages = [{"role": "user", "content": prompt}]
        proposal = await generate_with_fallback(
            messages,
            use_system_message=True,
            system_content="Ты помощник консультанта для генерации коммерческих предложений. Пиши деловым, но дружелюбным стилем.",
            max_tokens=3000,
            temperature=0.7
        )
        
        log.info(f"✅ КП сгенерировано (длина: {len(proposal)} символов)")
        return proposal
    except Exception as e:
        log.error(f"❌ Ошибка генерации КП: {e}")
        import traceback
        log.error(f"❌ Traceback: {traceback.format_exc()}")
        return f"Извините, произошла ошибка при генерации коммерческого предложения. Ошибка: {str(e)}"

async def generate_hypothesis(lead_request: str, rag_results: Optional[List[Dict]] = None) -> str:
    """
    Генерация консалтинговых гипотез на основе запроса и базы знаний
    
    Args:
        lead_request: Текст запроса
        rag_results: Результаты поиска в RAG базе
    
    Returns:
        Текст с гипотезами
    """
    if not LLM_AVAILABLE:
        return "Извините, сервис временно недоступен."
    
    try:
        # Если RAG результаты не предоставлены, ищем их
        if rag_results is None:
            rag_results = search_service(lead_request, limit=5)
        
        # Формируем контекст из похожих кейсов
        rag_context = ""
        if rag_results:
            rag_context = "Похожие кейсы и методики:\n\n"
            for i, result in enumerate(rag_results, 1):
                title = result.get("title", "Кейс")
                text = result.get("text", result.get("content", ""))[:500]
                category = result.get("category", "кейс")
                rag_context += f"{i}. [{category}] {title}\n{text}\n\n"
        else:
            rag_context = "В базе знаний не найдено похожих кейсов."
        
        prompt = HYPOTHESIS_GENERATION_PROMPT.replace("{{request}}", lead_request).replace("{{rag_context}}", rag_context)
        
        messages = [{"role": "user", "content": prompt}]
        hypothesis = await generate_with_fallback(
            messages,
            use_system_message=True,
            system_content="Ты помощник консультанта для генерации гипотез. Используй опыт из базы знаний.",
            max_tokens=2000,
            temperature=0.7
        )
        
        log.info(f"✅ Гипотеза сгенерирована (длина: {len(hypothesis)} символов)")
        return hypothesis
    except Exception as e:
        log.error(f"❌ Ошибка генерации гипотезы: {e}")
        return f"Извините, произошла ошибка при генерации гипотез. Ошибка: {str(e)}"
















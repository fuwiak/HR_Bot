"""
Сервис для работы с LLM (OpenRouter)
"""
import logging

log = logging.getLogger(__name__)


async def openrouter_chat(messages, use_system_message=False, system_content=""):
    """
    Асинхронная отправка запроса в LLM через новый модуль llm_helper
    Использует DeepSeek (primary) с fallback на GigaChat
    """
    try:
        from services.helpers.llm_helper import generate_with_fallback
        return await generate_with_fallback(
            messages=messages,
            use_system_message=use_system_message,
            system_content=system_content,
            max_tokens=2000,
            temperature=0.7
        )
    except ImportError:
        log.warning("⚠️ llm_helper недоступен, используем старый метод")
        # Fallback на старый метод если новый модуль недоступен
        return "Извините, сервис временно недоступен."

"""
Универсальный LLM-клиент с поддержкой OpenRouter (основной провайдер).
Поддерживает быструю замену endpoint через ENV переменные.
"""

import os
import httpx
import time
import asyncio
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """Ответ от LLM API"""
    content: str
    provider: str
    model: str
    confidence: float = 1.0
    tokens_used: Optional[int] = None
    error: Optional[str] = None


class LLMClient:
    """Универсальный клиент для работы с LLM API"""
    
    def __init__(
        self,
        primary_provider: str = "openrouter",
        primary_model: str = "deepseek/deepseek-chat",
        fallback_chain: Optional[List[Dict[str, str]]] = None,
        confidence_threshold: float = 0.7,
        timeout: int = 30
    ):
        self.primary_provider = primary_provider
        self.primary_model = primary_model
        self.confidence_threshold = confidence_threshold
        self.timeout = timeout
        
        # Цепочка fallback моделей (только OpenRouter)
        if fallback_chain is None:
            # Дефолтная цепочка fallback (только OpenRouter модели)
            self.fallback_chain = [
                {"provider": "openrouter", "model": "deepseek/deepseek-chat"},
                {"provider": "openrouter", "model": "meta-llama/llama-3.3-70b-instruct"}
            ]
        else:
            self.fallback_chain = fallback_chain
        
        # Загружаем конфигурацию из ENV (только OpenRouter)
        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        self.openrouter_api_key = openrouter_key.strip() if openrouter_key else None
        
        openrouter_url = os.getenv("OPENROUTER_API_URL", "https://openrouter.ai/api/v1/chat/completions")
        self.openrouter_api_url = openrouter_url.strip()
        
        # Для локального qroq/ollama можно установить через ENV
        # OpenRouter используется как основной провайдер
        
        # HTTP клиент создается лениво для thread-safety
        self._client: Optional[httpx.AsyncClient] = None
        self._client_lock = None
    
    def _get_client(self) -> httpx.AsyncClient:
        """Получает или создает HTTP клиент (thread-safe)"""
        if self._client_lock is None:
            import threading
            self._client_lock = threading.Lock()
        
        # Проверяем, нужно ли пересоздать клиент
        if self._client is None:
            with self._client_lock:
                # Двойная проверка после получения блокировки
                if self._client is None:
                    # Создаем новый клиент
                    self._client = httpx.AsyncClient(timeout=self.timeout)
                    logger.debug("Создан новый HTTP клиент")
        elif self._client.is_closed:
            # Клиент закрыт - пересоздаем
            with self._client_lock:
                # Двойная проверка
                if self._client.is_closed:
                    self._client = httpx.AsyncClient(timeout=self.timeout)
                    logger.debug("HTTP клиент пересоздан (был закрыт)")
        
        return self._client
    
    async def _ensure_client(self) -> httpx.AsyncClient:
        """Обеспечивает наличие рабочего HTTP клиента (async-safe)"""
        client = self._get_client()
        
        # Проверяем, не закрыт ли клиент
        if client.is_closed:
            logger.warning("HTTP клиент закрыт, пересоздаю...")
            if self._client_lock is not None:
                with self._client_lock:
                    if self._client is not None and self._client.is_closed:
                        try:
                            await self._client.aclose()
                        except:
                            pass
                        self._client = None
            client = self._get_client()
        
        return client
    
    async def _call_api(
        self,
        provider: str,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> LLMResponse:
        """Выполняет запрос к LLM API"""
        
        if provider == "openrouter":
            api_key = self.openrouter_api_key
            api_url = self.openrouter_api_url
            # Очищаем API ключ от возможных пробелов/переносов
            api_key = api_key.strip() if api_key else None
            api_url = api_url.strip()
            app_url = os.getenv("APP_URL", "https://hr2137-bot.railway.app").strip()
            headers = {
                "Authorization": f"Bearer {api_key}",
                "HTTP-Referer": app_url,
                "X-Title": "HR2137 Bot RAG",
                "Content-Type": "application/json"
            }
        else:
            raise ValueError(f"Unknown provider: {provider}")
        
        if not api_key:
            raise ValueError(f"{provider.upper()}_API_KEY not set in environment")
        
        # Валидация URL (проверяем, что нет непечатаемых символов)
        if '\n' in api_url or '\r' in api_url:
            logger.error(f"Invalid URL contains newline characters: {repr(api_url)}")
            api_url = api_url.replace('\n', '').replace('\r', '').strip()
            logger.warning(f"Cleaned URL: {api_url}")
        
        # Очищаем messages от возможных проблем с форматированием
        cleaned_messages = []
        for msg in messages:
            cleaned_msg = {
                "role": msg.get("role", "user").strip(),
                "content": msg.get("content", "").strip()
            }
            # Удаляем пустые сообщения
            if cleaned_msg["content"]:
                cleaned_messages.append(cleaned_msg)
        
        if not cleaned_messages:
            raise ValueError("No valid messages to send")
        
        payload = {
            "model": model.strip() if isinstance(model, str) else model,
            "messages": cleaned_messages,
            "temperature": float(temperature),
            "max_tokens": int(max_tokens)
        }
        
        try:
            logger.info(f"🔵 [LLM API] Вызов {provider} API с моделью {model}")
            logger.info(f"🔵 [LLM API] URL: {api_url}")
            logger.info(f"🔵 [LLM API] Параметры: temperature={temperature}, max_tokens={max_tokens}")
            
            # Логируем промпты (первые 500 символов для читаемости)
            for idx, msg in enumerate(cleaned_messages):
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                preview = content[:500] + "..." if len(content) > 500 else content
                logger.info(f"🔵 [LLM API] Сообщение {idx+1} ({role}): {preview}")
            
            start_time = time.time()
            
            # Обеспечиваем наличие рабочего клиента
            client = await self._ensure_client()
            
            try:
                response = await client.post(
                    api_url,
                    headers=headers,
                    json=payload
                )
            except (RuntimeError, httpx.TransportError, httpx.RequestError) as e:
                # Если клиент закрыт или произошла ошибка транспорта - пересоздаем
                error_str = str(e).lower()
                if "closed" in error_str or "client has been closed" in error_str:
                    logger.warning(f"HTTP клиент закрыт ({str(e)}), пересоздаю и повторяю запрос...")
                    # Закрываем старый клиент
                    if self._client_lock is not None:
                        with self._client_lock:
                            if self._client is not None:
                                try:
                                    await self._client.aclose()
                                except:
                                    pass
                            self._client = None
                    # Создаем новый клиент и повторяем запрос
                    client = await self._ensure_client()
                    response = await client.post(
                        api_url,
                        headers=headers,
                        json=payload
                    )
                else:
                    raise
            
            elapsed_time = time.time() - start_time
            logger.info(f"✅ [LLM API] Ответ получен за {elapsed_time:.2f}s")
            
            response.raise_for_status()
            data = response.json()
            
            content = data["choices"][0]["message"]["content"]
            tokens_used = data.get("usage", {}).get("total_tokens")
            
            # Логируем ответ LLM (первые 500 символов)
            content_preview = content[:500] + "..." if len(content) > 500 else content
            logger.info(f"✅ [LLM API] Ответ от {provider}/{model}: {content_preview}")
            logger.info(f"✅ [LLM API] Использовано токенов: {tokens_used}")
            
            # Простая оценка уверенности (можно улучшить)
            confidence = 1.0 if len(content) > 50 else 0.5
            logger.info(f"✅ [LLM API] Уверенность: {confidence:.2f}")
            
            return LLMResponse(
                content=content,
                provider=provider,
                model=model,
                confidence=confidence,
                tokens_used=tokens_used
            )
            
        except httpx.TimeoutException:
            logger.error(f"❌ [LLM API] Таймаут при вызове {provider} API (модель: {model})")
            return LLMResponse(
                content="",
                provider=provider,
                model=model,
                confidence=0.0,
                error="Timeout"
            )
        except httpx.HTTPStatusError as e:
            error_detail = ""
            try:
                error_data = e.response.json()
                error_detail = f": {error_data}"
            except:
                try:
                    error_detail = f": {e.response.text[:200]}"
                except:
                    pass
            
            logger.error(f"❌ [LLM API] Ошибка {provider} API: HTTP {e.response.status_code}{error_detail}")
            return LLMResponse(
                content="",
                provider=provider,
                model=model,
                confidence=0.0,
                error=f"HTTP {e.response.status_code}{error_detail}"
            )
        except Exception as e:
            logger.error(f"❌ [LLM API] Исключение при вызове {provider} API: {str(e)}")
            import traceback
            logger.error(f"❌ [LLM API] Traceback: {traceback.format_exc()}")
            return LLMResponse(
                content="",
                provider=provider,
                model=model,
                confidence=0.0,
                error=str(e)
            )
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        use_fallback: bool = True
    ) -> LLMResponse:
        """
        Генерирует ответ используя основной провайдер, при необходимости fallback.
        
        Args:
            prompt: Пользовательский промпт
            system_prompt: Системный промпт (опционально)
            model: Модель (если не указано, используется дефолтная)
            temperature: Температура генерации
            max_tokens: Максимальное количество токенов
            use_fallback: Использовать fallback при ошибке/низкой уверенности
        
        Returns:
            LLMResponse с ответом или ошибкой
        """
        # Очищаем промпты от возможных проблем (но сохраняем переносы строк в content)
        cleaned_prompt = prompt.strip() if prompt else ""
        cleaned_system_prompt = system_prompt.strip() if system_prompt else None
        
        if not cleaned_prompt:
            raise ValueError("Prompt cannot be empty")
        
        messages = []
        if cleaned_system_prompt:
            messages.append({"role": "system", "content": cleaned_system_prompt})
        messages.append({"role": "user", "content": cleaned_prompt})
        
        # Определяем модель для основного провайдера
        primary_model = model or self.primary_model
        
        # Пытаемся вызвать основной провайдер
        logger.info(f"🚀 [LLM GENERATE] Начало генерации ответа")
        logger.info(f"🚀 [LLM GENERATE] Основной провайдер: {self.primary_provider}, модель: {primary_model}")
        logger.info(f"🚀 [LLM GENERATE] Параметры: temperature={temperature}, max_tokens={max_tokens}")
        logger.info(f"🚀 [LLM GENERATE] Промпт (первые 300 символов): {cleaned_prompt[:300]}...")
        if cleaned_system_prompt:
            logger.info(f"🚀 [LLM GENERATE] System промпт (первые 300 символов): {cleaned_system_prompt[:300]}...")
        
        response = await self._call_api(
            provider=self.primary_provider,
            model=primary_model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        # Если успешно и уверенность достаточна - возвращаем
        if response.error is None and response.confidence >= self.confidence_threshold:
            logger.info(f"✅ [LLM GENERATE] Основной провайдер успешно вернул ответ (уверенность: {response.confidence:.2f})")
            logger.info(f"✅ [LLM GENERATE] Финальный ответ (первые 500 символов): {response.content[:500]}...")
            return response
        
        # Если нужен fallback - пробуем цепочку fallback моделей
        if use_fallback and self.fallback_chain:
            logger.warning(
                f"⚠️ [LLM GENERATE] Основная модель {primary_model} не прошла проверку "
                f"(ошибка: {response.error}, уверенность: {response.confidence:.2f}). "
                f"Пробую fallback цепочку из {len(self.fallback_chain)} моделей..."
            )
            
            # Пробуем каждую модель в цепочке fallback
            for idx, fallback_config in enumerate(self.fallback_chain, 1):
                fallback_provider = fallback_config.get("provider", "openrouter")
                fallback_model = fallback_config.get("model")
                
                if not fallback_model:
                    logger.warning(f"Fallback {idx} skipped: model not specified")
                    continue
                
                logger.info(f"🔄 [LLM GENERATE] Пробую fallback {idx}/{len(self.fallback_chain)}: {fallback_provider}/{fallback_model}")
                
                fallback_response = await self._call_api(
                    provider=fallback_provider,
                    model=fallback_model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                
                # Если успешно - возвращаем ответ
                if fallback_response.error is None:
                    logger.info(f"✅ [LLM GENERATE] Fallback {idx} ({fallback_provider}/{fallback_model}) успешно вернул ответ")
                    logger.info(f"✅ [LLM GENERATE] Финальный ответ (первые 500 символов): {fallback_response.content[:500]}...")
                    return fallback_response
                else:
                    logger.warning(
                        f"❌ [LLM GENERATE] Fallback {idx} ({fallback_provider}/{fallback_model}) не сработал: "
                        f"{fallback_response.error}"
                    )
            
            logger.error("❌ [LLM GENERATE] Все модели в fallback цепочке не сработали")
        
        # Если все модели не сработали, возвращаем последний ответ (или primary)
        logger.error(f"❌ [LLM GENERATE] Все провайдеры и fallback модели не сработали. Возвращаю последний ответ (ошибка: {response.error})")
        return response
    
    def _get_default_model(self, provider: str) -> str:
        """Возвращает дефолтную модель для провайдера (deprecated, используется primary_model)"""
        defaults = {
            "openrouter": "deepseek/deepseek-chat"
        }
        return defaults.get(provider, self.primary_model)
    
    async def close(self):
        """Закрывает HTTP клиент"""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None


"""
Клиент AnythingLLM Developer API для чата с workspace.
Используется когда USE_ANYTHINGLLM_RAG=true; конфигурация LLM/эмбеддингов/векторной БД в AnythingLLM.
"""
import os
import logging
import asyncio
from typing import Optional, List, Dict, Any, Tuple

import aiohttp

log = logging.getLogger(__name__)

# Переменные окружения
def _base_url() -> str:
    return (os.getenv("ANYTHINGLLM_BASE_URL") or "").strip().rstrip("/")

def _api_key() -> Optional[str]:
    key = os.getenv("ANYTHINGLLM_API_KEY")
    return key.strip() if key else None

def _workspace_slug() -> str:
    return (os.getenv("ANYTHINGLLM_WORKSPACE_SLUG") or "hr-bot").strip()


def _email_workspace_slug() -> Optional[str]:
    """Slug отдельной рабочей области для ответов на email (опционально)."""
    slug = (os.getenv("ANYTHINGLLM_EMAIL_WORKSPACE_SLUG") or "").strip()
    return slug if slug else None


def use_anythingllm_rag() -> bool:
    return os.getenv("USE_ANYTHINGLLM_RAG", "").strip().lower() in ("true", "1", "yes")

def is_configured() -> bool:
    return bool(_base_url() and _api_key() and _workspace_slug())


# Таймаут и повтор
DEFAULT_TIMEOUT = 60
RETRY_COUNT = 1


async def chat(
    workspace_slug: str,
    message: str,
    history: Optional[List[Dict[str, str]]] = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> Tuple[Optional[str], List[Dict[str, Any]]]:
    """
    Отправить сообщение в AnythingLLM workspace и получить ответ.

    Args:
        workspace_slug: slug workspace (например hr-bot).
        message: текст сообщения пользователя.
        history: опциональная история в формате [{"role": "user"|"assistant", "content": "..."}].
        timeout: таймаут запроса в секундах.

    Returns:
        (response_text, sources) — ответ или (None, []) при ошибке.
        sources — список источников из RAG, если API их возвращает.
    """
    base = _base_url()
    api_key = _api_key()
    if not base or not api_key:
        log.warning("AnythingLLM: не заданы ANYTHINGLLM_BASE_URL или ANYTHINGLLM_API_KEY")
        return None, []

    url = f"{base}/api/v1/workspace/{workspace_slug}/chat"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    body: Dict[str, Any] = {"message": message}
    if history:
        body["history"] = history

    last_error: Optional[Exception] = None
    for attempt in range(RETRY_COUNT + 1):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=body,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=timeout),
                ) as response:
                    if response.status >= 400:
                        text = await response.text()
                        log.warning(
                            "AnythingLLM API error %s: %s",
                            response.status,
                            text[:500],
                        )
                        return None, []

                    data = await response.json()

                    # Разные версии API могут возвращать response / text / message
                    text = (
                        data.get("response")
                        or data.get("text")
                        or data.get("message")
                        or ""
                    )
                    if isinstance(text, dict):
                        text = text.get("content", text.get("text", str(text)))

                    # Источники RAG
                    sources: List[Dict[str, Any]] = []
                    raw_sources = data.get("sources") or data.get("citations") or []
                    if isinstance(raw_sources, list):
                        for s in raw_sources:
                            if isinstance(s, dict):
                                sources.append(s)
                            else:
                                sources.append({"content": str(s)})

                    if not text and not sources:
                        log.debug("AnythingLLM empty response: %s", data)

                    return (text.strip() if text else None) or None, sources

        except asyncio.TimeoutError as e:
            last_error = e
            log.warning("AnythingLLM timeout (attempt %s): %s", attempt + 1, e)
        except aiohttp.ClientError as e:
            last_error = e
            log.warning("AnythingLLM client error (attempt %s): %s", attempt + 1, e)
        except Exception as e:
            last_error = e
            log.warning("AnythingLLM error (attempt %s): %s", attempt + 1, e)

        if attempt < RETRY_COUNT:
            await asyncio.sleep(1)

    if last_error:
        log.error("AnythingLLM chat failed: %s", last_error)
    return None, []


async def chat_with_workspace_env(
    message: str,
    history: Optional[List[Dict[str, str]]] = None,
) -> Tuple[Optional[str], List[Dict[str, Any]]]:
    """
    Вызов chat с workspace_slug из переменной окружения ANYTHINGLLM_WORKSPACE_SLUG.
    """
    return await chat(_workspace_slug(), message, history=history)


async def chat_for_email_reply(
    message: str,
    history: Optional[List[Dict[str, str]]] = None,
) -> Tuple[Optional[str], List[Dict[str, Any]]]:
    """
    Генерация черновика ответа на письмо через отдельный workspace AnythingLLM.
    Использует ANYTHINGLLM_EMAIL_WORKSPACE_SLUG, если задан; иначе ANYTHINGLLM_WORKSPACE_SLUG.
    Возвращает (текст_ответа, sources). При ошибке — (None, []).
    """
    slug = _email_workspace_slug() or _workspace_slug()
    return await chat(slug, message, history=history)

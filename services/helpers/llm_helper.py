"""
LLM Helper Module
Обеспечивает работу с DeepSeek (primary) и GigaChat (fallback) через async функции
"""
import os
import logging
import aiohttp
import asyncio
from typing import List, Dict, Optional
from pathlib import Path

# Загружаем переменные окружения из .env файла (для локальной разработки)
# В Railway переменные окружения доступны автоматически через os.getenv()
try:
    from dotenv import load_dotenv
    project_root = Path(__file__).parent.parent.parent
    env_file = project_root / ".env"
    if env_file.exists():
        load_dotenv(env_file)
        log = logging.getLogger()
        log.debug(f"✅ Загружен .env файл из {env_file}")
except ImportError:
    # dotenv не установлен, это нормально для Railway
    pass

log = logging.getLogger()

# ===================== CONFIGURATION =====================
# Читаем переменные окружения динамически через функции для надежности
def get_openrouter_api_key() -> Optional[str]:
    """Получить OPENROUTER_API_KEY с проверкой"""
    key = os.getenv("OPENROUTER_API_KEY")
    if not key:
        # Пробуем перезагрузить переменные окружения
        try:
            from dotenv import load_dotenv
            load_dotenv(override=False)
            key = os.getenv("OPENROUTER_API_KEY")
        except ImportError:
            pass
    return key

def get_openrouter_api_url() -> str:
    """Получить OPENROUTER_API_URL"""
    return os.getenv("OPENROUTER_API_URL", "https://openrouter.ai/api/v1/chat/completions")

def get_openrouter_model() -> str:
    """Получить OPENROUTER_MODEL"""
    return os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-chat")

def get_gigachat_api_key() -> Optional[str]:
    """Получить GIGACHAT_API_KEY"""
    return os.getenv("GIGACHAT_API_KEY")

def get_gigachat_api_url() -> str:
    """Получить GIGACHAT_API_URL"""
    return os.getenv("GIGACHAT_API_URL", "https://gigachat.devices.sberbank.ru/api/v1/chat/completions")

# Для обратной совместимости оставляем переменные на уровне модуля
OPENROUTER_API_KEY = get_openrouter_api_key()
OPENROUTER_API_URL = get_openrouter_api_url()
OPENROUTER_MODEL = get_openrouter_model()
GIGACHAT_API_KEY = get_gigachat_api_key()
GIGACHAT_API_URL = get_gigachat_api_url()

# Логирование статуса переменных окружения при инициализации модуля
if OPENROUTER_API_KEY:
    log.info(f"✅ OPENROUTER_API_KEY загружен (длина: {len(OPENROUTER_API_KEY)} символов)")
else:
    log.warning("⚠️ OPENROUTER_API_KEY не найден. Проверьте переменные окружения в Railway.")
    railway_env = os.getenv("RAILWAY_ENVIRONMENT")
    if railway_env:
        log.warning(f"⚠️ Railway environment: {railway_env}")

if GIGACHAT_API_KEY:
    log.info(f"✅ GIGACHAT_API_KEY загружен (длина: {len(GIGACHAT_API_KEY)} символов)")
else:
    log.debug("ℹ️ GIGACHAT_API_KEY не установлен (fallback будет недоступен)")

# ===================== DEEPSEEK (PRIMARY) =====================

async def deepseek_chat(
    messages: List[Dict[str, str]], 
    use_system_message: bool = False, 
    system_content: str = "",
    max_tokens: int = 2000,
    temperature: float = 0.7
) -> Optional[str]:
    """
    Асинхронная отправка запроса в DeepSeek через OpenRouter API
    
    Args:
        messages: Список сообщений в формате [{"role": "user", "content": "..."}]
        use_system_message: Использовать system message
        system_content: Содержимое system message
        max_tokens: Максимальное количество токенов
        temperature: Температура генерации
    
    Returns:
        Ответ от модели или None при ошибке
    """
    # Читаем переменные окружения динамически при каждом вызове
    api_key = get_openrouter_api_key()
    api_url = get_openrouter_api_url()
    model = get_openrouter_model()
    
    if not api_key:
        log.error("❌ OPENROUTER_API_KEY не установлен. Проверьте переменные окружения в Railway.")
        # Дополнительная диагностика
        railway_env = os.getenv("RAILWAY_ENVIRONMENT")
        if railway_env:
            log.error(f"❌ Railway environment: {railway_env}, но OPENROUTER_API_KEY не найден")
        return None
    
    # Очищаем API ключ от пробелов и переносов строк
    api_key_clean = api_key.strip().replace('\n', '').replace('\r', '') if api_key else None
    
    if not api_key_clean:
        log.error("❌ OPENROUTER_API_KEY пустой или не установлен")
        return None
    
    app_url = os.getenv("APP_URL", "https://hr2137-bot.railway.app").strip()
    headers = {
        "Authorization": f"Bearer {api_key_clean}",
        "Content-Type": "application/json",
        "HTTP-Referer": app_url,
        "X-Title": "HR2137 Bot RAG"
    }
    
    # Если есть system message, добавляем его первым
    if use_system_message and system_content:
        if not any(msg.get("role") == "system" for msg in messages):
            messages = [{"role": "system", "content": system_content}] + messages
    
    data = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature
    }
    
    try:
        log.info(f"🌐 [DeepSeek] Отправка запроса к OpenRouter: модель {model}")
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                api_url,
                json=data,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                log.info(f"📡 [DeepSeek] Статус ответа: {response.status}")
                
                if response.status == 404:
                    error_text = await response.text()
                    log.error(f"❌ [DeepSeek] 404 Not Found - модель {OPENROUTER_MODEL} недоступна")
                    log.error(f"❌ Ответ сервера: {error_text}")
                    return None
                
                if response.status >= 400:
                    error_text = await response.text()
                    log.error(f"❌ [DeepSeek] HTTP ошибка {response.status}: {error_text}")
                    return None
                
                response_json = await response.json()
                
                if "choices" in response_json and len(response_json["choices"]) > 0:
                    content = response_json["choices"][0]["message"]["content"]
                    log.info(f"✅ [DeepSeek] Получен ответ: {content[:100]}...")
                    return content
                else:
                    log.error(f"❌ [DeepSeek] Неожиданный формат ответа: {response_json}")
                    return None
                    
    except aiohttp.ClientError as e:
        log.error(f"❌ [DeepSeek] Ошибка клиента: {e}")
        return None
    except asyncio.TimeoutError:
        log.error(f"❌ [DeepSeek] Таймаут при запросе (60 секунд)")
        return None
    except Exception as e:
        log.error(f"❌ [DeepSeek] Неожиданная ошибка: {e}")
        import traceback
        log.error(f"❌ Traceback: {traceback.format_exc()}")
        return None

# ===================== GIGACHAT (FALLBACK) =====================

async def gigachat_chat(
    messages: List[Dict[str, str]], 
    use_system_message: bool = False, 
    system_content: str = "",
    max_tokens: int = 2000,
    temperature: float = 0.7
) -> Optional[str]:
    """
    Асинхронная отправка запроса в GigaChat API (fallback для российского решения)
    
    Args:
        messages: Список сообщений в формате [{"role": "user", "content": "..."}]
        use_system_message: Использовать system message
        system_content: Содержимое system message
        max_tokens: Максимальное количество токенов
        temperature: Температура генерации
    
    Returns:
        Ответ от модели или None при ошибке
    """
    # Читаем переменные окружения динамически при каждом вызове
    api_key = get_gigachat_api_key()
    api_url = get_gigachat_api_url()
    
    if not api_key:
        log.error("❌ GIGACHAT_API_KEY не установлен")
        return None
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Если есть system message, добавляем его первым
    if use_system_message and system_content:
        if not any(msg.get("role") == "system" for msg in messages):
            messages = [{"role": "system", "content": system_content}] + messages
    
    data = {
        "model": "GigaChat",  # Стандартное имя модели для GigaChat
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature
    }
    
    try:
        log.info(f"🌐 [GigaChat] Отправка запроса к GigaChat API")
        
        # Отключаем проверку SSL для GigaChat (самоподписанный сертификат)
        import ssl
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.post(
                api_url,
                json=data,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                log.info(f"📡 [GigaChat] Статус ответа: {response.status}")
                
                if response.status >= 400:
                    error_text = await response.text()
                    log.error(f"❌ [GigaChat] HTTP ошибка {response.status}: {error_text}")
                    return None
                
                response_json = await response.json()
                
                # GigaChat может иметь другую структуру ответа
                if "choices" in response_json and len(response_json["choices"]) > 0:
                    content = response_json["choices"][0]["message"]["content"]
                    log.info(f"✅ [GigaChat] Получен ответ: {content[:100]}...")
                    return content
                elif "response" in response_json:
                    # Альтернативный формат ответа GigaChat
                    content = response_json["response"]
                    log.info(f"✅ [GigaChat] Получен ответ: {content[:100]}...")
                    return content
                else:
                    log.error(f"❌ [GigaChat] Неожиданный формат ответа: {response_json}")
                    return None
                    
    except aiohttp.ClientError as e:
        log.error(f"❌ [GigaChat] Ошибка клиента: {e}")
        return None
    except asyncio.TimeoutError:
        log.error(f"❌ [GigaChat] Таймаут при запросе (60 секунд)")
        return None
    except Exception as e:
        log.error(f"❌ [GigaChat] Неожиданная ошибка: {e}")
        import traceback
        log.error(f"❌ Traceback: {traceback.format_exc()}")
        return None

# ===================== UNIFIED INTERFACE WITH FALLBACK =====================

async def generate_with_fallback(
    messages: List[Dict[str, str]], 
    use_system_message: bool = False, 
    system_content: str = "",
    max_tokens: int = 2000,
    temperature: float = 0.7,
    use_fallback: bool = True
) -> str:
    """
    Унифицированная функция генерации ответа с автоматическим fallback
    Сначала пытается использовать DeepSeek, при ошибке переключается на GigaChat
    
    Args:
        messages: Список сообщений
        use_system_message: Использовать system message
        system_content: Содержимое system message
        max_tokens: Максимальное количество токенов
        temperature: Температура генерации
        use_fallback: Использовать fallback на GigaChat при ошибке
    
    Returns:
        Ответ от модели или сообщение об ошибке
    """
    # Пытаемся использовать DeepSeek (primary)
    result = await deepseek_chat(
        messages=messages,
        use_system_message=use_system_message,
        system_content=system_content,
        max_tokens=max_tokens,
        temperature=temperature
    )
    
    if result is not None:
        return result
    
    # Если DeepSeek недоступен и включен fallback, пробуем GigaChat
    if use_fallback:
        log.warning("⚠️ DeepSeek недоступен, переключаюсь на GigaChat (fallback)")
        result = await gigachat_chat(
            messages=messages,
            use_system_message=use_system_message,
            system_content=system_content,
            max_tokens=max_tokens,
            temperature=temperature
        )
        
        if result is not None:
            log.info("✅ Успешно переключился на GigaChat (fallback) - бот продолжает работать")
            return result
        else:
            log.error("❌ GigaChat также недоступен после переключения с DeepSeek")
    
    # Если оба провайдера недоступны
    log.error("❌ Оба LLM провайдера недоступны (DeepSeek и GigaChat)")
    return "Извините, сервис временно недоступен. Пожалуйста, попробуйте позже."


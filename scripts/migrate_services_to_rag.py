#!/usr/bin/env python3
"""
Миграция услуг в RAG коллекцию hr2137_bot_knowledge_base

Парсит текст с услугами (каждая услуга - 2 строки: название + цена)
и загружает их в Qdrant для точного поиска через RAG.
"""

import os
import sys
import logging
import hashlib
import time
from typing import List, Dict
from datetime import datetime
from pathlib import Path

# Добавляем корневую директорию проекта в sys.path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Загружаем переменные окружения из .env файла
try:
    from dotenv import load_dotenv
    load_dotenv(project_root / ".env")
except ImportError:
    pass  # python-dotenv не установлен, используем только системные переменные окружения

import requests  # pip install requests
from qdrant_client import QdrantClient
from qdrant_client.http.models import PointStruct

# =============================================================================
# КОНФИГ
# =============================================================================

# Используем ту же логику определения URL что и в qdrant_helper.py
try:
    from config import load_config
    _qdrant_config = load_config("qdrant")
    _qdrant_settings = _qdrant_config.get("qdrant", {})
except Exception:
    _qdrant_settings = {}

# Приоритет: QDRANT_HOST -> RAILWAY_SERVICE_QDRANT_URL -> private domain -> QDRANT_URL
QDRANT_HOST = _qdrant_settings.get("host") or os.getenv("QDRANT_HOST")
RAILWAY_SERVICE_QDRANT_URL = os.getenv("RAILWAY_SERVICE_QDRANT_URL")
QDRANT_PORT = _qdrant_settings.get("port") or os.getenv("QDRANT_PORT", "6333")

if QDRANT_HOST:
    # Определяем, является ли домен публичным
    is_public_domain = (
        ".up.railway.app" in QDRANT_HOST or
        ".railway.app" in QDRANT_HOST or
        QDRANT_HOST.startswith("https://")
    )
    if is_public_domain:
        if QDRANT_HOST.startswith("https://"):
            QDRANT_URL = QDRANT_HOST
        elif QDRANT_HOST.startswith("http://"):
            QDRANT_URL = QDRANT_HOST.replace("http://", "https://")
        else:
            QDRANT_URL = f"https://{QDRANT_HOST}"
    else:
        QDRANT_URL = f"http://{QDRANT_HOST}:{QDRANT_PORT}"
elif RAILWAY_SERVICE_QDRANT_URL:
    if RAILWAY_SERVICE_QDRANT_URL.startswith("https://"):
        QDRANT_URL = RAILWAY_SERVICE_QDRANT_URL
    else:
        QDRANT_URL = f"https://{RAILWAY_SERVICE_QDRANT_URL}"
elif os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("RAILWAY_PROJECT_ID"):
    QDRANT_URL = f"http://qdrant.railway.internal:{QDRANT_PORT}"
else:
    QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")

COLLECTION_NAME = _qdrant_settings.get("collection_name", "hr2137_bot_knowledge_base")

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")  # Опциональный API ключ для Qdrant
EMBEDDING_MODEL = "qwen/qwen3-embedding-8b"  # 1536-мерные эмбеддинги для совместимости с Qdrant коллекцией

# Таймауты для Qdrant (уменьшены для быстрого запуска)
QDRANT_TIMEOUT = 10.0  # Уменьшенный таймаут для быстрого запуска
QDRANT_MAX_RETRIES = 2  # Меньше попыток
QDRANT_RETRY_DELAY = 1.0  # Меньше задержка

if not OPENROUTER_API_KEY:
    print("❌ Установите переменную окружения OPENROUTER_API_KEY=sk-or-...")
    sys.exit(1)

# Настройка OpenRouter для эмбеддингов
OPENROUTER_EMBEDDINGS_URL = "https://openrouter.ai/api/v1/embeddings"

# =============================================================================
# SERVICES_TEXT (ПОЛНЫЙ)
# =============================================================================

SERVICES_TEXT = """Услуги исполнителя
Автоматизация и настройка HR бизнес - процессов / постановка работы HR-функции с "0"
от 80 000 рублей
Стратегическая сессия
от 85 000 рублей
Оптимизация и разработка организационной структуры компании / группы компаний
от 80 000 рублей
Оптимизация / описание / реинжиниринг бизнес-процессов
от 90 000 рублей
HR-сопровождение компании / HRD на аутсорсинге
от 25 000 рублей
Оптимизация оплаты труда, численности и затрат на персонал
от 100 000 рублей
Коучинг руководителей и управленческих команд
от 30 000 рублей
Трудоустройство / карьерный коучинг для ТОП - менеджеров
от 10 000 рублей
Сопровождение реорганизации и антикризисных трансформаций компании
от 50 000 рублей
Консультация по трудоустройству / составлению резюме
от 10 000 рублей
Трудоустройство / смена работы с увеличением зарплаты
от 10 000 рублей
Помогаю сменить деятельность / найти и получить работу по новому профилю
от 10 000 рублей
Внедрение / автоматизация системы массового подбора и адаптации персонала
от 70 000 рублей
Подготовка к переговорам с руководителем ( о зарплате / карьерном росте / при реорганизации)
от 10 000 рублей
Кадровый аудит и постановка КДП компании любой численности
от 50 000 рублей
Автоматизация бизнес-процессов "под ключ"
от 200 000 рублей
Разработка HR - процессов и регламентов
от 150 000 рублей
Автоматизация онбординга персонала
от 120 000 рублей
Разработка системы мотивации отдела продаж
от 60 000 рублей
Стратегическая сессия OKR
от 80 000 рублей
Разработка корпоративной базы знаний
от 100 000 рублей
Подготовка к собеседованию / переговорам о зарплате
от 10 000 рублей
Услуги профориентолога, разработка карьерных векторов и их монетизации
от 10 000 рублей
Описание бизнес-процессов / разработка регламентов для малого бизнеса
от 40 000 рублей
Консультация по подбору персонала
от 10 000 рублей
Разработка и внедрение системы KPIs / системы сбалансированных показателей
от 60 000 рублей
Разработка и внедрение результативной системы оплаты труда
от 60 000 рублей
Разработка ЛНА организации
от 35 000 рублей
Повышение эффективности сотрудников и подразделений
от 100 000 рублей
Формирование команды / консалтинг по подбору персонала для малого бизнеса
от 40 000 рублей
Тренинг по трудоустройству для высвобождающегося персонала
от 80 000 рублей
Тренинг "Эффективное взаимодействие подразделений"
от 90 000 рублей
Обучение руководителей филиалов управлению персоналом (HR-цикл)
от 80 000 рублей
Обучение сотрудников ведению КДП с "0" / автоматизация КДП
от 60 000 рублей
Спикер по темам HR / эффективности и управления персоналом
от 50 000 рублей
Разработка электронных курсов для сотрудников и руководителей
от 60 000 рублей
Тренинг «Эффективный HR-цикл: от операционки к стратегии для HRG / HRBP»
от 100 000 рублей
Тренинг «Продвинутый массовый подбор: технологии и AI»
от 90 000 рублей
Тренинг «Массовый подбор: скорость и качество 2.0»
от 100 000 рублей
Тренинг «Эмоциональный интеллект (EQ) для бизнеса»
от 90 000 рублей
Тренинг «Лидерство 2.0 и управление командой»
от 90 000 рублей
Обучение управлению проектами по Agile (Scrum, Kanban)
от 90 000 рублей
Тренинг по проектному управлению
от 90 000 рублей
Аудит профессиональных и управленческих компетенций IT-команды
от 200 000 рублей
Тренинг по обучению сотрудников работе с AI
от 90 000 рублей
Сессия построения и синхронизации командной работы
от 100 000 рублей
Стратегическая сессия разработки новых продуктов и выхода на новые рынки
от 120 000 рублей
Антикризисная стратегическая сессия
от 80 000 рублей
Стратегическая сессия по внедрению ИИ – решений
от 120 000 рублей
Стратегическая сессия по цифровой трансформации бизнеса
от 120 000 рублей
Сессия сценарного планирования для бизнеса
от 100 000 рублей
Фасилитация стратегической сессии
от 80 000 рублей
Форсайт - сессия
от 90 000 рублей
Нормирование труда
от 60 000 рублей
Оптимизация оплаты труда, численности и затрат на персонал
от 100 000 рублей
Консультация по управлению персоналом в условиях кризиса
от 30 000 рублей
Отрисовка бизнес-процессов из текстового описания
от 30 000 рублей
Консалтинг по трудовому законодательству
от 10 000 рублей
HR-аудит компании / подразделения
от 40 000 рублей
Разработка стандартов и регламентов
от 30 000 рублей
Восстановление КДП любой сложности / численности компании
от 80 000 рублей
Автоматизация работы сотрудников / управления малого бизнеса
от 40 000 рублей
Стратегическая сессия по развитию малого бизнеса / стартапа
от 30 000 рублей
Консультация по вопросам персонала / управления для малого бизнеса
от 10 000 рублей
Разработка оргструктуры и функциональной матрицы для малого бизнеса и стартапов
от 25 000 рублей"""

# =============================================================================
# ЛОГИРОВАНИЕ
# =============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)

# =============================================================================
# ПАРСИНГ УСЛУГ
# =============================================================================

def parse_services(text: str) -> List[Dict]:
    """
    Парсит текст с услугами.
    Каждая услуга - 2 строки: название + цена (начинается с "от X рублей")
    """
    lines = [line.strip() for line in text.strip().split("\n") if line.strip()]
    services = []

    # Пропускаем первую строку "Услуги исполнителя"
    i = 1
    while i < len(lines):
        title = lines[i]
        i += 1

        if i < len(lines) and lines[i].startswith("от"):
            price_str = lines[i]
            price_str_clean = (
                price_str.replace("от", "")
                .replace("рублей", "")
                .replace(" ", "")
                .strip()
            )
            try:
                price = int(price_str_clean)
            except ValueError:
                log.warning(f"⚠️ Не удалось распарсить цену: {price_str}")
                price = 0
            i += 1
        else:
            log.warning(f"⚠️ Не найдена цена для услуги: {title}")
            price_str = "цена не указана"
            price = 0

        service = {
            "title": title,
            "price": price,
            "price_str": price_str,
            "indexed_at": datetime.now().isoformat(),
            "source_type": "service",
            "category": "услуги_исполнителя",
        }
        services.append(service)

    return services

def generate_service_id(service: Dict) -> str:
    """Генерирует уникальный ID для услуги"""
    service_str = f"{service.get('title', '')}_{service.get('price', 0)}"
    return hashlib.md5(service_str.encode()).hexdigest()

# =============================================================================
# EMBEDDING ЧЕРЕЗ OPENROUTER QWEN
# =============================================================================

def generate_embedding(text: str, target_dimension: int = 1536) -> List[float]:
    """
    Генерирует эмбеддинг через OpenRouter (Qwen3-Embedding-8B) используя прямой HTTP запрос.
    Автоматически обрезает или дополняет эмбеддинг до target_dimension.
    """
    if not OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY не установлен")
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": os.getenv("APP_URL", "https://github.com/HR2137_bot").strip(),
        "X-Title": "HR2137_bot",
    }
    
    data = {
        "model": EMBEDDING_MODEL,
        "input": text[:8000]  # Ограничение для API
    }
    
    try:
        response = requests.post(
            OPENROUTER_EMBEDDINGS_URL,
            json=data,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()
        result = response.json()
        embedding = result["data"][0]["embedding"]
        embedding_size = len(embedding)
        
        # Адаптируем размерность к целевой
        if embedding_size != target_dimension:
            if embedding_size > target_dimension:
                # Обрезаем до нужной размерности
                embedding = embedding[:target_dimension]
                log.debug(f"✂️ Эмбеддинг обрезан: {embedding_size} → {target_dimension}")
            else:
                # Дополняем нулями если меньше
                padding_size = target_dimension - embedding_size
                embedding = embedding + [0.0] * padding_size
                log.debug(f"📌 Эмбеддинг дополнен: {embedding_size} → {target_dimension} (+{padding_size} нулей)")
        
        return embedding
    except requests.exceptions.RequestException as e:
        log.error(f"❌ Ошибка при запросе к OpenRouter: {e}")
        if hasattr(e, 'response') and e.response is not None:
            log.error(f"❌ Ответ сервера: {e.response.text}")
        raise

# =============================================================================
# ИНФОРМАЦИЯ О КОЛЛЕКЦИИ
# =============================================================================

def print_collection_info(client: QdrantClient):
    """Выводит информацию о коллекции с retry логикой"""
    log.info("\n" + "=" * 80)
    log.info("📊 Информация о коллекции:")
    log.info("=" * 80)

    for attempt in range(QDRANT_MAX_RETRIES):
        try:
            info = client.get_collection(COLLECTION_NAME)
            count_result = client.count(collection_name=COLLECTION_NAME, exact=True)
            cfg = info.config.params.vectors

            log.info(f"📁 Коллекция: {COLLECTION_NAME}")
            log.info("✅ Существует: Да")
            log.info(f"🔢 Всего точек: {count_result.count}")
            log.info(f"📐 Размерность векторов: {cfg.size}")
            log.info(f"📏 Метрика расстояния: {cfg.distance}")
            break  # Успешно получена информация
        except Exception as e:
            error_str = str(e).lower()
            if "not found" in error_str or "404" in error_str or "does not exist" in error_str:
                log.info(f"❌ Коллекция {COLLECTION_NAME} не существует")
                break
            elif "timeout" in error_str or "timed out" in error_str or "handshake" in error_str:
                if attempt < QDRANT_MAX_RETRIES - 1:
                    delay = QDRANT_RETRY_DELAY * (attempt + 1)
                    log.warning(
                        f"⚠️ Таймаут при получении информации (попытка {attempt + 1}/{QDRANT_MAX_RETRIES}), повтор через {delay}с..."
                    )
                    time.sleep(delay)
                else:
                    log.warning(f"⚠️ Ошибка таймаута при получении информации о коллекции: {e}")
                    break
            else:
                log.warning(f"⚠️ Ошибка при получении информации о коллекции: {e}")
                break

    log.info("=" * 80 + "\n")

# =============================================================================
# МИГРАЦИЯ ЧЕРЕЗ HTTP API
# =============================================================================

def migrate_services_to_rag_http(services: List[Dict]) -> bool:
    """
    Загружает услуги в RAG коллекцию Qdrant используя прямой HTTP API
    (альтернатива Python клиенту)
    """
    log.info(f"🚀 Начинаем миграцию {len(services)} услуг через HTTP API...")
    
    # Подготовка заголовков
    headers = {
        "Content-Type": "application/json",
    }
    if QDRANT_API_KEY:
        headers["api-key"] = QDRANT_API_KEY
    
    base_url = QDRANT_URL.rstrip("/")
    
    # 1. Проверяем существование коллекции
    log.info("\n📊 Проверка коллекции...")
    collection_url = f"{base_url}/collections/{COLLECTION_NAME}"
    
    for attempt in range(QDRANT_MAX_RETRIES):
        try:
            response = requests.get(
                collection_url,
                headers=headers,
                timeout=QDRANT_TIMEOUT
            )
            if response.status_code == 200:
                collection_info = response.json()
                vector_size = collection_info["result"]["config"]["params"]["vectors"]["size"]
                log.info(f"✅ Коллекция найдена, vector_size={vector_size}")
                break
            elif response.status_code == 404:
                log.error(f"❌ Коллекция {COLLECTION_NAME} не найдена")
                return False
            else:
                response.raise_for_status()
        except requests.exceptions.Timeout:
            if attempt < QDRANT_MAX_RETRIES - 1:
                delay = QDRANT_RETRY_DELAY * (attempt + 1)
                log.warning(f"⚠️ Таймаут при проверке коллекции (попытка {attempt + 1}/{QDRANT_MAX_RETRIES})")
                time.sleep(delay)
            else:
                log.error("❌ Таймаут при проверке коллекции после всех попыток")
                return False
        except Exception as e:
            log.error(f"❌ Ошибка при проверке коллекции: {e}")
            return False
    else:
        log.error("❌ Не удалось проверить коллекцию")
        return False
    
    # 2. Генерируем эмбеддинги и подготавливаем точки
    log.info("\n" + "=" * 80)
    log.info("🔄 Генерация эмбеддингов и подготовка данных...")
    log.info("=" * 80)
    
    points_data = []
    successful = 0
    failed = 0
    start_time = datetime.now()
    
    for idx, service in enumerate(services, 1):
        try:
            service_text = f"{service['title']} {service['price_str']} услуга консультация"
            progress = (idx / len(services)) * 100
            log.info(
                f"[{idx}/{len(services)}] ({progress:.1f}%) 🔄 Генерация эмбеддинга: {service['title'][:50]}..."
            )
            
            embedding_start = datetime.now()
            embedding = generate_embedding(service_text, target_dimension=vector_size)
            embedding_time = (datetime.now() - embedding_start).total_seconds()
            
            if embedding is None:
                log.warning(
                    f"⚠️ [{idx}/{len(services)}] Не удалось сгенерировать эмбеддинг для: {service['title']}"
                )
                failed += 1
                continue
            
            if len(embedding) != vector_size:
                log.error(
                    f"❌ Размер эмбеддинга {len(embedding)} != vector_size коллекции {vector_size}"
                )
                failed += 1
                continue
            
            log.info(
                f"    ✅ Эмбеддинг создан ({embedding_time:.2f}с, размерность: {len(embedding)})"
            )
            
            service_id = generate_service_id(service)
            point_id = int(service_id[:8], 16)
            
            point = {
                "id": point_id,
                "vector": embedding,
                "payload": {
                    "title": service["title"],
                    "price": service["price"],
                    "price_str": service["price_str"],
                    "text": service_text,
                    "indexed_at": service["indexed_at"],
                    "source_type": "service",
                    "category": service.get("category", "услуги_исполнителя"),
                    "service_id": service_id,
                    "id": service_id,
                    "master": "",
                    "duration": 0,
                }
            }
            
            points_data.append(point)
            successful += 1
            
        except Exception as e:
            log.error(
                f"❌ [{idx}/{len(services)}] Ошибка обработки услуги "
                f"'{service.get('title', 'unknown')}': {e}"
            )
            failed += 1
            continue
    
    generation_time = (datetime.now() - start_time).total_seconds()
    log.info("\n" + "=" * 80)
    log.info(
        f"✅ Генерация завершена: {successful} успешно, {failed} ошибок "
        f"(время: {generation_time:.1f}с)"
    )
    log.info("=" * 80)
    
    if not points_data:
        log.error("❌ Нет точек для загрузки")
        return False
    
    # 3. Загружаем точки через HTTP API (батчами)
    log.info("\n" + "=" * 80)
    log.info(f"📤 Загрузка {len(points_data)} услуг в Qdrant через HTTP API...")
    log.info("=" * 80)
    
    upsert_url = f"{base_url}/collections/{COLLECTION_NAME}/points"
    batch_size = 100
    upload_start = datetime.now()
    
    for batch_idx in range(0, len(points_data), batch_size):
        batch = points_data[batch_idx:batch_idx + batch_size]
        batch_num = (batch_idx // batch_size) + 1
        total_batches = (len(points_data) + batch_size - 1) // batch_size
        
        log.info(f"📦 Загрузка батча {batch_num}/{total_batches} ({len(batch)} точек)...")
        
        payload = {
            "points": batch,
            "wait": True
        }
        
        for attempt in range(QDRANT_MAX_RETRIES):
            try:
                response = requests.put(
                    upsert_url,
                    json=payload,
                    headers=headers,
                    timeout=QDRANT_TIMEOUT
                )
                response.raise_for_status()
                result = response.json()
                log.info(f"    ✅ Батч {batch_num} загружен успешно")
                break
            except requests.exceptions.Timeout:
                if attempt < QDRANT_MAX_RETRIES - 1:
                    delay = QDRANT_RETRY_DELAY * (attempt + 1)
                    log.warning(
                        f"    ⚠️ Таймаут при загрузке батча {batch_num} "
                        f"(попытка {attempt + 1}/{QDRANT_MAX_RETRIES})"
                    )
                    time.sleep(delay)
                else:
                    log.error(f"    ❌ Таймаут при загрузке батча {batch_num} после всех попыток")
                    return False
            except Exception as e:
                if attempt < QDRANT_MAX_RETRIES - 1:
                    delay = QDRANT_RETRY_DELAY * (attempt + 1)
                    log.warning(
                        f"    ⚠️ Ошибка при загрузке батча {batch_num} "
                        f"(попытка {attempt + 1}/{QDRANT_MAX_RETRIES}): {e}"
                    )
                    time.sleep(delay)
                else:
                    log.error(f"    ❌ Ошибка при загрузке батча {batch_num}: {e}")
                    return False
    
    upload_time = (datetime.now() - upload_start).total_seconds()
    log.info(f"✅ Успешно загружено {successful} услуг (время: {upload_time:.1f}с)")
    
    if failed > 0:
        log.warning(f"⚠️ Не удалось загрузить {failed} услуг")
    
    # 4. Проверяем количество точек
    count_url = f"{base_url}/collections/{COLLECTION_NAME}/points/count"
    for attempt in range(QDRANT_MAX_RETRIES):
        try:
            response = requests.post(
                count_url,
                json={"exact": True},
                headers=headers,
                timeout=QDRANT_TIMEOUT
            )
            response.raise_for_status()
            count_result = response.json()
            total_points = count_result["result"]["count"]
            log.info(f"📊 Проверка: в коллекции теперь {total_points} точек")
            break
        except Exception as e:
            if attempt < QDRANT_MAX_RETRIES - 1:
                delay = QDRANT_RETRY_DELAY * (attempt + 1)
                log.warning(f"⚠️ Таймаут при проверке количества точек, повтор через {delay}с...")
                time.sleep(delay)
            else:
                log.warning(f"⚠️ Не удалось проверить количество точек: {e}")
    
    return True

# =============================================================================
# МИГРАЦИЯ
# =============================================================================

def create_qdrant_client():
    """Создает QdrantClient с таймаутами и retry логикой"""
    
    client_kwargs = {
        "url": QDRANT_URL,
        "timeout": QDRANT_TIMEOUT,
        "prefer_grpc": False,  # Используем HTTP для публичных доменов
    }
    
    if QDRANT_API_KEY:
        client_kwargs["api_key"] = QDRANT_API_KEY
        log.info(f"🔗 Подключение к Qdrant с API ключом (таймаут: {QDRANT_TIMEOUT}с)")
    else:
        log.info(f"🔗 Подключение к Qdrant (таймаут: {QDRANT_TIMEOUT}с)")
    
    # Retry логика для создания клиента
    for attempt in range(QDRANT_MAX_RETRIES):
        try:
            client = QdrantClient(**client_kwargs)
            # Проверяем подключение простым запросом
            client.get_collections()
            log.info(f"✅ Успешное подключение к Qdrant")
            return client
        except Exception as e:
            error_str = str(e).lower()
            if attempt < QDRANT_MAX_RETRIES - 1:
                delay = QDRANT_RETRY_DELAY * (attempt + 1)
                log.warning(
                    f"⚠️ Попытка {attempt + 1}/{QDRANT_MAX_RETRIES} подключения не удалась: {str(e)[:100]}"
                )
                log.info(f"⏳ Повторная попытка через {delay} секунд...")
                time.sleep(delay)
            else:
                log.error(f"❌ Не удалось подключиться к Qdrant после {QDRANT_MAX_RETRIES} попыток: {e}")
                raise
    
    return None

def migrate_services_to_rag(services: List[Dict]) -> bool:
    """
    Загружает услуги в RAG коллекцию Qdrant
    """
    log.info(f"🚀 Начинаем миграцию {len(services)} услуг в RAG коллекцию...")
    log.info("\n📊 Статус коллекции ДО загрузки:")

    try:
        client = create_qdrant_client()
    except Exception as e:
        log.error(f"❌ Не удалось создать клиент Qdrant: {e}")
        return False
    
    print_collection_info(client)

    # Проверяем, что коллекция существует и узнаём vector_size с retry
    vector_size = None
    
    for attempt in range(QDRANT_MAX_RETRIES):
        try:
            info = client.get_collection(COLLECTION_NAME)
            vector_size = info.config.params.vectors.size
            log.info(f"✅ Коллекция готова, vector_size={vector_size}")
            break
        except Exception as e:
            error_str = str(e).lower()
            if "not found" in error_str or "404" in error_str or "does not exist" in error_str:
                log.error(
                    f"❌ Коллекция {COLLECTION_NAME} не найдена. "
                    f"Создайте её в Qdrant dashboard с размерностью, совпадающей с эмбеддингами модели."
                )
                return False
            elif "timeout" in error_str or "timed out" in error_str or "handshake" in error_str:
                if attempt < QDRANT_MAX_RETRIES - 1:
                    delay = QDRANT_RETRY_DELAY * (attempt + 1)
                    log.warning(
                        f"⚠️ Таймаут при получении коллекции (попытка {attempt + 1}/{QDRANT_MAX_RETRIES}): {str(e)[:100]}"
                    )
                    log.info(f"⏳ Повторная попытка через {delay} секунд...")
                    time.sleep(delay)
                else:
                    log.error(f"❌ Ошибка таймаута при получении коллекции после {QDRANT_MAX_RETRIES} попыток: {e}")
                    return False
            else:
                log.error(f"❌ Ошибка при получении коллекции: {e}")
                return False
    
    if vector_size is None:
        log.error("❌ Не удалось получить размерность коллекции")
        return False

    log.info("\n" + "=" * 80)
    log.info("🔄 Генерация эмбеддингов и подготовка данных...")
    log.info("=" * 80)

    points = []
    successful = 0
    failed = 0
    start_time = datetime.now()

    for idx, service in enumerate(services, 1):
        try:
            service_text = f"{service['title']} {service['price_str']} услуга консультация"
            progress = (idx / len(services)) * 100
            log.info(
                f"[{idx}/{len(services)}] ({progress:.1f}%) 🔄 Генерация эмбеддинга: {service['title'][:50]}..."
            )

            embedding_start = datetime.now()
            embedding = generate_embedding(service_text, target_dimension=vector_size)
            embedding_time = (datetime.now() - embedding_start).total_seconds()

            if embedding is None:
                log.warning(
                    f"⚠️ [{idx}/{len(services)}] Не удалось сгенерировать эмбеддинг для: {service['title']}"
                )
                failed += 1
                continue

            if len(embedding) != vector_size:
                log.error(
                    f"❌ Размер эмбеддинга {len(embedding)} != vector_size коллекции {vector_size}"
                )
                failed += 1
                continue

            log.info(
                f"    ✅ Эмбеддинг создан ({embedding_time:.2f}с, размерность: {len(embedding)})"
            )

            payload = {
                "title": service["title"],
                "price": service["price"],
                "price_str": service["price_str"],
                "text": service_text,
                "indexed_at": service["indexed_at"],
                "source_type": "service",
                "category": service.get("category", "услуги_исполнителя"),
                "service_id": generate_service_id(service),
                # Дополнительные поля для совместимости
                "id": generate_service_id(service),
                "master": "",
                "duration": 0,
            }

            service_id = generate_service_id(service)
            point_id = int(service_id[:8], 16)

            points.append(
                PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload=payload,
                )
            )

            successful += 1

        except Exception as e:
            log.error(
                f"❌ [{idx}/{len(services)}] Ошибка обработки услуги "
                f"'{service.get('title', 'unknown')}': {e}"
            )
            failed += 1
            continue

    generation_time = (datetime.now() - start_time).total_seconds()
    log.info("\n" + "=" * 80)
    log.info(
        f"✅ Генерация завершена: {successful} успешно, {failed} ошибок "
        f"(время: {generation_time:.1f}с)"
    )
    log.info("=" * 80)

    if not points:
        log.error("❌ Нет точек для загрузки")
        return False

    log.info("\n" + "=" * 80)
    log.info(f"📤 Загрузка {len(points)} услуг в Qdrant...")
    log.info("=" * 80)

    # Retry логика для загрузки данных
    upload_start = datetime.now()
    result = None
    
    for attempt in range(QDRANT_MAX_RETRIES):
        try:
            result = client.upsert(
                collection_name=COLLECTION_NAME,
                points=points,
                wait=True,
            )
            break  # Успешно загружено
        except Exception as e:
            error_str = str(e).lower()
            if "timeout" in error_str or "timed out" in error_str or "handshake" in error_str:
                if attempt < QDRANT_MAX_RETRIES - 1:
                    delay = QDRANT_RETRY_DELAY * (attempt + 1)
                    log.warning(
                        f"⚠️ Таймаут при загрузке данных (попытка {attempt + 1}/{QDRANT_MAX_RETRIES}): {str(e)[:100]}"
                    )
                    log.info(f"⏳ Повторная попытка через {delay} секунд...")
                    time.sleep(delay)
                else:
                    log.error(f"❌ Ошибка таймаута при загрузке после {QDRANT_MAX_RETRIES} попыток: {e}")
                    import traceback
                    log.error(f"❌ Traceback: {traceback.format_exc()}")
                    return False
            else:
                log.error(f"❌ Ошибка загрузки в Qdrant: {e}")
                import traceback
                log.error(f"❌ Traceback: {traceback.format_exc()}")
                return False
    
    if result is None:
        log.error("❌ Не удалось загрузить данные после всех попыток")
        return False

    upload_time = (datetime.now() - upload_start).total_seconds()
    status = getattr(result, "status", "COMPLETED")

    log.info(f"✅ Статус загрузки: {status}")
    log.info(
        f"✅ Успешно загружено {successful} услуг в RAG коллекцию "
        f"'{COLLECTION_NAME}' (время: {upload_time:.1f}с)"
    )

    if failed > 0:
        log.warning(f"⚠️ Не удалось загрузить {failed} услуг")

    # Проверка количества точек с retry
    for attempt in range(QDRANT_MAX_RETRIES):
        try:
            count_result = client.count(
                collection_name=COLLECTION_NAME,
                exact=True,
            )
            log.info(f"📊 Проверка: в коллекции теперь {count_result.count} точек")
            break
        except Exception as count_e:
            error_str = str(count_e).lower()
            if attempt < QDRANT_MAX_RETRIES - 1 and ("timeout" in error_str or "timed out" in error_str):
                delay = QDRANT_RETRY_DELAY * (attempt + 1)
                log.warning(f"⚠️ Таймаут при проверке количества точек, повтор через {delay}с...")
                time.sleep(delay)
            else:
                log.warning(f"⚠️ Не удалось проверить количество точек: {count_e}")

    log.info("\n📊 Статус коллекции ПОСЛЕ загрузки:")
    print_collection_info(client)

    return True

# =============================================================================
# MAIN
# =============================================================================

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Миграция услуг в RAG коллекцию")
    parser.add_argument(
        "--http",
        action="store_true",
        help="Использовать прямой HTTP API вместо Python клиента"
    )
    args = parser.parse_args()
    
    log.info("=" * 80)
    log.info("🚀 Миграция услуг в RAG коллекцию hr2137_bot_knowledge_base")
    if args.http:
        log.info("📡 Режим: HTTP API (прямые запросы)")
    else:
        log.info("🐍 Режим: Python клиент Qdrant")
    log.info("=" * 80)

    log.info("📝 Парсинг услуг из текста...")
    services = parse_services(SERVICES_TEXT)
    log.info(f"✅ Найдено {len(services)} услуг")

    log.info("\n📋 Примеры услуг:")
    for i, service in enumerate(services[:5], 1):
        log.info(f"  {i}. {service['title']} - {service['price_str']}")

    # Выбираем метод миграции
    if args.http:
        success = migrate_services_to_rag_http(services)
    else:
        success = migrate_services_to_rag(services)
    
    if success:
        log.info("\n" + "=" * 80)
        log.info("✅ Миграция завершена успешно!")
        log.info("=" * 80)
        return 0
    else:
        log.error("\n" + "=" * 80)
        log.error("❌ Миграция завершилась с ошибками")
        log.error("=" * 80)
        return 1

if __name__ == "__main__":
    sys.exit(main())

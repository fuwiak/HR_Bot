"""
Точка входа FastAPI приложения
"""
import os
import sys
import logging
from contextlib import asynccontextmanager

# Добавляем корневую директорию в path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle менеджер приложения"""
    # Startup
    log.info("🚀 Запуск HR Bot Backend...")
    
    # Инициализация базы данных
    try:
        from backend.database import init_db
        if init_db():
            log.info("✅ PostgreSQL инициализирован")
    except Exception as e:
        log.warning(f"⚠️ PostgreSQL недоступен: {e}")
    
    # Инициализация LangGraph
    try:
        from backend.api.services import get_conversation_workflow
        workflow = get_conversation_workflow()
        if workflow.is_initialized():
            log.info("✅ LangGraph Conversation Workflow инициализирован")
    except Exception as e:
        log.warning(f"⚠️ LangGraph недоступен: {e}")
    
    yield
    
    # Shutdown
    log.info("👋 Завершение работы HR Bot Backend...")


# Создание FastAPI приложения
app = FastAPI(
    title="HR Bot API",
    description="API для HR Bot с поддержкой RAG и LangGraph",
    version="2.0.0",
    lifespan=lifespan
)

# CORS настройки
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Базовые эндпоинты
@app.get("/")
async def root():
    """Корневой эндпоинт"""
    return {
        "status": "ok",
        "service": "HR Bot API",
        "version": "2.0.0"
    }


@app.get("/health")
async def health_check():
    """Проверка здоровья сервиса"""
    health = {
        "status": "healthy",
        "services": {}
    }
    
    # Проверка PostgreSQL
    try:
        from backend.database import DATABASE_AVAILABLE
        health["services"]["postgresql"] = "available" if DATABASE_AVAILABLE else "unavailable"
    except:
        health["services"]["postgresql"] = "unavailable"
    
    # Проверка Redis
    try:
        from backend.config import get_redis_config
        redis_config = get_redis_config()
        health["services"]["redis"] = "available" if redis_config.is_available() else "unavailable"
    except:
        health["services"]["redis"] = "unavailable"
    
    # Проверка LangGraph
    try:
        from backend.api.services import LANGGRAPH_AVAILABLE
        health["services"]["langgraph"] = "available" if LANGGRAPH_AVAILABLE else "unavailable"
    except:
        health["services"]["langgraph"] = "unavailable"
    
    return health


@app.post("/api/chat")
async def chat(request: Request):
    """Эндпоинт для чата"""
    try:
        data = await request.json()
        message = data.get("message", "")
        user_id = data.get("user_id", "anonymous")
        platform = data.get("platform", "api")
        
        if not message:
            return JSONResponse(
                status_code=400,
                content={"error": "Сообщение не может быть пустым"}
            )
        
        # Используем LangGraph workflow
        from backend.api.services import query_with_conversation_workflow
        
        result = await query_with_conversation_workflow(
            message=message,
            user_id=str(user_id),
            platform=platform
        )
        
        return {
            "response": result.get("response", ""),
            "status": result.get("status", "success"),
            "task_type": result.get("task_type", "general")
        }
    except Exception as e:
        log.error(f"❌ Ошибка в /api/chat: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.post("/api/rag/search")
async def rag_search(request: Request):
    """Поиск в RAG базе знаний"""
    try:
        data = await request.json()
        query = data.get("query", "")
        limit = data.get("limit", 5)
        
        if not query:
            return JSONResponse(
                status_code=400,
                content={"error": "Запрос не может быть пустым"}
            )
        
        # Импортируем qdrant_helper
        from services.rag.qdrant_helper import search_service
        
        results = search_service(query, limit=limit)
        
        formatted_results = []
        for result in results:
            payload = result.get("payload", {})
            formatted_results.append({
                "title": payload.get("title", ""),
                "price": payload.get("price", 0),
                "price_str": payload.get("price_str", ""),
                "master": payload.get("master", ""),
                "score": result.get("score", 0)
            })
        
        return {
            "query": query,
            "results": formatted_results,
            "count": len(formatted_results)
        }
    except Exception as e:
        log.error(f"❌ Ошибка в /api/rag/search: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.get("/api/services")
async def get_services():
    """Получить список услуг"""
    try:
        from app import get_services as app_get_services
        services = app_get_services()
        return {
            "services": services,
            "count": len(services)
        }
    except Exception as e:
        log.error(f"❌ Ошибка в /api/services: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.get("/api/masters")
async def get_masters():
    """Получить список мастеров"""
    try:
        from app import get_masters as app_get_masters
        masters = app_get_masters()
        return {
            "masters": masters,
            "count": len(masters)
        }
    except Exception as e:
        log.error(f"❌ Ошибка в /api/masters: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


# ==================== YANDEX DISK API ====================

@app.get("/api/yadisk/list")
async def yadisk_list(path: str = "/"):
    """Получить список файлов на Яндекс.Диске"""
    try:
        from services.helpers.yandex_disk_helper import list_files, get_disk_info
        
        result = await list_files(path=path, limit=50)
        disk_info = await get_disk_info()
        
        items = result.get("_embedded", {}).get("items", []) if result else []
        
        formatted_items = []
        for item in items:
            formatted_items.append({
                "name": item.get("name", ""),
                "type": item.get("type", "file"),
                "path": item.get("path", ""),
                "size": item.get("size", 0),
                "modified": item.get("modified", "")
            })
        
        return {
            "items": formatted_items,
            "path": path,
            "count": len(formatted_items),
            "disk_info": {
                "total_space": disk_info.get("total_space", 0) if disk_info else 0,
                "used_space": disk_info.get("used_space", 0) if disk_info else 0
            }
        }
    except Exception as e:
        log.error(f"❌ Ошибка в /api/yadisk/list: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.get("/api/yadisk/search")
async def yadisk_search(query: str):
    """Поиск файлов на Яндекс.Диске"""
    try:
        from services.helpers.yandex_disk_helper import search_files
        
        files = await search_files(query, limit=50)
        
        formatted_files = []
        for file in (files or []):
            formatted_files.append({
                "name": file.get("name", ""),
                "type": file.get("type", "file"),
                "path": file.get("path", ""),
                "size": file.get("size", 0),
                "modified": file.get("modified", "")
            })
        
        return {
            "files": formatted_files,
            "query": query,
            "count": len(formatted_files)
        }
    except Exception as e:
        log.error(f"❌ Ошибка в /api/yadisk/search: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.get("/api/yadisk/recent")
async def yadisk_recent():
    """Получить последние файлы на Яндекс.Диске"""
    try:
        from services.helpers.yandex_disk_helper import get_recent_files
        
        files = await get_recent_files(limit=20)
        
        formatted_files = []
        for file in (files or []):
            formatted_files.append({
                "name": file.get("name", ""),
                "type": file.get("type", "file"),
                "path": file.get("path", ""),
                "size": file.get("size", 0),
                "modified": file.get("modified", "")
            })
        
        return {
            "files": formatted_files,
            "count": len(formatted_files)
        }
    except Exception as e:
        log.error(f"❌ Ошибка в /api/yadisk/recent: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


# ==================== BOOKING API ====================

@app.post("/api/booking")
async def create_booking(request: Request):
    """Создать запись на услугу"""
    try:
        data = await request.json()
        service = data.get("service", "")
        master = data.get("master", "")
        date = data.get("date", "")
        time = data.get("time", "")
        user_id = data.get("userId", "")
        
        if not all([service, master, date, time]):
            return JSONResponse(
                status_code=400,
                content={"error": "Заполните все обязательные поля"}
            )
        
        # Формируем запись
        booking_info = f"ЗАПИСЬ: {service} | {master} | {date} {time}"
        
        log.info(f"📅 Новая запись от {user_id}: {booking_info}")
        
        # Отправляем уведомление администратору через Telegram (если настроено)
        try:
            admin_ids = os.getenv("TELEGRAM_ADMIN_IDS", "5305427956").split(",")
            bot_token = os.getenv("TELEGRAM_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
            
            if bot_token and admin_ids:
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    for admin_id in admin_ids:
                        admin_id = admin_id.strip()
                        if admin_id:
                            message = (
                                f"📅 *Новая запись из Mini App!*\n\n"
                                f"📋 Услуга: {service}\n"
                                f"👤 Специалист: {master}\n"
                                f"📆 Дата: {date}\n"
                                f"🕐 Время: {time}\n"
                                f"🆔 Пользователь: {user_id}"
                            )
                            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                            await session.post(url, json={
                                "chat_id": admin_id,
                                "text": message,
                                "parse_mode": "Markdown"
                            })
        except Exception as notify_error:
            log.warning(f"⚠️ Не удалось отправить уведомление: {notify_error}")
        
        return {
            "success": True,
            "booking": {
                "service": service,
                "master": master,
                "date": date,
                "time": time,
                "user_id": user_id
            },
            "message": "Запись успешно создана"
        }
    except Exception as e:
        log.error(f"❌ Ошибка в /api/booking: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


# ==================== ADMIN API ====================

@app.get("/api/admin/check")
async def check_admin(user_id: str):
    """Проверить, является ли пользователь администратором"""
    try:
        admin_ids_str = os.getenv("TELEGRAM_ADMIN_IDS", os.getenv("TELEGRAM_ADMIN_ID", "5305427956"))
        admin_ids = [int(uid.strip()) for uid in admin_ids_str.split(",") if uid.strip().isdigit()]
        
        try:
            user_id_int = int(user_id)
            is_admin = user_id_int in admin_ids
        except ValueError:
            is_admin = False
        
        return {
            "is_admin": is_admin,
            "user_id": user_id
        }
    except Exception as e:
        log.error(f"❌ Ошибка в /api/admin/check: {e}")
        return {"is_admin": False}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", os.getenv("WEB_PORT", "8081")))
    uvicorn.run(app, host="0.0.0.0", port=port)

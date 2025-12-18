"""
Ретро UI Дашборд для управления RAG системой и просмотра метрик.
FastAPI бэкенд с веб-интерфейсом в стиле ретро терминала.
"""

import os
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, BackgroundTasks, Request, Depends, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import asyncio
from dotenv import load_dotenv
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="HR2137 RAG Dashboard", version="1.0.0")

# ===================== AUTHENTICATION =====================
# Учетные данные для входа
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin"

# Секретный ключ для подписи cookies (в продакшене используйте случайный ключ из ENV)
SECRET_KEY = os.getenv("SECRET_KEY", "hr2137-bot-secret-key-change-in-production")
SESSION_COOKIE_NAME = "hr2137_session"
SESSION_MAX_AGE = 86400  # 24 часа

# Создаем сериализатор для подписи cookies
serializer = URLSafeTimedSerializer(SECRET_KEY)

def create_session_token() -> str:
    """Создает токен сессии"""
    return serializer.dumps({"authenticated": True})

def verify_session_token(token: str) -> bool:
    """Проверяет токен сессии"""
    try:
        data = serializer.loads(token, max_age=SESSION_MAX_AGE)
        return data.get("authenticated", False)
    except (BadSignature, SignatureExpired):
        return False

def is_authenticated(request: StarletteRequest) -> bool:
    """Проверяет, аутентифицирован ли пользователь"""
    session_token = request.cookies.get(SESSION_COOKIE_NAME)
    if not session_token:
        return False
    return verify_session_token(session_token)

# Список путей, которые не требуют аутентификации
PUBLIC_PATHS = ["/login", "/static", "/webhook", "/api/test/query"]  # /api/test/query может быть публичным для тестирования

# Middleware для проверки аутентификации
class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: StarletteRequest, call_next):
        # Проверяем, нужна ли аутентификация для этого пути
        path = request.url.path
        
        # Пропускаем публичные пути
        if any(path.startswith(public) for public in PUBLIC_PATHS):
            return await call_next(request)
        
        # Проверяем аутентификацию для всех остальных путей
        if not is_authenticated(request):
            if path.startswith("/api/"):
                # Для API возвращаем JSON ошибку
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"error": "Unauthorized"}
                )
            else:
                # Для HTML страниц редиректим на логин
                return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
        
        return await call_next(request)

app.add_middleware(AuthMiddleware)

# Статические файлы
static_dir = Path("dashboard_static")
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Templates
templates_dir = Path("templates")
templates = Jinja2Templates(directory=str(templates_dir))

# ===================== AUTH ROUTES =====================

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Страница входа"""
    # Если уже аутентифицирован, редирект на главную
    if is_authenticated(request):
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse("login.html", {"request": request, "title": "Вход"})

@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    """Обработка входа"""
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        # Создаем токен сессии
        session_token = create_session_token()
        # Создаем ответ с редиректом
        response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
        # Устанавливаем cookie с токеном
        response.set_cookie(
            key=SESSION_COOKIE_NAME,
            value=session_token,
            max_age=SESSION_MAX_AGE,
            httponly=True,
            secure=False,  # В продакшене с HTTPS установите True
            samesite="lax"
        )
        logger.info("User authenticated successfully")
        return response
    else:
        # Неверные учетные данные
        logger.warning(f"Failed login attempt for username: {username}")
        error_msg = "Неверный логин или пароль"
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "title": "Вход",
                "error": error_msg
            },
            status_code=status.HTTP_401_UNAUTHORIZED
        )

@app.get("/logout")
async def logout():
    """Выход из системы"""
    response = RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    response.delete_cookie(key=SESSION_COOKIE_NAME)
    logger.info("User logged out")
    return response


# Модели данных
class VectorDBInfo(BaseModel):
    collection_name: str
    points_count: int
    vectors_count: int
    status: str


class RAGMetrics(BaseModel):
    precision_at_k_regulated: float
    precision_at_k_general: float
    precision_at_k_overall: float
    mrr_overall: float
    groundedness_overall: float
    halucination_rate_overall: float
    timestamp: str
    total_questions: int


class LLMStats(BaseModel):
    provider: str
    model: str
    confidence: float
    tokens_used: int
    query_count: int


class FileInfo(BaseModel):
    name: str
    source_url: str
    chunks_count: int
    file_type: str
    added_at: str


class RAGParameters(BaseModel):
    chunk_size: int = 500
    chunk_overlap: int = 50
    top_k: int = 10
    min_score: float = 0.3
    temperature: float = 0.7
    max_tokens: int = 2048


# Глобальные объекты
qdrant_loader: Optional[QdrantLoader] = None
rag_chain: Optional[RAGChain] = None
bot_instance = None  # Будет установлен из run_both.py для webhook

# Хранилище статусов фоновых задач
background_tasks_status: Dict[str, Dict[str, Any]] = {}


def get_qdrant_loader() -> QdrantLoader:
    """Получает singleton экземпляр QdrantLoader"""
    # Singleton автоматически вернет существующий экземпляр или создаст новый
    return QdrantLoader()


def get_rag_chain() -> RAGChain:
    """Получает singleton экземпляр RAGChain"""
    # Singleton автоматически вернет существующий экземпляр или создаст новый
    # RAGChain singleton автоматически использует тот же QdrantLoader singleton
    return RAGChain()


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Главная страница дашборда"""
    html_path = static_dir / "index.html"
    if html_path.exists():
        return FileResponse(html_path)
    else:
        return HTMLResponse(content=get_default_html(), status_code=200)


@app.post("/webhook")
async def telegram_webhook(request: Request):
    """
    Webhook endpoint для получения обновлений от Telegram.
    Используется на Railway для работы бота.
    """
    global bot_instance
    
    if not bot_instance:
        raise HTTPException(status_code=503, detail="Bot not initialized")
    
    try:
        from aiogram.types import Update
        update_data = await request.json()
        update = Update(**update_data)
        await bot_instance.dp.feed_update(bot_instance.bot, update)
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/vectordb/info")
async def get_vectordb_info() -> VectorDBInfo:
    """Получает информацию о векторной БД"""
    try:
        loader = get_qdrant_loader()
        info = loader.get_collection_info()
        # Преобразуем name в collection_name для модели
        if "name" in info:
            info["collection_name"] = info.pop("name")
        return VectorDBInfo(**info)
    except Exception as e:
        logger.error(f"Error getting vectordb info: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/vectordb/sources")
async def get_sources() -> List[Dict[str, Any]]:
    """Получает список всех источников в векторной БД"""
    try:
        loader = get_qdrant_loader()
        # Получаем все точки для анализа источников
        scroll_result = loader.client.scroll(
            collection_name=loader.collection_name,
            limit=10000,
            with_payload=True,
            with_vectors=False
        )
        points = scroll_result[0]
        
        # Группируем по источникам
        sources_map = {}
        for point in points:
            source_url = point.payload.get("source_url", "unknown")
            if source_url not in sources_map:
                sources_map[source_url] = {
                    "source_url": source_url,
                    "chunks_count": 0,
                    "file_name": point.payload.get("file_name", ""),
                    "document_type": point.payload.get("document_type", ""),
                    "first_seen": point.payload.get("chunk_index", 0)
                }
            sources_map[source_url]["chunks_count"] += 1
        
        return list(sources_map.values())
    except Exception as e:
        logger.error(f"Error getting sources: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/metrics/latest")
async def get_latest_metrics() -> Optional[RAGMetrics]:
    """Получает последние метрики оценки"""
    try:
        # Ищем последний файл с результатами
        results_dir = Path(".")
        result_files = sorted(
            results_dir.glob("evaluation_results_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        
        if not result_files:
            return None
        
        latest_file = result_files[0]
        with open(latest_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # JSON файл имеет структуру {"summary": {...}, "results": [...]}
        # Извлекаем summary для модели
        if "summary" in data:
            summary_data = data["summary"]
        else:
            # Если структура плоская, используем напрямую
            summary_data = data
        
        return RAGMetrics(**summary_data)
    except Exception as e:
        logger.error(f"Error getting latest metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/metrics/history")
async def get_metrics_history() -> List[Dict[str, Any]]:
    """Получает историю метрик"""
    try:
        results_dir = Path(".")
        result_files = sorted(
            results_dir.glob("evaluation_results_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        
        history = []
        for result_file in result_files[:20]:  # Последние 20
            try:
                with open(result_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                # Извлекаем summary если есть
                summary_data = data.get("summary", data)
                
                history.append({
                    "timestamp": summary_data.get("timestamp", ""),
                    "file": result_file.name,
                    "precision_at_k_overall": summary_data.get("precision_at_k_overall", 0),
                    "mrr_overall": summary_data.get("mrr_overall", 0),
                    "groundedness_overall": summary_data.get("groundedness_overall", 0),
                    "halucination_rate_overall": summary_data.get("halucination_rate_overall", 0),
                })
            except Exception as e:
                logger.warning(f"Error reading {result_file}: {str(e)}")
                continue
        
        return history
    except Exception as e:
        logger.error(f"Error getting metrics history: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


def process_file_upload(file_path: str, file_ext: str, source_url: str, task_id: str):
    """Фоновая задача для загрузки файла в векторную БД"""
    try:
        background_tasks_status[task_id] = {
            "status": "processing",
            "message": "Загрузка файла в векторную БД...",
            "progress": 0
        }
        
        loader = get_qdrant_loader()
        chunks_count = 0
        
        if file_ext == '.pdf':
            chunks_count = load_pdf(str(file_path), source_url, qdrant_loader=loader)
        elif file_ext in ['.xlsx', '.xls']:
            price_loader = PriceListLoader(str(file_path), loader)
            chunks_count = price_loader.load()
        else:
            background_tasks_status[task_id] = {
                "status": "error",
                "message": f"Неподдерживаемый тип файла: {file_ext}",
                "progress": 100
            }
            return
        
        background_tasks_status[task_id] = {
            "status": "completed",
            "message": f"Успешно загружено {chunks_count} чанков",
            "progress": 100,
            "chunks_count": chunks_count,
            "source_url": source_url
        }
        
        logger.info(f"File upload completed: {file_path}, chunks: {chunks_count}")
    except Exception as e:
        logger.error(f"Error processing file upload: {str(e)}")
        background_tasks_status[task_id] = {
            "status": "error",
            "message": f"Ошибка: {str(e)}",
            "progress": 100
        }


@app.post("/api/workflow/load-pdf")
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """Загружает файл (PDF или Excel) в векторную БД (асинхронно)"""
    try:
        import uuid
        task_id = str(uuid.uuid4())
        
        # Сохраняем файл во временную директорию
        media_dir = Path("media")
        media_dir.mkdir(exist_ok=True)
        
        file_path = media_dir / file.filename
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        file_ext = file_path.suffix.lower()
        source_url = f"file://media/{file.filename}"
        
        if file_ext not in ['.pdf', '.xlsx', '.xls']:
            raise HTTPException(status_code=400, detail=f"Неподдерживаемый тип файла: {file_ext}")
        
        # Инициализируем статус задачи
        background_tasks_status[task_id] = {
            "status": "pending",
            "message": "Файл сохранен, ожидание обработки...",
            "progress": 0
        }
        
        # Запускаем фоновую задачу
        background_tasks.add_task(process_file_upload, str(file_path), file_ext, source_url, task_id)
        
        return {
            "success": True,
            "task_id": task_id,
            "filename": file.filename,
            "message": "Файл принят, обработка началась",
            "status_url": f"/api/workflow/task-status/{task_id}"
        }
    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/workflow/task-status/{task_id}")
async def get_task_status(task_id: str):
    """Получает статус фоновой задачи"""
    if task_id not in background_tasks_status:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return background_tasks_status[task_id]


@app.post("/api/workflow/evaluate")
async def run_evaluation():
    """Запускает оценку RAG системы"""
    try:
        # Загружаем Ground-Truth QA
        gt_path = Path("ground_truth_qa.json")
        if not gt_path.exists():
            raise HTTPException(status_code=404, detail="ground_truth_qa.json not found")
        
        with open(gt_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        qa_list = []
        for qa_data in data.get("ground_truth_qa", []):
            qa = GroundTruthQA(
                question=qa_data["question"],
                expected_answer=qa_data["expected_answer"],
                category=qa_data["category"],
                expected_sources=qa_data.get("expected_sources", []),
                key_facts=qa_data.get("key_facts", [])
            )
            qa_list.append(qa)
        
        # Запускаем оценку с использованием существующего RAG chain
        # чтобы избежать создания нового QdrantLoader
        rag_chain_instance = get_rag_chain()
        evaluator = RAGEvaluator(rag_chain=rag_chain_instance)
        summary = await evaluator.evaluate(qa_list, k=5)
        
        # Сохраняем результаты
        output_file = f"evaluation_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        evaluator.save_results(summary, output_file)
        
        await evaluator.close()
        
        return {
            "success": True,
            "output_file": output_file,
            "metrics": {
                "precision_at_k_overall": summary.precision_at_k_overall,
                "mrr_overall": summary.mrr_overall,
                "groundedness_overall": summary.groundedness_overall,
                "halucination_rate_overall": summary.halucination_rate_overall,
            }
        }
    except Exception as e:
        logger.error(f"Error running evaluation: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


def process_scraping(task_id: str):
    """Фоновая задача для скрапинга сайтов"""
    try:
        background_tasks_status[task_id] = {
            "status": "processing",
            "message": "Начало скрапинга сайтов...",
            "progress": 0
        }
        
        from scraper import scrape_whitelist_urls
        
        loader = get_qdrant_loader()
        whitelist_urls = loader.whitelist.get_allowed_urls()
        
        # Запускаем скрапинг (синхронно, но в фоне)
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loaded_count = loop.run_until_complete(
            scrape_whitelist_urls(whitelist_urls, qdrant_loader=loader, max_pages=20)
        )
        loop.close()
        
        background_tasks_status[task_id] = {
            "status": "completed",
            "message": f"Скрапинг завершен. Загружено {loaded_count} страниц",
            "progress": 100,
            "pages_loaded": loaded_count
        }
    except Exception as e:
        logger.error(f"Error processing scraping: {str(e)}")
        background_tasks_status[task_id] = {
            "status": "error",
            "message": f"Ошибка: {str(e)}",
            "progress": 100
        }


@app.post("/api/workflow/scrape")
async def scrape_website(background_tasks: BackgroundTasks):
    """Запускает скрапинг сайтов из whitelist (асинхронно)"""
    try:
        import uuid
        task_id = str(uuid.uuid4())
        
        # Инициализируем статус задачи
        background_tasks_status[task_id] = {
            "status": "pending",
            "message": "Ожидание начала скрапинга...",
            "progress": 0
        }
        
        # Запускаем фоновую задачу
        background_tasks.add_task(process_scraping, task_id)
        
        return {
            "success": True,
            "task_id": task_id,
            "message": "Скрапинг начат",
            "status_url": f"/api/workflow/task-status/{task_id}"
        }
    except Exception as e:
        logger.error(f"Error scraping websites: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/vectordb/sources/{source_url:path}")
async def delete_source(source_url: str):
    """Удаляет все документы с указанным source_url"""
    try:
        loader = get_qdrant_loader()
        
        # Декодируем URL (может быть закодирован)
        import urllib.parse
        source_url = urllib.parse.unquote(source_url)
        
        # Создаем фильтр для удаления всех точек с этим source_url
        delete_filter = Filter(
            must=[
                FieldCondition(
                    key="source_url",
                    match=MatchValue(value=source_url)
                )
            ]
        )
        
        # Получаем все точки с этим source_url для подсчета
        scroll_result = loader.client.scroll(
            collection_name=loader.collection_name,
            scroll_filter=delete_filter,
            limit=10000,
            with_payload=False,
            with_vectors=False
        )
        points_to_delete = scroll_result[0]
        points_count = len(points_to_delete)
        
        if points_count == 0:
            return {
                "success": False,
                "message": f"Источник {source_url} не найден"
            }
        
        # Удаляем точки
        point_ids = [point.id for point in points_to_delete]
        loader.client.delete(
            collection_name=loader.collection_name,
            points_selector=point_ids
        )
        
        # Помечаем BM25 индекс для перестроения
        loader._bm25_needs_rebuild = True
        
        logger.info(f"Deleted {points_count} points with source_url: {source_url}")
        
        return {
            "success": True,
            "deleted_points": points_count,
            "source_url": source_url
        }
    except Exception as e:
        logger.error(f"Error deleting source: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/test/query")
async def test_query(query: str):
    """Тестовый запрос к RAG системе"""
    try:
        chain = get_rag_chain()
        result = await chain.query(query)
        
        return {
            "query": query,
            "answer": result.get("answer", ""),
            "sources": result.get("sources", []),
            "provider": result.get("provider", ""),
            "model": result.get("model", ""),
            "confidence": result.get("confidence", 0),
            "context_count": result.get("context_count", 0),
        }
    except Exception as e:
        logger.error(f"Error testing query: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/parameters")
async def get_parameters():
    """Получает текущие параметры RAG"""
    try:
        import yaml
        config_path = Path("config.yaml")
        if not config_path.exists():
            raise HTTPException(status_code=404, detail="config.yaml not found")
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        rag_config = config.get("rag", {})
        llm_config = config.get("llm", {})
        primary_config = llm_config.get("primary", {})
        
        return {
            "chunk_size": rag_config.get("chunk_size", 500),
            "chunk_overlap": rag_config.get("chunk_overlap", 50),
            "top_k": rag_config.get("top_k", 10),
            "min_score": rag_config.get("min_score", 0.3),
            "temperature": primary_config.get("temperature", 0.7),
            "max_tokens": primary_config.get("max_tokens", 2048),
        }
    except Exception as e:
        logger.error(f"Error getting parameters: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/parameters")
async def update_parameters(params: RAGParameters):
    """Обновляет параметры RAG (временно, без сохранения в config.yaml)"""
    try:
        chain = get_rag_chain()
        loader = get_qdrant_loader()
        
        # Обновляем параметры в RAGChain (если они доступны для изменения)
        # Примечание: некоторые параметры требуют перезагрузки документов
        chain.top_k = params.top_k
        chain.min_score = params.min_score
        
        # Обновляем параметры в QdrantLoader
        loader.chunk_size = params.chunk_size
        loader.chunk_overlap = params.chunk_overlap
        
        # Обновляем параметры LLM (если доступны)
        if chain.llm_client:
            # Температура и max_tokens передаются при каждом запросе
            # Сохраняем их для использования
            chain._temp_temperature = params.temperature
            chain._temp_max_tokens = params.max_tokens
        
        logger.info(f"Parameters updated: chunk_size={params.chunk_size}, "
                   f"chunk_overlap={params.chunk_overlap}, top_k={params.top_k}, "
                   f"min_score={params.min_score}, temperature={params.temperature}, "
                   f"max_tokens={params.max_tokens}")
        
        return {
            "status": "success",
            "message": "Parameters updated (temporary, not saved to config.yaml)",
            "parameters": {
                "chunk_size": params.chunk_size,
                "chunk_overlap": params.chunk_overlap,
                "top_k": params.top_k,
                "min_score": params.min_score,
                "temperature": params.temperature,
                "max_tokens": params.max_tokens,
            }
        }
    except Exception as e:
        logger.error(f"Error updating parameters: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


def get_default_html() -> str:
    """Возвращает HTML по умолчанию если файл не найден"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>RAG Dashboard</title>
        <meta charset="utf-8">
    </head>
    <body>
        <h1>Dashboard HTML file not found</h1>
        <p>Please create dashboard_static/index.html</p>
    </body>
    </html>
    """


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


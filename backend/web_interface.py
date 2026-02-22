"""
Web Interface for Demonstration
FastAPI веб-интерфейс для демонстрации функционала инвесторам
"""
import os
import sys
import logging
from typing import Optional, TYPE_CHECKING
from datetime import datetime
from pathlib import Path

# Добавляем корневую директорию проекта в sys.path для импорта модулей
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

if TYPE_CHECKING:
    from services.rag.rag_chain import RAGChain

from fastapi import FastAPI, Request, Form, HTTPException, UploadFile, File, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
import uvicorn

log = logging.getLogger()

# ===================== CONFIGURATION =====================
WEB_INTERFACE_PORT = int(os.getenv("WEB_INTERFACE_PORT", 8081))

# FastAPI app
app = FastAPI(title="HR2137 Bot Demo Interface", version="1.0.0")

# CORS middleware для работы с Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В production укажите конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Templates
templates = Jinja2Templates(directory="templates")

# ===================== AUTHENTICATION =====================
# Учетные данные для входа
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin"

# Секретный ключ для подписи cookies (в продакшене используйте случайный ключ из ENV)
SECRET_KEY = os.getenv("SECRET_KEY", "hr2137-bot-secret-key-change-in-production")
SESSION_COOKIE_NAME = "hr2137_web_session"
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
PUBLIC_PATHS = ["/login", "/static", "/health"]

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
            # Разрешаем доступ к API endpoints без аутентификации (для frontend Next.js)
            if path.startswith("/api/") or path.startswith("/demo/") or path.startswith("/rag/"):
                # Пропускаем API запросы без проверки аутентификации
                return await call_next(request)
            else:
                # Для HTML страниц редиректим на логин
                return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
        
        return await call_next(request)

app.add_middleware(AuthMiddleware)

# ===================== IMPORTS =====================
try:
    from services.rag.qdrant_helper import search_with_preview, get_collection_stats, list_documents
    from services.agents.lead_processor import generate_proposal, validate_lead, classify_request
    from services.helpers.email_helper import send_email
    # Новая RAG система
    from services.rag.rag_chain import RAGChain
    from services.rag.qdrant_loader import QdrantLoader
    INTEGRATIONS_AVAILABLE = True
    RAG_AVAILABLE = True
except ImportError as e:
    log.warning(f"⚠️ Некоторые модули недоступны: {e}")
    INTEGRATIONS_AVAILABLE = False
    RAG_AVAILABLE = False

# Глобальный экземпляр RAGChain (Singleton)
_rag_chain_instance = None

def get_rag_chain():
    """Получить экземпляр RAGChain (Singleton)"""
    global _rag_chain_instance
    if not RAG_AVAILABLE:
        return None
    if _rag_chain_instance is None:
        try:
            from services.rag.rag_chain import RAGChain
            _rag_chain_instance = RAGChain()
        except Exception as e:
            log.error(f"❌ Ошибка инициализации RAGChain: {e}")
            return None
    return _rag_chain_instance

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
        log.info("User authenticated successfully")
        return response
    else:
        # Неверные учетные данные
        log.warning(f"Failed login attempt for username: {username}")
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
    log.info("User logged out")
    return response

# ===================== ROUTES =====================

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Главная страница"""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "title": "HR2137 Bot - Демонстрационный интерфейс"
    })

@app.get("/rag", response_class=HTMLResponse)
async def rag_dashboard(request: Request):
    """RAG Dashboard - управление базой знаний"""
    return templates.TemplateResponse("rag_dashboard.html", {
        "request": request,
        "title": "HR2137 RAG Dashboard"
    })

@app.get("/architecture", response_class=HTMLResponse)
async def architecture(request: Request):
    """Страница с архитектурой системы"""
    return templates.TemplateResponse("architecture.html", {
        "request": request,
        "title": "Архитектура системы"
    })

@app.post("/demo/email")
async def demo_email(
    recipient: str = Form(...),
    subject: str = Form(...),
    body: str = Form(...)
):
    """Отправка тестового email для демонстрации"""
    if not INTEGRATIONS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Email модуль недоступен")
    
    try:
        success = await send_email(
            to_email=recipient,
            subject=subject,
            body=body,
            is_html=False
        )
        
        if success:
            return JSONResponse({
                "status": "success",
                "message": f"Email отправлен на {recipient}",
                "timestamp": datetime.now().isoformat()
            })
        else:
            raise HTTPException(status_code=500, detail="Ошибка отправки email")
    except Exception as e:
        log.error(f"❌ Ошибка отправки email: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/demo/proposal")
async def demo_proposal(request_data: dict):
    """Генерация КП для демонстрации"""
    if not INTEGRATIONS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Модуль генерации КП недоступен")
    
    lead_request = request_data.get("request", "")
    if not lead_request:
        raise HTTPException(status_code=400, detail="Поле 'request' обязательно")
    
    try:
        # Классификация запроса
        classification = await classify_request(lead_request)
        
        # Валидация лида
        validation = await validate_lead(lead_request)
        
        # Генерация КП
        proposal = await generate_proposal(lead_request, lead_contact={})
        
        return JSONResponse({
            "status": "success",
            "classification": classification,
            "validation": validation,
            "proposal": proposal,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        log.error(f"❌ Ошибка генерации КП: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ===================== RAG WORKFLOW ENDPOINTS =====================

@app.post("/rag/workflow/evaluate")
async def rag_evaluate():
    """Запуск оценки RAG системы (evaluation)"""
    if not RAG_AVAILABLE:
        raise HTTPException(status_code=503, detail="RAG система недоступна")
    
    try:
        from rag_evaluator import RAGEvaluator, GroundTruthQA
        from pathlib import Path
        import json
        
        # Загружаем Ground-Truth QA (если есть)
        gt_path = Path("ground_truth_qa.json")
        if not gt_path.exists():
            return JSONResponse({
                "status": "error",
                "message": "ground_truth_qa.json не найден. Создайте файл с тестовыми вопросами."
            }, status_code=404)
        
        with open(gt_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        qa_list = []
        for qa_data in data.get("ground_truth_qa", []):
            qa = GroundTruthQA(
                question=qa_data["question"],
                expected_answer=qa_data["expected_answer"],
                category=qa_data.get("category", "general"),
                expected_sources=qa_data.get("expected_sources", []),
                key_facts=qa_data.get("key_facts", [])
            )
            qa_list.append(qa)
        
        if not qa_list:
            return JSONResponse({
                "status": "error",
                "message": "Нет вопросов в ground_truth_qa.json"
            }, status_code=400)
        
        # Запускаем оценку
        rag = get_rag_chain()
        if not rag:
            raise HTTPException(status_code=503, detail="Не удалось инициализировать RAG")
        
        evaluator = RAGEvaluator(rag_chain=rag)
        summary = await evaluator.evaluate(qa_list, k=5)
        
        # Сохраняем результаты
        output_file = f"evaluation_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        evaluator.save_results(summary, output_file)
        await evaluator.close()
        
        return JSONResponse({
            "status": "success",
            "output_file": output_file,
            "summary": {
                "total_questions": summary.total_questions,
                "precision_at_k_regulated": summary.precision_at_k_regulated,
                "precision_at_k_general": summary.precision_at_k_general,
                "precision_at_k_overall": summary.precision_at_k_overall,
                "mrr_overall": summary.mrr_overall,
                "groundedness_overall": summary.groundedness_overall,
                "halucination_rate_overall": summary.halucination_rate_overall,
                "timestamp": summary.timestamp
            }
        })
    except Exception as e:
        log.error(f"❌ Ошибка оценки RAG: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/rag/workflow/load-pdf")
async def rag_load_pdf(file: UploadFile = File(...)):
    """Загрузка PDF файла в RAG базу знаний"""
    if not RAG_AVAILABLE:
        raise HTTPException(status_code=503, detail="RAG система недоступна")
    
    from pathlib import Path
    from load_pdf import load_pdf
    
    if not file:
        raise HTTPException(status_code=400, detail="Файл не предоставлен")
    
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Поддерживаются только PDF файлы")
    
    try:
        # Сохраняем файл во временную директорию
        media_dir = Path("media")
        media_dir.mkdir(exist_ok=True)
        
        file_path = media_dir / file.filename
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        source_url = f"file://media/{file.filename}"
        loader = QdrantLoader()
        chunks_count = load_pdf(str(file_path), source_url, qdrant_loader=loader)
        
        return JSONResponse({
            "status": "success",
            "filename": file.filename,
            "chunks_count": chunks_count,
            "source_url": source_url,
            "message": f"Загружено {chunks_count} чанков"
        })
    except Exception as e:
        log.error(f"❌ Ошибка загрузки PDF: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/rag/workflow/scrape")
async def rag_scrape():
    """Скрапинг сайтов из whitelist для загрузки в RAG"""
    if not RAG_AVAILABLE:
        raise HTTPException(status_code=503, detail="RAG система недоступна")
    
    try:
        from scraper import scrape_whitelist_urls
        
        loader = QdrantLoader()
        whitelist_urls = loader.whitelist.get_allowed_urls()
        web_urls = [url for url in whitelist_urls if url.startswith("http")]
        
        if not web_urls:
            return JSONResponse({
                "status": "warning",
                "message": "Нет веб-URL в whitelist для скрапинга"
            })
        
        loaded_count = await scrape_whitelist_urls(web_urls, qdrant_loader=loader, max_pages=20)
        
        return JSONResponse({
            "status": "success",
            "pages_loaded": loaded_count,
            "urls_processed": len(web_urls),
            "message": f"Загружено {loaded_count} страниц"
        })
    except Exception as e:
        log.error(f"❌ Ошибка скрапинга: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/rag/metrics/latest")
async def rag_metrics_latest():
    """Получение последних метрик оценки"""
    from pathlib import Path
    import json
    
    try:
        results_dir = Path(".")
        result_files = sorted(
            results_dir.glob("evaluation_results_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        
        if not result_files:
            return JSONResponse({
                "status": "not_found",
                "message": "Метрики не найдены. Запустите оценку через /rag/workflow/evaluate"
            })
        
        latest_file = result_files[0]
        with open(latest_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        summary_data = data.get("summary", data)
        
        return JSONResponse({
            "status": "success",
            "file": latest_file.name,
            "metrics": summary_data
        })
    except Exception as e:
        log.error(f"❌ Ошибка получения метрик: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/rag/search")
async def rag_search(query: str, limit: int = 5):
    """Поиск в RAG базе знаний (старый метод для совместимости)"""
    if not INTEGRATIONS_AVAILABLE:
        raise HTTPException(status_code=503, detail="RAG модуль недоступен")
    
    try:
        results = await search_with_preview(query, limit=limit)
        return JSONResponse(results)
    except Exception as e:
        log.error(f"❌ Ошибка поиска в RAG: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/rag/query")
async def rag_query(request_data: dict):
    """Полноценный RAG запрос с генерацией ответа через LLM"""
    if not RAG_AVAILABLE:
        raise HTTPException(status_code=503, detail="RAG система недоступна")
    
    user_query = request_data.get("query", "")
    if not user_query:
        raise HTTPException(status_code=400, detail="Поле 'query' обязательно")
    
    # Проверяем, является ли запрос запросом о ценах
    is_pricing_query = any(kw in user_query.lower() for kw in [
        "цена", "стоимость", "стоит", "рублей", "руб", "прайс", "сколько",
        "коммерческое предложение", "кп", "расценки", "тарифы"
    ])
    
    # Если это запрос о ценах, используем LangGraph
    if is_pricing_query:
        try:
            from rag_langgraph import query_with_langgraph
            log.info("💰 Используем LangGraph RAG для запроса о ценах")
            
            thread_id = request_data.get("thread_id", "default")
            result = await query_with_langgraph(user_query, thread_id=thread_id)
            
            return JSONResponse({
                "status": "success",
                "query": user_query,
                "answer": result.get("answer", ""),
                "sources": result.get("sources", []),
                "query_type": result.get("query_type", "pricing"),
                "validated": result.get("validated", False),
                "validation_errors": result.get("validation_errors", []),
                "retry_count": result.get("retry_count", 0),
                "pricing_info": result.get("pricing_info", {}),
                "metadata": result.get("metadata", {}),
                "method": "langgraph",
                "timestamp": datetime.now().isoformat()
            })
        except ImportError:
            log.warning("⚠️ LangGraph не установлен, используем стандартный RAG")
        except Exception as e:
            log.error(f"❌ Ошибка LangGraph RAG: {e}")
            # Fallback на стандартный RAG
    
    # Стандартный RAG для не-ценовых запросов или fallback
    top_k = request_data.get("top_k", 5)
    min_score = request_data.get("min_score", None)
    
    # AnythingLLM: при включённом флаге — запрос к workspace API вместо RAGChain
    try:
        from services.integrations.anythingllm_client import (
            use_anythingllm_rag,
            is_configured,
            chat_with_workspace_env,
        )
        if use_anythingllm_rag() and is_configured():
            log.info("🔍 [AnythingLLM] /rag/query через workspace API")
            answer, sources_list = await chat_with_workspace_env(message=user_query, history=None)
            sources = [
                s.get("content") or s.get("text") or str(s)
                for s in (sources_list or [])
                if isinstance(s, dict)
            ]
            return JSONResponse({
                "status": "success",
                "query": user_query,
                "answer": answer or "",
                "sources": sources,
                "context_count": len(sources),
                "provider": "anythingllm",
                "model": "",
                "confidence": 0.0,
                "tokens_used": 0,
                "error": None,
                "method": "anythingllm",
                "timestamp": datetime.now().isoformat()
            })
    except Exception as anythingllm_err:
        log.warning("⚠️ [AnythingLLM] /rag/query ошибка: %s, fallback на RAGChain", anythingllm_err)
    
    try:
        rag = get_rag_chain()
        if not rag:
            raise HTTPException(status_code=503, detail="Не удалось инициализировать RAG")
        
        result = await rag.query(
            user_query=user_query,
            use_rag=True,
            top_k=top_k,
            min_score=min_score
        )
        
        return JSONResponse({
            "status": "success",
            "query": user_query,
            "answer": result.get("answer", ""),
            "sources": result.get("sources", []),
            "context_count": result.get("context_count", 0),
            "provider": result.get("provider", ""),
            "model": result.get("model", ""),
            "confidence": result.get("confidence", 0.0),
            "tokens_used": result.get("tokens_used", 0),
            "error": result.get("error"),
            "method": "standard",
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        log.error(f"❌ Ошибка RAG запроса: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/rag/test")
async def rag_test(query: str = "Что такое HR консалтинг?", top_k: int = 5):
    """Тестовый RAG запрос через GET (для удобства)"""
    if not RAG_AVAILABLE:
        raise HTTPException(status_code=503, detail="RAG система недоступна")
    
    try:
        rag = get_rag_chain()
        if not rag:
            raise HTTPException(status_code=503, detail="Не удалось инициализировать RAG")
        
        result = await rag.query(
            user_query=query,
            use_rag=True,
            top_k=top_k
        )
        
        return JSONResponse({
            "status": "success",
            "query": query,
            "answer": result.get("answer", ""),
            "sources": result.get("sources", []),
            "context_count": result.get("context_count", 0),
            "provider": result.get("provider", ""),
            "model": result.get("model", ""),
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        log.error(f"❌ Ошибка тестового RAG запроса: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/rag/stats")
async def rag_stats():
    """Статистика RAG базы знаний"""
    if not INTEGRATIONS_AVAILABLE:
        raise HTTPException(status_code=503, detail="RAG модуль недоступен")
    
    try:
        # Используем новый QdrantLoader для получения статистики
        if RAG_AVAILABLE:
            try:
                loader = QdrantLoader()
                info = loader.get_collection_info()
                return JSONResponse({
                    "collection_name": info.get("name", ""),
                    "points_count": info.get("points_count", 0),
                    "vectors_count": info.get("vectors_count", 0),
                    "status": info.get("status", "unknown"),
                    "source": "qdrant_loader"
                })
            except Exception as e:
                log.warning(f"⚠️ Ошибка получения статистики через QdrantLoader: {e}, пробую старый метод")
        
        # Fallback на старый метод
        stats = await get_collection_stats()
        return JSONResponse(stats)
    except Exception as e:
        log.error(f"❌ Ошибка получения статистики: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/rag/docs")
async def rag_docs(limit: int = 50):
    """Список документов в базе знаний"""
    if not INTEGRATIONS_AVAILABLE:
        raise HTTPException(status_code=503, detail="RAG модуль недоступен")
    
    try:
        docs = await list_documents(limit=limit)
        return JSONResponse({
            "total": len(docs),
            "documents": docs
        })
    except Exception as e:
        log.error(f"❌ Ошибка получения списка документов: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/rag/parameters")
async def rag_get_parameters():
    """Получение текущих параметров RAG"""
    try:
        import yaml
        from pathlib import Path
        
        config_path = Path("config.yaml")
        if not config_path.exists():
            return JSONResponse({
                "status": "error",
                "message": "config.yaml не найден"
            }, status_code=404)
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        rag_config = config.get("rag", {})
        llm_config = config.get("llm", {})
        primary_config = llm_config.get("primary", {})
        
        return JSONResponse({
            "status": "success",
            "parameters": {
                "chunk_size": rag_config.get("chunk_size", 500),
                "chunk_overlap": rag_config.get("chunk_overlap", 50),
                "top_k": rag_config.get("top_k", 10),
                "min_score": rag_config.get("min_score", 0.3),
                "temperature": primary_config.get("temperature", 0.7),
                "max_tokens": primary_config.get("max_tokens", 2048),
            }
        })
    except Exception as e:
        log.error(f"❌ Ошибка получения параметров: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/rag/parameters")
async def rag_update_parameters(params: dict):
    """Обновление параметров RAG (временно, без сохранения в config.yaml)"""
    if not RAG_AVAILABLE:
        raise HTTPException(status_code=503, detail="RAG система недоступна")
    
    try:
        rag = get_rag_chain()
        if not rag:
            raise HTTPException(status_code=503, detail="Не удалось инициализировать RAG")
        
        loader = QdrantLoader()
        
        # Обновляем параметры
        if "top_k" in params:
            rag.top_k = params["top_k"]
        if "min_score" in params:
            rag.min_score = params["min_score"]
        if "chunk_size" in params:
            loader.chunk_size = params["chunk_size"]
        if "chunk_overlap" in params:
            loader.chunk_overlap = params["chunk_overlap"]
        if "temperature" in params:
            rag._temp_temperature = params["temperature"]
        if "max_tokens" in params:
            rag._temp_max_tokens = params["max_tokens"]
        
        return JSONResponse({
            "status": "success",
            "message": "Параметры обновлены (временно, не сохранены в config.yaml)",
            "parameters": {
                "chunk_size": loader.chunk_size,
                "chunk_overlap": loader.chunk_overlap,
                "top_k": rag.top_k,
                "min_score": rag.min_score,
                "temperature": rag._temp_temperature or 0.7,
                "max_tokens": rag._temp_max_tokens or 2048,
            }
        })
    except Exception as e:
        log.error(f"❌ Ошибка обновления параметров: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    """Проверка здоровья сервиса"""
    rag_status = "unavailable"
    if RAG_AVAILABLE:
        try:
            rag = get_rag_chain()
            rag_status = "available" if rag else "initialization_failed"
        except:
            rag_status = "error"
    
    return JSONResponse({
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "integrations_available": INTEGRATIONS_AVAILABLE,
        "rag_system": rag_status
    })


# ==================== NOTIFICATIONS API ====================

# In-memory хранилище уведомлений (можно заменить на Redis или БД)
_notifications_store: dict = {}  # {user_id: [notifications]}

def _get_user_notifications(user_id: str) -> list:
    """Получить уведомления пользователя"""
    return _notifications_store.get(user_id, [])

def _add_notification(user_id: str, notification: dict):
    """Добавить уведомление"""
    if user_id not in _notifications_store:
        _notifications_store[user_id] = []
    
    if "id" not in notification:
        notification["id"] = f"{user_id}_{datetime.now().timestamp()}"
    if "created_at" not in notification:
        notification["created_at"] = datetime.now().isoformat()
    if "read" not in notification:
        notification["read"] = False
    
    _notifications_store[user_id].append(notification)
    if len(_notifications_store[user_id]) > 50:
        _notifications_store[user_id] = _notifications_store[user_id][-50:]

@app.get("/notifications")
async def get_notifications(user_id: str = None, limit: int = 20):
    """Получить список уведомлений для пользователя"""
    try:
        if not user_id:
            raise HTTPException(status_code=400, detail="user_id обязателен")
        
        notifications = _get_user_notifications(user_id)
        unread_count = sum(1 for n in notifications if not n.get("read", False))
        
        sorted_notifications = sorted(
            notifications,
            key=lambda x: x.get("created_at", ""),
            reverse=True
        )[:limit]
        
        return JSONResponse({
            "notifications": sorted_notifications,
            "unread_count": unread_count,
            "total": len(notifications)
        })
    except Exception as e:
        log.error(f"❌ Ошибка в /notifications: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/notifications/unread-count")
async def get_unread_notification_count(user_id: str = None):
    """Получить количество непрочитанных уведомлений"""
    try:
        if not user_id:
            raise HTTPException(status_code=400, detail="user_id обязателен")
        
        notifications = _get_user_notifications(user_id)
        unread_count = sum(1 for n in notifications if not n.get("read", False))
        
        return JSONResponse({
            "unread_count": unread_count,
            "user_id": user_id
        })
    except Exception as e:
        log.error(f"❌ Ошибка в /notifications/unread-count: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/notifications/mark-read")
async def mark_notification_read(request_data: dict):
    """Отметить уведомление как прочитанное"""
    try:
        user_id = request_data.get("user_id")
        notification_id = request_data.get("notification_id")
        
        if not user_id:
            raise HTTPException(status_code=400, detail="user_id обязателен")
        
        notifications = _get_user_notifications(user_id)
        
        if notification_id:
            for notification in notifications:
                if notification.get("id") == notification_id:
                    notification["read"] = True
                    notification["read_at"] = datetime.now().isoformat()
                    break
        else:
            for notification in notifications:
                notification["read"] = True
                notification["read_at"] = datetime.now().isoformat()
        
        return JSONResponse({
            "success": True,
            "message": "Уведомление отмечено как прочитанное"
        })
    except Exception as e:
        log.error(f"❌ Ошибка в /notifications/mark-read: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/notifications/hrtime")
async def create_hrtime_notification(request_data: dict):
    """Создать уведомление из HRTime заказа"""
    try:
        user_id = request_data.get("user_id")
        order_id = request_data.get("order_id")
        order_data = request_data.get("order_data", {})
        
        if not user_id:
            raise HTTPException(status_code=400, detail="user_id обязателен")
        if not order_id:
            raise HTTPException(status_code=400, detail="order_id обязателен")
        
        client_name = order_data.get("client_name", "Неизвестно")
        client_email = order_data.get("client_email", "")
        score = order_data.get("score", 0)
        category = order_data.get("category", "")
        
        notification = {
            "type": "hrtime",
            "title": f"🔥 Новый заказ HR Time #{order_id}",
            "message": f"Клиент: {client_name}" + (f" | Email: {client_email}" if client_email else ""),
            "action_url": f"/projects?order={order_id}",
            "metadata": {
                "order_id": order_id,
                "score": score,
                "category": category,
                "client_name": client_name,
                "client_email": client_email
            }
        }
        
        _add_notification(user_id, notification)
        log.info(f"✅ Создано уведомление HRTime для пользователя {user_id}, заказ {order_id}")
        
        return JSONResponse({
            "success": True,
            "notification": notification
        })
    except Exception as e:
        log.error(f"❌ Ошибка в /notifications/hrtime: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/notifications/hrtime")
async def get_hrtime_notifications(user_id: str = None, limit: int = 20):
    """Получить список уведомлений HRTime для пользователя"""
    try:
        if not user_id:
            raise HTTPException(status_code=400, detail="user_id обязателен")
        
        notifications = _get_user_notifications(user_id)
        hrtime_notifications = [
            n for n in notifications 
            if n.get("type") == "hrtime"
        ]
        
        sorted_notifications = sorted(
            hrtime_notifications,
            key=lambda x: x.get("created_at", ""),
            reverse=True
        )[:limit]
        
        return JSONResponse({
            "notifications": sorted_notifications,
            "count": len(sorted_notifications),
            "total": len(hrtime_notifications)
        })
    except Exception as e:
        log.error(f"❌ Ошибка в /notifications/hrtime: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/notifications/sync-from-telegram")
async def sync_notifications_from_telegram(request_data: dict):
    """Синхронизировать уведомления из Telegram бота с Mini App"""
    try:
        user_id = request_data.get("user_id")
        telegram_notifications = request_data.get("notifications", [])
        
        if not user_id:
            raise HTTPException(status_code=400, detail="user_id обязателен")
        
        synced_count = 0
        for tg_notification in telegram_notifications:
            # Преобразуем формат Telegram уведомления в формат Mini App
            notification = {
                "type": tg_notification.get("type", "system"),
                "title": tg_notification.get("title", "Уведомление"),
                "message": tg_notification.get("message", ""),
                "action_url": tg_notification.get("action_url"),
                "metadata": tg_notification.get("metadata", {})
            }
            
            _add_notification(user_id, notification)
            synced_count += 1
        
        log.info(f"✅ Синхронизировано {synced_count} уведомлений для пользователя {user_id}")
        
        return JSONResponse({
            "success": True,
            "synced_count": synced_count
        })
    except Exception as e:
        log.error(f"❌ Ошибка в /notifications/sync-from-telegram: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== EMAIL API ====================

@app.get("/email/unread-count")
async def get_unread_email_count(user_id: str = None):
    """Получить количество непрочитанных писем"""
    try:
        from services.helpers.email_helper import check_new_emails
        
        emails = await check_new_emails(since_days=1, limit=10)
        unread_count = len(emails) if emails else 0
        
        return JSONResponse({
            "unread_count": unread_count,
            "user_id": user_id
        })
    except Exception as e:
        log.error(f"❌ Ошибка в /email/unread-count: {e}")
        return JSONResponse({
            "unread_count": 0,
            "user_id": user_id,
            "error": str(e)
        })

@app.get("/email/recent")
async def get_recent_emails(user_id: str = None, limit: int = 10):
    """Получить последние письма"""
    try:
        from services.helpers.email_helper import check_new_emails
        
        emails = await check_new_emails(since_days=7, limit=limit)
        
        formatted_emails = []
        for email in (emails or []):
            formatted_emails.append({
                "id": email.get("id", ""),
                "subject": email.get("subject", "Без темы"),
                "from": email.get("from", "Неизвестно"),
                "date": email.get("date", ""),
                "preview": email.get("preview", "")[:100] if email.get("preview") else ""
            })
        
        # Создаем уведомления для новых писем
        if user_id and formatted_emails:
            for email in formatted_emails[:3]:
                _add_notification(user_id, {
                    "type": "email",
                    "title": f"Новое письмо: {email['subject']}",
                    "message": f"От: {email['from']}",
                    "action_url": f"/email"
                })
        
        return JSONResponse({
            "emails": formatted_emails,
            "count": len(formatted_emails)
        })
    except Exception as e:
        log.error(f"❌ Ошибка в /email/recent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== CHAT SYNC API ====================

@app.post("/chat")
async def chat_sync(request_data: dict):
    """Синхронизировать сообщение из mini app с базой данных"""
    try:
        from backend.database.message_storage import save_telegram_message
        
        message = request_data.get("message", "")
        user_id = request_data.get("user_id", "anonymous")
        platform = request_data.get("platform", "miniapp")
        
        if not message:
            raise HTTPException(status_code=400, detail="Сообщение не может быть пустым")
        
        # Сохраняем сообщение в базу данных
        try:
            user_id_int = int(user_id) if user_id != "anonymous" and str(user_id).isdigit() else None
            if user_id_int:
                save_telegram_message(
                    user_id=user_id_int,
                    chat_id=user_id_int,
                    message_id=None,
                    role="user",
                    content=message,
                    message_type="text",
                    metadata={"platform": platform},
                    save_to_redis=True,
                    save_to_postgres=True,
                    save_to_qdrant=True
                )
        except Exception as e:
            log.warning(f"⚠️ Ошибка сохранения сообщения: {e}")
        
        # Используем LangGraph workflow
        from backend.api.services import query_with_conversation_workflow
        
        result = await query_with_conversation_workflow(
            message=message,
            user_id=str(user_id),
            platform=platform
        )
        
        # Сохраняем ответ ассистента
        if user_id_int and result.get("response"):
            try:
                save_telegram_message(
                    user_id=user_id_int,
                    chat_id=user_id_int,
                    message_id=None,
                    role="assistant",
                    content=result.get("response", ""),
                    message_type="text",
                    metadata={"platform": platform},
                    save_to_redis=True,
                    save_to_postgres=True,
                    save_to_qdrant=False
                )
            except Exception as e:
                log.warning(f"⚠️ Ошибка сохранения ответа: {e}")
        
        return JSONResponse({
            "response": result.get("response", ""),
            "status": result.get("status", "success"),
            "task_type": result.get("task_type", "general")
        })
    except Exception as e:
        log.error(f"❌ Ошибка в /chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/chat/history")
async def get_chat_history(user_id: str, limit: int = 20):
    """Получить историю чата пользователя (синхронизированную между Telegram и mini app)"""
    try:
        from backend.database import get_user_memory
        
        user_id_int = int(user_id) if user_id.isdigit() else None
        if not user_id_int:
            raise HTTPException(status_code=400, detail="Неверный user_id")
        
        history = get_user_memory(user_id_int, limit=limit)
        
        formatted_history = []
        for msg in history:
            formatted_history.append({
                "role": msg.get("role", "user"),
                "content": msg.get("text", msg.get("content", "")),
                "created_at": msg.get("created_at", ""),
                "platform": msg.get("platform", "unknown")
            })
        
        return JSONResponse({
            "history": formatted_history,
            "count": len(formatted_history)
        })
    except Exception as e:
        log.error(f"❌ Ошибка в /chat/history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ===================== MAIN =====================

def main():
    """Запуск веб-сервера"""
    log.info(f"🚀 Запуск веб-интерфейса на порту {WEB_INTERFACE_PORT}")
    uvicorn.run(app, host="0.0.0.0", port=WEB_INTERFACE_PORT)

if __name__ == "__main__":
    main()



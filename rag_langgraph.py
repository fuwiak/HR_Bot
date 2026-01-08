"""
RAG цепочка с LangGraph для точного извлечения цен без галлюцинаций.
Использует stateful processing и валидацию для гарантии точности цен.
"""
import logging
import re
from typing import TypedDict, Annotated, Literal, List, Dict, Any, Optional
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
import operator

from qdrant_helper import search_service
from llm_api import LLMClient

logger = logging.getLogger(__name__)

# Определение состояния для LangGraph
class RAGState(TypedDict):
    """Состояние RAG обработки"""
    user_query: str
    query_type: str  # "pricing", "general", "service_info"
    search_results: List[Dict[str, Any]]
    pricing_info: Dict[str, Any]
    context_docs: List[Dict[str, Any]]
    formatted_context: str
    llm_response: str
    validated: bool
    validation_errors: List[str]
    retry_count: int
    final_answer: str
    sources: List[str]
    metadata: Dict[str, Any]


def classify_query(state: RAGState) -> RAGState:
    """Классифицирует тип запроса пользователя"""
    query = state["user_query"].lower()
    
    pricing_keywords = [
        "цена", "стоимость", "стоит", "рублей", "руб", "прайс", "price", "cost",
        "сколько", "купить", "продажа", "прайс-лист", "pricelist", "коммерческое предложение",
        "кп", "коммерческий", "предложение", "расценки", "тарифы", "от"
    ]
    
    service_keywords = [
        "услуга", "консультация", "тренинг", "сессия", "коучинг", "аудит",
        "разработка", "внедрение", "автоматизация", "оптимизация"
    ]
    
    if any(kw in query for kw in pricing_keywords):
        query_type = "pricing"
        logger.info(f"🔍 Запрос классифицирован как: PRICING")
    elif any(kw in query for kw in service_keywords):
        query_type = "service_info"
        logger.info(f"🔍 Запрос классифицирован как: SERVICE_INFO")
    else:
        query_type = "general"
        logger.info(f"🔍 Запрос классифицирован как: GENERAL")
    
    state["query_type"] = query_type
    return state


def search_rag(state: RAGState) -> RAGState:
    """Поиск в RAG с разными параметрами в зависимости от типа запроса"""
    query = state["user_query"]
    query_type = state["query_type"]
    
    try:
        if query_type == "pricing":
            # Для запросов о ценах - более широкий поиск с большим лимитом
            results = search_service(query, limit=10)
            logger.info(f"🔍 Найдено {len(results)} услуг для запроса о ценах")
            state["search_results"] = results
        else:
            # Для общих запросов используем стандартный поиск
            # Можно интегрировать с qdrant_loader для документов базы знаний
            results = search_service(query, limit=5)
            state["search_results"] = results
            logger.info(f"🔍 Найдено {len(results)} результатов для общего запроса")
    except Exception as e:
        logger.error(f"❌ Ошибка поиска в RAG: {e}")
        state["search_results"] = []
    
    return state


def extract_pricing_info(state: RAGState) -> RAGState:
    """Извлекает точную информацию о ценах из результатов поиска"""
    if state["query_type"] != "pricing":
        state["pricing_info"] = {}
        return state
    
    results = state["search_results"]
    pricing_info = {
        "services": [],
        "exact_prices": {},
        "pricing_context": ""
    }
    
    for result in results:
        title = result.get("title", "")
        price_str = result.get("price_str", "")
        price = result.get("price", 0)
        score = result.get("score", 0)
        
        # Формируем точную цену
        if price_str:
            exact_price = price_str
        elif price > 0:
            exact_price = f"{price} рублей"
        else:
            exact_price = "уточнить цену"
        
        pricing_info["services"].append({
            "title": title,
            "price": exact_price,
            "score": score
        })
        
        # Добавляем в словарь для быстрого поиска (нижний регистр для сравнения)
        pricing_info["exact_prices"][title.lower()] = exact_price
    
    # Форматируем контекст для LLM
    if pricing_info["services"]:
        context = "\n\n🚨🚨🚨 КРИТИЧЕСКИ ВАЖНО - ТОЧНЫЕ ЦЕНЫ ИЗ БАЗЫ ДАННЫХ 🚨🚨🚨\n"
        context += "Используй ТОЛЬКО эти цены, НИКОГДА не выдумывай!\n\n"
        
        for service in pricing_info["services"]:
            context += f"✅ {service['title']}\n"
            context += f"   💰 ЦЕНА: {service['price']}\n"
            context += f"   📊 Релевантность: {service['score']:.1%}\n\n"
        
        context += "❌ ЗАПРЕЩЕНО:\n"
        context += "- Выдумывать цены\n"
        context += "- Округлять цены\n"
        context += "- Изменять формат цен\n"
        context += "- Использовать цены не из этого списка\n\n"
        context += "✅ ОБЯЗАТЕЛЬНО:\n"
        context += "- Используй ТОЧНО указанные цены из списка выше\n"
        context += "- Если услуги нет в списке - скажи 'уточнить цену'\n"
        context += "- Формат цены должен быть ТОЧНО как в базе: 'от X рублей' или 'X рублей'\n"
        
        pricing_info["pricing_context"] = context
        logger.info(f"💰 Извлечено {len(pricing_info['services'])} услуг с ценами")
    
    state["pricing_info"] = pricing_info
    return state


def format_context(state: RAGState) -> RAGState:
    """Форматирует контекст для LLM в зависимости от типа запроса"""
    if state["query_type"] == "pricing":
        # Для цен используем специальный контекст
        state["formatted_context"] = state["pricing_info"].get("pricing_context", "")
    else:
        # Для общих запросов форматируем стандартным образом
        results = state["search_results"]
        context_parts = []
        
        for i, result in enumerate(results, 1):
            title = result.get("title", "")
            price_str = result.get("price_str", "")
            score = result.get("score", 0)
            
            context_part = f"[Результат {i}] (релевантность: {score:.2f})\n"
            context_part += f"Услуга: {title}\n"
            if price_str:
                context_part += f"Цена: {price_str}\n"
            context_part += "\n"
            
            context_parts.append(context_part)
        
        state["formatted_context"] = "\n---\n".join(context_parts) if context_parts else ""
    
    return state


def generate_response(state: RAGState) -> RAGState:
    """Генерирует ответ через LLM с учетом контекста"""
    query = state["user_query"]
    context = state["formatted_context"]
    query_type = state["query_type"]
    
    try:
        # Формируем промпт в зависимости от типа запроса
        if query_type == "pricing":
            if context:
                prompt = f"""Контекст из базы знаний с ТОЧНЫМИ ЦЕНАМИ:

{context}

Вопрос пользователя: {query}

Ответь на вопрос, используя ТОЧНЫЕ цены из контекста выше. НИКОГДА не выдумывай цены!"""
            else:
                prompt = f"""Вопрос пользователя: {query}

Ответь на вопрос о ценах. Если точной информации нет, скажи что нужно уточнить цену."""
        else:
            if context:
                prompt = f"""Контекст из базы знаний:

{context}

Вопрос пользователя: {query}

Ответь на вопрос, используя предоставленный контекст."""
            else:
                prompt = f"""Вопрос пользователя: {query}

Ответь на вопрос, используя свои знания о HR консалтинге."""
        
        # Системный промпт
        if query_type == "pricing":
            system_prompt = """Ты AI-ассистент HR консультанта. 

КРИТИЧЕСКИ ВАЖНО для вопросов о ценах:
- Используй ТОЛЬКО точные цены из предоставленного контекста
- НИКОГДА не выдумывай, не округляй, не изменяй цены
- Если услуги нет в списке - пиши "уточнить цену"
- Формат цены должен быть ТОЧНО как в базе данных"""
        else:
            system_prompt = """Ты AI-ассистент HR консультанта. 
Отвечай профессионально, используя информацию из базы знаний если она предоставлена."""
        
        # Генерируем ответ (синхронная обертка для async функции)
        import asyncio
        llm_client = LLMClient()
        
        # Используем asyncio.run если нет event loop, иначе используем существующий
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Если loop уже запущен, используем asyncio.create_task или другой подход
                # В этом случае используем синхронную обертку
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        llm_client.generate(
                            prompt=prompt,
                            system_prompt=system_prompt,
                            temperature=0.3 if query_type == "pricing" else 0.7,
                            max_tokens=2048
                        )
                    )
                    response = future.result(timeout=60)
            else:
                response = loop.run_until_complete(
                    llm_client.generate(
                        prompt=prompt,
                        system_prompt=system_prompt,
                        temperature=0.3 if query_type == "pricing" else 0.7,
                        max_tokens=2048
                    )
                )
        except RuntimeError:
            # Нет event loop, создаем новый
            response = asyncio.run(
                llm_client.generate(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    temperature=0.3 if query_type == "pricing" else 0.7,
                    max_tokens=2048
                )
            )
        
        state["llm_response"] = response.content if response else "Не удалось сгенерировать ответ"
        logger.info(f"✅ Ответ сгенерирован (тип: {query_type})")
        
    except Exception as e:
        logger.error(f"❌ Ошибка генерации ответа: {e}")
        state["llm_response"] = "Произошла ошибка при генерации ответа"
    
    return state


def validate_prices(state: RAGState) -> RAGState:
    """Валидирует, что цены в ответе соответствуют найденным услугам"""
    if state["query_type"] != "pricing":
        state["validated"] = True
        return state
    
    response = state["llm_response"]
    exact_prices = state["pricing_info"].get("exact_prices", {})
    errors = []
    
    if not exact_prices:
        # Если нет точных цен, валидация проходит
        state["validated"] = True
        state["validation_errors"] = []
        return state
    
    # Ищем упоминания цен в ответе
    # Паттерн для поиска цен: числа с возможными пробелами/запятыми и словами "руб", "₽", "рублей"
    price_patterns = [
        r'от\s+(\d+[\s,.]?\d*)\s*(?:руб|₽|рублей|руб\.)',
        r'(\d+[\s,.]?\d*)\s*(?:руб|₽|рублей|руб\.)',
        r'стоимость[:\s]+(\d+[\s,.]?\d*)',
        r'цена[:\s]+(\d+[\s,.]?\d*)',
    ]
    
    found_prices = []
    for pattern in price_patterns:
        matches = re.findall(pattern, response, re.IGNORECASE)
        found_prices.extend(matches)
    
    # Проверяем каждую найденную цену
    for price_match in found_prices:
        if isinstance(price_match, tuple):
            price_value = price_match[0] if price_match else ""
        else:
            price_value = price_match
        
        # Нормализуем цену (убираем пробелы, запятые)
        price_normalized = price_value.replace(' ', '').replace(',', '.').replace(' ', '')
        
        # Проверяем, есть ли эта цена в точных ценах
        price_found = False
        for service_title, exact_price in exact_prices.items():
            # Извлекаем числа из точной цены
            exact_numbers = re.findall(r'\d+', exact_price)
            if price_normalized in exact_numbers or any(price_normalized in num for num in exact_numbers):
                price_found = True
                break
            # Также проверяем по тексту
            if price_normalized in exact_price.replace(' ', '').replace(',', '.'):
                price_found = True
                break
        
        if not price_found and price_normalized:
            errors.append(f"⚠️ Обнаружена цена '{price_value}', которой нет в базе данных")
    
    state["validation_errors"] = errors
    state["validated"] = len(errors) == 0
    
    if errors:
        logger.warning(f"⚠️ Обнаружены ошибки валидации цен: {errors}")
    else:
        logger.info("✅ Валидация цен прошла успешно")
    
    return state


def should_retry(state: RAGState) -> Literal["retry", "finish"]:
    """Определяет, нужно ли повторить генерацию ответа"""
    if not state["validated"] and state["retry_count"] < 2:
        logger.info(f"🔄 Требуется повторная попытка (попытка {state['retry_count'] + 1}/2)")
        return "retry"
    return "finish"


def increment_retry(state: RAGState) -> RAGState:
    """Увеличивает счетчик попыток"""
    state["retry_count"] = state.get("retry_count", 0) + 1
    return state


def finalize_answer(state: RAGState) -> RAGState:
    """Финаллизирует ответ"""
    if state["validated"]:
        state["final_answer"] = state["llm_response"]
    else:
        # Если валидация не прошла, добавляем предупреждение
        errors = "\n".join(state["validation_errors"])
        state["final_answer"] = f"{state['llm_response']}\n\n⚠️ ВНИМАНИЕ: Обнаружены возможные неточности в ценах. Пожалуйста, уточните информацию."
        logger.warning(f"⚠️ Ответ финализирован с предупреждением: {errors}")
    
    # Добавляем источники
    sources = []
    for result in state["search_results"]:
        title = result.get("title", "")
        if title:
            sources.append(title)
    state["sources"] = sources
    
    logger.info(f"✅ Ответ финализирован (валидация: {state['validated']})")
    return state


# Создание графа LangGraph
def create_rag_graph():
    """Создает граф LangGraph для RAG обработки"""
    workflow = StateGraph(RAGState)
    
    # Добавляем узлы
    workflow.add_node("classify", classify_query)
    workflow.add_node("search", search_rag)
    workflow.add_node("extract_pricing", extract_pricing_info)
    workflow.add_node("format", format_context)
    workflow.add_node("generate", generate_response)
    workflow.add_node("validate", validate_prices)
    workflow.add_node("increment_retry", increment_retry)
    workflow.add_node("finalize", finalize_answer)
    
    # Определяем поток
    workflow.set_entry_point("classify")
    workflow.add_edge("classify", "search")
    workflow.add_edge("search", "extract_pricing")
    workflow.add_edge("extract_pricing", "format")
    workflow.add_edge("format", "generate")
    workflow.add_edge("generate", "validate")
    
    # Условное переключение после валидации
    workflow.add_conditional_edges(
        "validate",
        should_retry,
        {
            "retry": "increment_retry",
            "finish": "finalize"
        }
    )
    
    # Если retry - возвращаемся к генерации
    workflow.add_edge("increment_retry", "generate")
    workflow.add_edge("finalize", END)
    
    # Компилируем граф с памятью состояния
    memory = MemorySaver()
    app = workflow.compile(checkpointer=memory)
    
    return app


# Singleton для графа
_rag_graph_app = None

def get_rag_graph():
    """Получить экземпляр графа LangGraph (Singleton)"""
    global _rag_graph_app
    if _rag_graph_app is None:
        _rag_graph_app = create_rag_graph()
    return _rag_graph_app


async def query_with_langgraph(
    user_query: str, 
    thread_id: str = "default"
) -> Dict[str, Any]:
    """
    Запрос через LangGraph с точным извлечением цен
    
    Args:
        user_query: Запрос пользователя
        thread_id: ID потока для сохранения состояния
    
    Returns:
        Словарь с ответом и метаданными
    """
    app = get_rag_graph()
    
    initial_state = {
        "user_query": user_query,
        "query_type": "",
        "search_results": [],
        "pricing_info": {},
        "context_docs": [],
        "formatted_context": "",
        "llm_response": "",
        "validated": False,
        "validation_errors": [],
        "retry_count": 0,
        "final_answer": "",
        "sources": [],
        "metadata": {}
    }
    
    config = {"configurable": {"thread_id": thread_id}}
    
    try:
        # Запускаем граф
        result = await app.ainvoke(initial_state, config)
        
        return {
            "answer": result["final_answer"],
            "sources": result["sources"],
            "query_type": result["query_type"],
            "validated": result["validated"],
            "validation_errors": result["validation_errors"],
            "retry_count": result["retry_count"],
            "pricing_info": result.get("pricing_info", {}),
            "metadata": {
                "search_results_count": len(result["search_results"]),
                "has_pricing_context": bool(result.get("pricing_info", {}).get("pricing_context"))
            }
        }
    except Exception as e:
        logger.error(f"❌ Ошибка выполнения LangGraph: {e}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        return {
            "answer": "Произошла ошибка при обработке запроса",
            "sources": [],
            "query_type": "error",
            "validated": False,
            "validation_errors": [str(e)],
            "retry_count": 0,
            "pricing_info": {},
            "metadata": {}
        }

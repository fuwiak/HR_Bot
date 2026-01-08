"""
LangGraph Conversation Workflow для генерации ответов с историей сообщений
Используется для генерации ответов HR бота с краткосрочной памятью
"""
import os
import sys
import logging
from typing import Dict, Any, Optional, List, TypedDict
from datetime import datetime

# Добавляем корневую директорию проекта в sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

try:
    from langgraph.graph import StateGraph, END, START
    from langgraph.graph.message import add_messages
    from typing import Annotated
    try:
        from langchain_core.messages import HumanMessage, AIMessage
        LANGCHAIN_MESSAGES_AVAILABLE = True
    except ImportError:
        LANGCHAIN_MESSAGES_AVAILABLE = False
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    LANGCHAIN_MESSAGES_AVAILABLE = False
    add_messages = None
    Annotated = None

log = logging.getLogger(__name__)


class ConversationState(TypedDict):
    """Состояние для LangGraph conversation workflow с поддержкой add_messages"""
    messages: Annotated[list, add_messages] if add_messages else List[Dict[str, str]]
    current_message: str
    system_prompt: str
    task_type: str  # pricing, general, booking, service_info
    response: Optional[str]
    error: Optional[str]
    # Контекст пользователя
    user_name: Optional[str]
    user_id: Optional[str]
    platform: Optional[str]
    bot_already_introduced: Optional[bool]
    needs_user_name: Optional[bool]
    # RAG контекст
    rag_context: Optional[str]
    search_results: Optional[list]
    pricing_info: Optional[dict]


class LangGraphConversationWorkflow:
    """
    LangGraph workflow для генерации ответов HR бота
    Использует in-memory хранилище состояний по user_id
    """
    
    def __init__(self, max_history_messages: int = 50):
        self.graph = None
        self._initialized = False
        self._thread_states: Dict[str, Dict[str, Any]] = {}
        self.max_history_messages = max_history_messages
    
    def initialize(self):
        """Инициализация LangGraph workflow"""
        if not LANGGRAPH_AVAILABLE:
            log.warning("LangGraph не установлен, workflow недоступен")
            return False
        
        if self._initialized:
            return True
        
        try:
            workflow = StateGraph(ConversationState)
            
            # Добавляем узлы
            workflow.add_node("trim_history", self._trim_history_node)
            workflow.add_node("classify_query", self._classify_query_node)
            workflow.add_node("search_rag", self._search_rag_node)
            workflow.add_node("format_messages", self._format_messages_node)
            workflow.add_node("generate_response", self._generate_response_node)
            
            # Определяем поток выполнения
            workflow.set_entry_point("trim_history")
            workflow.add_edge("trim_history", "classify_query")
            workflow.add_edge("classify_query", "search_rag")
            workflow.add_edge("search_rag", "format_messages")
            workflow.add_edge("format_messages", "generate_response")
            workflow.add_edge("generate_response", END)
            
            self.graph = workflow.compile()
            self._initialized = True
            log.info("✅ LangGraph Conversation Workflow инициализирован")
            return True
        except Exception as e:
            log.error(f"❌ Ошибка инициализации LangGraph: {e}", exc_info=True)
            return False
    
    async def _trim_history_node(self, state: ConversationState) -> Dict[str, Any]:
        """Обрезает историю до последних N сообщений"""
        try:
            user_id = state.get("user_id")
            platform = state.get("platform", "telegram")
            msgs = state.get("messages", [])
            
            if user_id:
                thread_key = f"{user_id}_{platform}"
                prev_state = self._thread_states.get(thread_key, {})
                prev_messages = prev_state.get("messages", [])
                
                if prev_messages:
                    if isinstance(prev_messages[0], dict):
                        if LANGCHAIN_MESSAGES_AVAILABLE:
                            converted = []
                            for msg in prev_messages:
                                role = msg.get("role", "user")
                                content = msg.get("content", "")
                                if role == "user":
                                    converted.append(HumanMessage(content=content))
                                elif role == "assistant":
                                    converted.append(AIMessage(content=content))
                            prev_messages = converted
                    msgs = list(prev_messages) + msgs
                
                msgs = msgs[-self.max_history_messages:] if len(msgs) > self.max_history_messages else msgs
                self._thread_states[thread_key] = {"messages": msgs}
                state["messages"] = msgs
                log.debug(f"✅ История обрезана до {len(msgs)} сообщений")
            else:
                msgs = msgs[-self.max_history_messages:] if len(msgs) > self.max_history_messages else msgs
                state["messages"] = msgs
            
            return state
        except Exception as e:
            log.error(f"❌ Ошибка обрезки истории: {e}")
            return state
    
    async def _classify_query_node(self, state: ConversationState) -> Dict[str, Any]:
        """Классификация запроса пользователя"""
        try:
            current_message = state.get("current_message", "").lower()
            
            # Определяем тип запроса
            pricing_keywords = ["цена", "стоимость", "стоит", "рублей", "руб", "прайс", 
                               "сколько", "купить", "расценки", "тарифы", "от 90"]
            booking_keywords = ["записаться", "запись", "бронь", "забронировать", 
                               "хочу записаться", "назначить"]
            service_keywords = ["услуга", "услуги", "что делаете", "что предлагаете",
                               "форсайт", "коучинг", "консультация"]
            
            if any(kw in current_message for kw in pricing_keywords):
                state["task_type"] = "pricing"
            elif any(kw in current_message for kw in booking_keywords):
                state["task_type"] = "booking"
            elif any(kw in current_message for kw in service_keywords):
                state["task_type"] = "service_info"
            else:
                state["task_type"] = "general"
            
            log.info(f"📊 Тип запроса: {state['task_type']}")
            return state
        except Exception as e:
            log.error(f"❌ Ошибка классификации: {e}")
            state["task_type"] = "general"
            return state
    
    async def _search_rag_node(self, state: ConversationState) -> Dict[str, Any]:
        """Поиск в RAG базе знаний"""
        try:
            current_message = state.get("current_message", "")
            task_type = state.get("task_type", "general")
            
            # Импортируем qdrant_helper
            try:
                from qdrant_helper import search_service
                
                # Выполняем поиск
                limit = 5 if task_type == "pricing" else 3
                results = search_service(current_message, limit=limit)
                
                if results:
                    state["search_results"] = results
                    
                    # Для ценовых запросов извлекаем информацию о ценах
                    if task_type == "pricing":
                        pricing_info = {"services": [], "exact_prices": {}}
                        for result in results:
                            payload = result.get("payload", {})
                            title = payload.get("title", "")
                            price = payload.get("price", 0)
                            price_str = payload.get("price_str", "")
                            
                            if title:
                                exact_price = price_str if price_str else (f"{price} рублей" if price > 0 else "уточнить цену")
                                pricing_info["services"].append({
                                    "title": title,
                                    "price": exact_price,
                                    "score": result.get("score", 0)
                                })
                                pricing_info["exact_prices"][title.lower()] = exact_price
                        
                        state["pricing_info"] = pricing_info
                        log.info(f"💰 Найдено {len(pricing_info['services'])} услуг с ценами")
                    
                    # Формируем RAG контекст
                    context_parts = []
                    for result in results:
                        payload = result.get("payload", {})
                        title = payload.get("title", "")
                        price_str = payload.get("price_str", "")
                        master = payload.get("master", "")
                        
                        if title:
                            part = f"- {title}"
                            if price_str:
                                part += f": {price_str}"
                            if master:
                                part += f" (мастер: {master})"
                            context_parts.append(part)
                    
                    state["rag_context"] = "\n".join(context_parts)
                    log.info(f"🔍 RAG поиск: найдено {len(results)} результатов")
                else:
                    log.info("⚠️ RAG поиск: результаты не найдены")
            except ImportError:
                log.warning("⚠️ qdrant_helper не доступен")
            except Exception as e:
                log.error(f"❌ Ошибка RAG поиска: {e}")
            
            return state
        except Exception as e:
            log.error(f"❌ Ошибка в search_rag_node: {e}")
            return state
    
    async def _format_messages_node(self, state: ConversationState) -> Dict[str, Any]:
        """Форматирование сообщений для LLM"""
        try:
            messages = state.get("messages", [])
            current_message = state.get("current_message", "")
            user_id = state.get("user_id")
            platform = state.get("platform", "telegram")
            
            formatted_messages = []
            
            # Добавляем system prompt
            system_prompt = state.get("system_prompt", "")
            if system_prompt:
                formatted_messages.append({"role": "system", "content": system_prompt})
            
            # Добавляем историю сообщений
            if messages:
                for msg in messages:
                    if LANGCHAIN_MESSAGES_AVAILABLE and (isinstance(msg, HumanMessage) or isinstance(msg, AIMessage)):
                        role = "user" if isinstance(msg, HumanMessage) else "assistant"
                        content = msg.content if hasattr(msg, 'content') else str(msg)
                        if content:
                            formatted_messages.append({"role": role, "content": content})
                    elif isinstance(msg, dict):
                        role = msg.get("role", "user")
                        content = msg.get("content", msg.get("text", ""))
                        if content:
                            formatted_messages.append({"role": role, "content": content})
            
            # Добавляем текущее сообщение
            if current_message:
                formatted_messages.append({"role": "user", "content": current_message})
                
                # Сохраняем в in-memory хранилище
                if user_id:
                    try:
                        thread_key = f"{user_id}_{platform}"
                        prev_state = self._thread_states.get(thread_key, {})
                        prev_messages = prev_state.get("messages", [])
                        
                        if LANGCHAIN_MESSAGES_AVAILABLE:
                            prev_messages.append(HumanMessage(content=current_message))
                        else:
                            prev_messages.append({"role": "user", "content": current_message})
                        
                        prev_messages = prev_messages[-self.max_history_messages:]
                        self._thread_states[thread_key] = {"messages": prev_messages}
                    except Exception as e:
                        log.debug(f"Не удалось сохранить в хранилище: {e}")
            
            state["formatted_messages"] = formatted_messages
            return state
        except Exception as e:
            log.error(f"❌ Ошибка форматирования: {e}")
            return {"error": str(e)}
    
    async def _generate_response_node(self, state: ConversationState) -> Dict[str, Any]:
        """Генерация ответа через LLM"""
        try:
            formatted_messages = state.get("formatted_messages", [])
            current_message = state.get("current_message", "")
            task_type = state.get("task_type", "general")
            rag_context = state.get("rag_context", "")
            pricing_info = state.get("pricing_info", {})
            
            # Загружаем system prompt
            system_prompt = state.get("system_prompt", "")
            if not system_prompt:
                system_prompt = """Ты — профессиональный HR ассистент.
Отвечай ТОЛЬКО НА РУССКОМ ЯЗЫКЕ.
Будь вежливым и профессиональным.
Помогай клиентам с вопросами об услугах, ценах и записи.

КРИТИЧНО для ценовых запросов:
- Используй ТОЛЬКО точные цены из базы данных
- НЕ выдумывай и НЕ округляй цены
- Если цена указана как "от X рублей" - используй ТОЧНО этот формат
- Если цены нет в базе - скажи "уточнить цену"
"""
            
            if not formatted_messages:
                if current_message:
                    formatted_messages = [{"role": "user", "content": current_message}]
                else:
                    return {"response": "Не удалось сформировать сообщения.", "error": "Empty messages"}
            
            # Формируем промпт с контекстом
            prompt_parts = []
            
            # Добавляем RAG контекст
            if rag_context:
                prompt_parts.append(f"Информация из базы знаний:\n{rag_context}")
            
            # Для ценовых запросов добавляем строгие инструкции
            if task_type == "pricing" and pricing_info:
                services = pricing_info.get("services", [])
                if services:
                    prices_text = "\n".join([f"- {s['title']}: {s['price']}" for s in services])
                    prompt_parts.append(f"""
ТОЧНЫЕ ЦЕНЫ ИЗ БАЗЫ ДАННЫХ:
{prices_text}

❌ ЗАПРЕЩЕНО:
- Выдумывать цены
- Округлять цены
- Изменять формат цен

✅ ОБЯЗАТЕЛЬНО:
- Используй ТОЧНО указанные цены
- Формат: "от X рублей" или "X рублей"
""")
            
            # Добавляем текущее сообщение
            prompt_parts.append(f"Сообщение пользователя: {current_message}")
            
            user_prompt = "\n\n".join(prompt_parts) if prompt_parts else current_message
            
            # Генерируем ответ через LLM
            try:
                from llm_api import LLMClient
                
                llm_client = LLMClient(
                    primary_provider="openrouter",
                    primary_model="deepseek/deepseek-chat",
                    timeout=30
                )
                
                # Для ценовых запросов используем низкую температуру
                temperature = 0.3 if task_type == "pricing" else 0.7
                
                response = await llm_client.generate(
                    prompt=user_prompt,
                    system_prompt=system_prompt,
                    temperature=temperature,
                    max_tokens=2048
                )
                
                if response.error:
                    log.error(f"❌ Ошибка LLM: {response.error}")
                    return {"response": "Извините, произошла ошибка.", "error": response.error}
                
                answer = response.content.strip() if response.content else "Не удалось получить ответ."
                
            except Exception as llm_error:
                log.error(f"❌ Ошибка LLM клиента: {llm_error}")
                # Fallback на openrouter_chat
                try:
                    from app import openrouter_chat
                    messages = [{"role": "user", "content": user_prompt}]
                    answer = await openrouter_chat(messages, use_system_message=True, system_content=system_prompt)
                except Exception as fallback_error:
                    log.error(f"❌ Fallback тоже не сработал: {fallback_error}")
                    return {"response": "Извините, сервис временно недоступен.", "error": str(fallback_error)}
            
            # Сохраняем ответ в хранилище
            user_id = state.get("user_id")
            platform = state.get("platform", "telegram")
            
            if user_id and answer:
                try:
                    thread_key = f"{user_id}_{platform}"
                    prev_state = self._thread_states.get(thread_key, {})
                    prev_messages = prev_state.get("messages", [])
                    
                    if LANGCHAIN_MESSAGES_AVAILABLE:
                        prev_messages.append(AIMessage(content=answer))
                    else:
                        prev_messages.append({"role": "assistant", "content": answer})
                    
                    prev_messages = prev_messages[-self.max_history_messages:]
                    self._thread_states[thread_key] = {"messages": prev_messages}
                except Exception as e:
                    log.debug(f"Не удалось сохранить ответ: {e}")
            
            return {"response": answer}
            
        except Exception as e:
            log.error(f"❌ Ошибка генерации: {e}", exc_info=True)
            return {"response": "Извините, произошла ошибка.", "error": str(e)}
    
    async def run(
        self,
        message: str,
        message_history: Optional[List[Dict[str, str]]] = None,
        system_prompt: Optional[str] = None,
        task_type: str = "general",
        user_name: Optional[str] = None,
        bot_already_introduced: bool = False,
        needs_user_name: bool = False,
        user_id: Optional[str] = None,
        platform: str = "telegram"
    ) -> Dict[str, Any]:
        """
        Запустить workflow для генерации ответа
        
        Args:
            message: Текущее сообщение пользователя
            message_history: История сообщений
            system_prompt: Системный промпт
            task_type: Тип задачи
            user_name: Имя пользователя
            bot_already_introduced: Бот уже представлялся?
            needs_user_name: Нужно спросить имя?
            user_id: ID пользователя
            platform: Платформа
        
        Returns:
            Результат с ответом
        """
        log.info(f"📨 LangGraph Conversation Workflow запущен, task_type={task_type}")
        
        if not self._initialized:
            if not self.initialize():
                return {
                    "response": "LangGraph недоступен",
                    "error": "LangGraph не инициализирован",
                    "status": "error"
                }
        
        try:
            # Загружаем system prompt если не передан
            if not system_prompt:
                system_prompt = """Ты — профессиональный HR ассистент.
Отвечай ТОЛЬКО НА РУССКОМ ЯЗЫКЕ.
Будь вежливым и профессиональным.
Помогай клиентам с вопросами об услугах, ценах и записи.

КРИТИЧНО:
- Используй ТОЛЬКО точные цены из базы данных
- НЕ выдумывай цены
- Если цены нет - скажи "уточнить цену"
"""
            
            # Формируем начальное состояние
            initial_state: ConversationState = {
                "messages": message_history or [],
                "current_message": message,
                "system_prompt": system_prompt,
                "task_type": task_type,
                "response": None,
                "error": None,
                "user_name": user_name,
                "user_id": user_id,
                "platform": platform,
                "bot_already_introduced": bot_already_introduced,
                "needs_user_name": needs_user_name,
                "rag_context": None,
                "search_results": None,
                "pricing_info": None
            }
            
            # Запускаем workflow
            result = await self.graph.ainvoke(initial_state)
            
            response = result.get("response", "Не удалось получить ответ")
            log.info(f"✅ LangGraph завершил генерацию, length={len(response) if response else 0}")
            
            return {
                "response": response,
                "error": result.get("error"),
                "status": "success" if not result.get("error") else "error",
                "task_type": result.get("task_type", task_type),
                "pricing_info": result.get("pricing_info"),
                "search_results": result.get("search_results")
            }
        except Exception as e:
            log.error(f"❌ Ошибка LangGraph workflow: {e}", exc_info=True)
            return {
                "response": f"Ошибка: {str(e)}",
                "error": str(e),
                "status": "error"
            }


# Глобальный экземпляр workflow
_conversation_workflow: Optional[LangGraphConversationWorkflow] = None


def get_conversation_workflow(max_history_messages: int = 50) -> LangGraphConversationWorkflow:
    """Получить глобальный экземпляр LangGraph Conversation Workflow"""
    global _conversation_workflow
    if _conversation_workflow is None:
        _conversation_workflow = LangGraphConversationWorkflow(max_history_messages=max_history_messages)
        _conversation_workflow.initialize()
    return _conversation_workflow


async def query_with_conversation_workflow(
    message: str,
    user_id: str = None,
    platform: str = "telegram",
    message_history: List[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Удобная функция для запроса через LangGraph Conversation Workflow
    
    Args:
        message: Сообщение пользователя
        user_id: ID пользователя
        platform: Платформа
        message_history: История сообщений
    
    Returns:
        Словарь с ответом и метаданными
    """
    workflow = get_conversation_workflow()
    return await workflow.run(
        message=message,
        user_id=user_id,
        platform=platform,
        message_history=message_history
    )

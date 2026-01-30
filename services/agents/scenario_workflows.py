"""
Scenario Workflows Module
Реализация всех 4 бизнес-сценариев использования AI-ассистента
"""
import os
import logging
import asyncio
import json
import re
from typing import Dict, List, Optional
from datetime import datetime, timedelta

log = logging.getLogger()

# Импорты модулей
try:
    from services.helpers.hrtime_helper import get_new_orders, send_proposal, send_message, get_order_details
    from services.agents.lead_processor import classify_request, validate_lead, generate_proposal
    from services.helpers.email_helper import check_new_emails, classify_email, send_email
    from services.helpers.weeek_helper import create_project, create_task, get_project_deadlines
    from services.rag.rag_chain import RAGChain
    from services.services.hrtime_order_parser import HRTimeOrderParser
    from services.services.hrtime_lead_validator import HRTimeLeadValidator
    from services.helpers.llm_api import LLMClient
    HRTIME_AVAILABLE = True
    EMAIL_AVAILABLE = True
    WEEEK_AVAILABLE = True
    RAG_AVAILABLE = True
    PARSER_AVAILABLE = True
    VALIDATOR_AVAILABLE = True
    LLM_AVAILABLE = True
except ImportError as e:
    log.warning(f"⚠️ Некоторые модули недоступны: {e}")
    HRTIME_AVAILABLE = False
    EMAIL_AVAILABLE = False
    WEEEK_AVAILABLE = False
    RAG_AVAILABLE = False
    PARSER_AVAILABLE = False
    VALIDATOR_AVAILABLE = False
    LLM_AVAILABLE = False

# Telegram bot для отправки уведомлений консультанту
TELEGRAM_CONSULTANT_CHAT_ID = os.getenv("TELEGRAM_CONSULTANT_CHAT_ID")  # ID чата консультанта для уведомлений
TELEGRAM_LEADS_CHANNEL_ID = os.getenv("TELEGRAM_LEADS_CHANNEL_ID")  # ID канала для лидов (HRAI_ANovoselova_Лиды)

# Глобальный экземпляр RAG для всех сценариев
_rag_chain = None

def get_rag_chain():
    """Получить экземпляр RAGChain (Singleton)"""
    global _rag_chain
    if not RAG_AVAILABLE:
        return None
    if _rag_chain is None:
        try:
            _rag_chain = RAGChain()
        except Exception as e:
            log.error(f"❌ Ошибка инициализации RAGChain: {e}")
            return None
    return _rag_chain


async def classify_email_as_lead(email_subject: str, email_body: str) -> Dict[str, str]:
    """
    Классифицировать email как lead или non_lead используя Open Router LLM
    
    Args:
        email_subject: Тема письма
        email_body: Тело письма
    
    Returns:
        Словарь с ключами:
        - label: "lead" или "non_lead"
        - confidence: уверенность (0.0-1.0)
        - reason: причина классификации
    """
    if not LLM_AVAILABLE:
        log.warning("⚠️ LLM недоступен, используем дефолтную классификацию как non_lead")
        return {
            "label": "non_lead",
            "confidence": 0.5,
            "reason": "LLM недоступен, использована дефолтная классификация"
        }
    
    try:
        # Формируем промпт для классификации
        classification_prompt = f"""Проанализируй следующее email сообщение и определи, является ли оно потенциальным лидом (запросом на услуги HR-консалтинга) или нет.

Тема письма: "{email_subject}"

Текст письма:
{email_body[:2000]}

Определи, является ли это письмо:
- **lead** - потенциальный клиент, который интересуется услугами HR-консалтинга, запрашивает консультацию, хочет получить предложение, интересуется ценами, просит информацию об услугах
- **non_lead** - спам, рассылки, уведомления, автоматические сообщения, личная переписка не связанная с бизнесом, реклама, технические уведомления

Ответь ТОЛЬКО в формате JSON:
{{
    "label": "lead" или "non_lead",
    "confidence": число от 0.0 до 1.0 (уверенность в классификации),
    "reason": "краткое объяснение причины классификации на русском языке"
}}

Важно: Отвечай ТОЛЬКО валидным JSON, без дополнительного текста."""

        # Используем LLMClient для классификации
        llm_client = LLMClient()
        response = await llm_client.generate(
            prompt=classification_prompt,
            system_prompt="Ты помощник для классификации email сообщений. Отвечай только в формате JSON.",
            temperature=0.3,  # Низкая температура для более детерминированных ответов
            max_tokens=200
        )
        
        if response.error:
            log.error(f"❌ Ошибка LLM при классификации email: {response.error}")
            return {
                "label": "non_lead",
                "confidence": 0.5,
                "reason": f"Ошибка LLM: {response.error}"
            }
        
        # Парсим JSON ответ
        content = response.content.strip()
        
        # Извлекаем JSON из ответа (может быть обернут в markdown код блоки)
        json_match = re.search(r'\{[^{}]*"label"[^{}]*\}', content, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
        else:
            # Пробуем найти JSON между фигурными скобками
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = content[json_start:json_end]
            else:
                json_str = content
        
        try:
            result = json.loads(json_str)
            label = result.get("label", "non_lead").lower()
            confidence = float(result.get("confidence", 0.5))
            reason = result.get("reason", "Классификация выполнена")
            
            # Валидация label
            if label not in ["lead", "non_lead"]:
                log.warning(f"⚠️ Неожиданный label от LLM: {label}, используем non_lead")
                label = "non_lead"
            
            log.info(f"✅ Email классифицирован как {label} (confidence: {confidence:.2f}, reason: {reason})")
            return {
                "label": label,
                "confidence": max(0.0, min(1.0, confidence)),  # Ограничиваем от 0 до 1
                "reason": reason
            }
        except json.JSONDecodeError as e:
            log.error(f"❌ Ошибка парсинга JSON от LLM: {e}, ответ: {content[:200]}")
            # Пробуем извлечь label из текста напрямую
            if "lead" in content.lower() and "non_lead" not in content.lower():
                return {
                    "label": "lead",
                    "confidence": 0.6,
                    "reason": "Классификация по ключевым словам (JSON не распарсился)"
                }
            return {
                "label": "non_lead",
                "confidence": 0.5,
                "reason": f"Ошибка парсинга JSON: {str(e)}"
            }
            
    except Exception as e:
        log.error(f"❌ Исключение при классификации email: {e}")
        import traceback
        log.error(traceback.format_exc())
        return {
            "label": "non_lead",
            "confidence": 0.5,
            "reason": f"Исключение: {str(e)}"
        }


async def classify_email_type(email_subject: str, email_body: str) -> Dict[str, str]:
    """
    Классифицировать email на три категории используя Open Router LLM:
    - новый лид
    - продолжение диалога
    - служебная информация
    
    Args:
        email_subject: Тема письма
        email_body: Тело письма
    
    Returns:
        Словарь с ключами:
        - category: "new_lead", "followup", "service"
        - confidence: уверенность (0.0-1.0)
        - reason: причина классификации на русском языке
    """
    if not LLM_AVAILABLE:
        log.warning("⚠️ LLM недоступен, используем дефолтную классификацию как service")
        return {
            "category": "service",
            "confidence": 0.5,
            "reason": "LLM недоступен, использована дефолтная классификация"
        }
    
    try:
        # Формируем промпт для классификации на три категории
        classification_prompt = f"""Проанализируй следующее email сообщение и определи его тип.

Тема письма: "{email_subject}"

Текст письма:
{email_body[:2000]}

Определи тип письма (выбери ОДНУ категорию):
- **new_lead** - новый потенциальный клиент, который впервые обращается за услугами HR-консалтинга, запрашивает консультацию, хочет получить предложение, интересуется ценами, просит информацию об услугах, новый запрос на сотрудничество
- **followup** - продолжение диалога, ответ на предыдущее письмо, переписка по существующему проекту, уточняющие вопросы по текущему запросу, ответы на вопросы клиента, обсуждение деталей проекта
- **service** - служебная информация: счета, договоры, технические уведомления, автоматические сообщения, рассылки, спам, реклама, уведомления от систем, отчеты, документы без запроса

Ответь ТОЛЬКО в формате JSON:
{{
    "category": "new_lead", "followup" или "service",
    "confidence": число от 0.0 до 1.0 (уверенность в классификации),
    "reason": "краткое объяснение причины классификации на русском языке"
}}

Важно: Отвечай ТОЛЬКО валидным JSON, без дополнительного текста."""

        # Используем LLMClient для классификации
        llm_client = LLMClient()
        response = await llm_client.generate(
            prompt=classification_prompt,
            system_prompt="Ты помощник для классификации email сообщений на три категории. Отвечай только в формате JSON.",
            temperature=0.3,  # Низкая температура для более детерминированных ответов
            max_tokens=200
        )
        
        if response.error:
            log.error(f"❌ Ошибка LLM при классификации email: {response.error}")
            return {
                "category": "service",
                "confidence": 0.5,
                "reason": f"Ошибка LLM: {response.error}"
            }
        
        # Парсим JSON ответ
        content = response.content.strip()
        
        # Извлекаем JSON из ответа (может быть обернут в markdown код блоки)
        json_match = re.search(r'\{[^{}]*"category"[^{}]*\}', content, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
        else:
            # Пробуем найти JSON между фигурными скобками
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = content[json_start:json_end]
            else:
                json_str = content
        
        try:
            result = json.loads(json_str)
            category = result.get("category", "service").lower()
            confidence = float(result.get("confidence", 0.5))
            reason = result.get("reason", "Классификация выполнена")
            
            # Валидация category
            valid_categories = ["new_lead", "followup", "service"]
            if category not in valid_categories:
                log.warning(f"⚠️ Неожиданная категория от LLM: {category}, используем service")
                category = "service"
            
            log.info(f"✅ Email классифицирован как {category} (confidence: {confidence:.2f}, reason: {reason})")
            return {
                "category": category,
                "confidence": max(0.0, min(1.0, confidence)),  # Ограничиваем от 0 до 1
                "reason": reason
            }
        except json.JSONDecodeError as e:
            log.error(f"❌ Ошибка парсинга JSON от LLM: {e}, ответ: {content[:200]}")
            # Пробуем извлечь category из текста напрямую
            content_lower = content.lower()
            if "new_lead" in content_lower or ("новый" in content_lower and "лид" in content_lower):
                return {
                    "category": "new_lead",
                    "confidence": 0.6,
                    "reason": "Классификация по ключевым словам (JSON не распарсился)"
                }
            elif "followup" in content_lower or "продолжение" in content_lower:
                return {
                    "category": "followup",
                    "confidence": 0.6,
                    "reason": "Классификация по ключевым словам (JSON не распарсился)"
                }
            return {
                "category": "service",
                "confidence": 0.5,
                "reason": f"Ошибка парсинга JSON: {str(e)}"
            }
            
    except Exception as e:
        log.error(f"❌ Исключение при классификации email: {e}")
        import traceback
        log.error(traceback.format_exc())
        return {
            "category": "service",
            "confidence": 0.5,
            "reason": f"Исключение: {str(e)}"
        }


async def send_lead_to_channel(telegram_bot, lead_info: Dict) -> bool:
    """
    Отправить информацию о лиде в канал HRAI_ANovoselova_Лиды
    
    Args:
        telegram_bot: Экземпляр Telegram бота
        lead_info: Словарь с информацией о лиде (source, title, client_name, client_email, client_phone, message, score, status, category, email_category)
                   email_category: "new_lead", "followup", "service" (опционально, если не указан, будет определён через LLM для email)
    
    Returns:
        True если сообщение отправлено успешно, False в противном случае
    """
    if not telegram_bot or not TELEGRAM_LEADS_CHANNEL_ID:
        return False
    
    try:
        source = lead_info.get("source", "неизвестно")
        title = lead_info.get("title", "Новый лид")
        client_name = lead_info.get("client_name", "Не указано")
        client_email = lead_info.get("client_email", "")
        client_phone = lead_info.get("client_phone", "")
        message = lead_info.get("message", "")
        score = lead_info.get("score", 0)
        status = lead_info.get("status", "unknown")
        category = lead_info.get("category", "")
        email_category = lead_info.get("email_category")  # "new_lead", "followup", "service"
        
        # Если email_category не указан и это email, классифицируем через LLM
        if not email_category and source == "📧 Email":
            classification = await classify_email_type(title, message)
            email_category = classification.get("category", "service")
            if "classification_reason" not in lead_info:
                lead_info["classification_reason"] = classification.get("reason", "")
            if "classification_confidence" not in lead_info:
                lead_info["classification_confidence"] = classification.get("confidence", 0.5)
        
        # Если email_category всё ещё не определён, используем дефолт
        if not email_category:
            email_category = "new_lead"  # По умолчанию считаем новым лидом для других источников
        
        # Определяем метку источника (в правом верхнем углу)
        source_label_map = {
            "📧 Email": "📧 YANDEX",
            "📢 Канал: @HRTime_bot": "📢 HRTIME",
            "🌐 Источник: HR Time API": "📢 HRTIME",
            "💬 Telegram бот": "💬 TELEGRAM",
            "📢 HR Time: Вся лента": "📢 HRTIME"
        }
        source_label = source_label_map.get(source, "📋 OTHER")
        
        # Определяем эмодзи и текст для категории
        category_map = {
            "new_lead": ("🔥", "НОВЫЙ ЛИД"),
            "followup": ("💬", "ПРОДОЛЖЕНИЕ ДИАЛОГА"),
            "service": ("📋", "СЛУЖЕБНАЯ ИНФОРМАЦИЯ")
        }
        
        category_emoji, category_text = category_map.get(email_category, ("📧", "НЕИЗВЕСТНО"))
        
        # Формируем заголовок с меткой источника в правом верхнем углу
        # Используем пробелы для выравнивания метки справа
        header_text = f"{category_emoji} *{category_text}*"
        # Добавляем метку источника справа (примерно 30 символов для выравнивания)
        header_line = f"{header_text:<30} {source_label}"
        
        # Формируем сообщение для канала лидов с меткой источника
        lead_message_parts = [
            f"{header_line}\n",
            f"*Источник:* {source}\n",
            f"*Название/Тема:* {title}\n",
            f"*Клиент:* {client_name}\n"
        ]
        
        if client_email:
            lead_message_parts.append(f"*Email:* {client_email}\n")
        if client_phone:
            lead_message_parts.append(f"*Телефон:* {client_phone}\n")
        
        if message:
            lead_message_parts.append(f"\n*Сообщение:*\n{message[:300]}{'...' if len(message) > 300 else ''}\n")
        
        # Добавляем информацию о классификации если есть
        if "classification_reason" in lead_info:
            confidence = lead_info.get("classification_confidence", 0.5)
            lead_message_parts.append(f"\n*Классификация:* {lead_info['classification_reason']} (уверенность: {confidence:.2f})")
        
        if score > 0:
            lead_message_parts.append(f"\n*Оценка:* {score:.2f} ({status})")
        if category:
            lead_message_parts.append(f"*Категория:* {category}")
        
        lead_message = "\n".join(lead_message_parts)
        
        await telegram_bot.send_message(
            chat_id=TELEGRAM_LEADS_CHANNEL_ID,
            text=lead_message,
            parse_mode="Markdown"
        )
        log.info(f"✅ {category_text} отправлен в канал HRAI_ANovoselova_Лиды")
        return True
    except Exception as e:
        log.error(f"❌ Ошибка отправки лида в канал: {e}")
        import traceback
        log.error(traceback.format_exc())
        return False


# ===================== СЦЕНАРИЙ 1: Новый лид с HR Time =====================

async def process_hrtime_order(order_id: str, order_data: Optional[Dict] = None, telegram_bot=None) -> Dict:
    """
    Полный workflow обработки нового заказа с HR Time
    
    Шаги:
    1. Парсинг данных заказа через LLM (текст ТЗ, бюджет, сроки, контакты)
    2. RAG + Классификация через LLM
    3. Валидация лида с уточняющими вопросами (если нужно)
    4. Действия для теплого лида:
       - Отправка отклика на HR Time
       - Отправка КП по email/Telegram
       - Создание проекта в WEEEK
       - Уведомление консультанта
    
    Args:
        order_id: ID заказа в HR Time
        order_data: Данные заказа (если не указано, загружается через API)
    
    Returns:
        Словарь с результатами обработки
    """
    if not HRTIME_AVAILABLE:
        return {"success": False, "error": "HR Time модуль недоступен"}
    
    try:
        # Шаг 1: Парсинг данных заказа через LLM
        log.info(f"📥 [Сценарий 1] Парсинг заказа {order_id}...")
        
        parsed_order = None
        if PARSER_AVAILABLE:
            try:
                parser = HRTimeOrderParser()
                parsed_result = await parser.parse_order(order_id, order_data)
                if parsed_result.get("success"):
                    parsed_order = parsed_result
                    log.info(f"✅ [Сценарий 1] Заказ распарсен через LLM")
                else:
                    log.warning(f"⚠️ [Сценарий 1] Ошибка парсинга: {parsed_result.get('error')}")
            except Exception as e:
                log.error(f"❌ [Сценарий 1] Ошибка парсера: {e}")
        
        # Получаем данные заказа, если не были распарсены
        if order_data is None:
            order_data = await get_order_details(order_id)
            if not order_data:
                return {"success": False, "error": "Не удалось получить данные заказа"}
        
        # Извлекаем данные (используем распарсенные, если доступны)
        if parsed_order and parsed_order.get("parsed"):
            parsed = parsed_order["parsed"]
            title = order_data.get("title", "")
            description = parsed.get("requirements", order_data.get("description", ""))
            budget_text = parsed.get("budget", {}).get("text", str(order_data.get("budget", "")))
            deadline_text = parsed.get("deadline", {}).get("text", str(order_data.get("deadline", "")))
            contacts = parsed.get("contacts", {})
            client_name = contacts.get("full_name", order_data.get("client", {}).get("name", "Клиент"))
            client_email = contacts.get("email", order_data.get("client", {}).get("email", ""))
            client_phone = contacts.get("phone", order_data.get("client", {}).get("phone", ""))
        else:
            # Fallback на старый способ
            title = order_data.get("title", "")
            description = order_data.get("description", "")
            budget_text = str(order_data.get("budget", ""))
            deadline_text = str(order_data.get("deadline", ""))
            client = order_data.get("client", {})
            client_name = client.get("name", "Клиент")
            client_email = client.get("email", "")
            client_phone = client.get("phone", "")
        
        # Формируем полный текст запроса для анализа
        request_text = f"{title}\n\n{description}"
        if budget_text:
            request_text += f"\nБюджет: {budget_text}"
        if deadline_text:
            request_text += f"\nСрок: {deadline_text}"
        
        # Шаг 2: RAG + Классификация
        log.info(f"🔍 [Сценарий 1] Анализ заказа {order_id}: {title}")
        
        rag_chain = get_rag_chain()
        rag_context = ""
        if rag_chain:
            try:
                rag_result = await rag_chain.query(request_text, use_rag=True, top_k=5)
                rag_context = rag_result.get("answer", "")
                log.info(f"✅ [Сценарий 1] RAG анализ завершен")
            except Exception as e:
                log.error(f"❌ [Сценарий 1] Ошибка RAG анализа: {e}")
        
        classification = await classify_request(request_text)
        category = classification.get("category", "другое")
        log.info(f"✅ [Сценарий 1] Заказ классифицирован как: {category}")
        
        # Шаг 3: Валидация лида с уточняющими вопросами
        validation_result = None
        if VALIDATOR_AVAILABLE:
            try:
                validator = HRTimeLeadValidator()
                validation_result = await validator.validate_lead_with_questions(
                    lead_request=request_text,
                    parsed_order=parsed_order
                )
                validation = validation_result.get("validation", {})
                
                # Если нужны уточняющие вопросы, пытаемся их задать
                if validation_result.get("needs_clarification") and validation_result.get("questions"):
                    questions = validation_result.get("questions", [])
                    log.info(f"💬 [Сценарий 1] Нужны уточняющие вопросы: {len(questions)}")
                    
                    # Пытаемся задать вопросы (placeholder)
                    questions_result = await validator.ask_clarification_questions(
                        order_id=order_id,
                        questions=questions,
                        client_email=client_email
                    )
                    
                    if questions_result.get("success"):
                        log.info(f"✅ [Сценарий 1] Вопросы отправлены через {questions_result.get('method')}")
                    else:
                        log.warning(f"⚠️ [Сценарий 1] Не удалось отправить вопросы автоматически")
                        # Сохраняем вопросы для ручной отправки
                        validation_result["questions_for_manual"] = questions_result.get("questions_text", "")
            except Exception as e:
                log.error(f"❌ [Сценарий 1] Ошибка валидатора: {e}")
                validation = await validate_lead(request_text)
        else:
            validation = await validate_lead(request_text)
        
        if not validation_result:
            validation = await validate_lead(request_text)
        else:
            validation = validation_result.get("validation", {})
        
        score = validation.get("score", 0)
        status = validation.get("status", "cold")
        
        log.info(f"✅ [Сценарий 1] Лид валидирован: score={score}, status={status}")
        
        result = {
            "success": True,
            "order_id": order_id,
            "parsed_order": parsed_order,
            "classification": classification,
            "validation": validation,
            "validation_result": validation_result,
            "proposal_sent": False,
            "weeek_project_created": False,
            "notification_sent": False
        }
        
        # Определяем источник данных (нужно для всех лидов)
        source = order_data.get("source", "api")
        source_text = "📢 Канал: @HRTime_bot" if source == "telegram_channel" else "🌐 Источник: HR Time API"
        
        # Шаг 4: Действия для теплого лида (score > 0.6 или status == "warm")
        if score > 0.6 or status == "warm":
            log.info(f"🔥 [Сценарий 1] Теплый лид! Выполняем действия...")
            
            # 4a. Генерация КП
            proposal = await generate_proposal(
                lead_request=request_text,
                lead_contact={
                    "name": client_name,
                    "email": client_email,
                    "phone": client_phone
                },
                rag_results=None  # RAG уже использован выше
            )
            
            # 4b. Отправка отклика на HR Time
            proposal_sent = await send_proposal(order_id, proposal)
            result["proposal_sent"] = proposal_sent
            
            if proposal_sent:
                log.info(f"✅ [Сценарий 1] Отклик отправлен на HR Time")
            
            # 4c. Отправка КП по email (если есть email)
            if client_email:
                try:
                    await send_email(
                        to_email=client_email,
                        subject=f"Коммерческое предложение: {title}",
                        body=proposal,
                        is_html=False
                    )
                    log.info(f"✅ [Сценарий 1] КП отправлено на email: {client_email}")
                except Exception as e:
                    log.error(f"❌ [Сценарий 1] Ошибка отправки email: {e}")
            
            # 4d. Создание проекта в WEEEK
            if WEEEK_AVAILABLE:
                project_name = f"{title} — HR Time"
                project_description = f"Заказ с HR Time\n\n{description}\n\nКлиент: {client_name}\nEmail: {client_email}\nТелефон: {client_phone}"
                
                weeek_project = await create_project(
                    name=project_name,
                    description=project_description
                )
                
                if weeek_project:
                    project_id = weeek_project.get("id")
                    if project_id:  # Проверяем, что project_id не None
                        result["weeek_project_id"] = project_id
                        result["weeek_project_created"] = True
                        log.info(f"✅ [Сценарий 1] Проект создан в WEEEK: {project_id}")
                        
                        # Автоматически устанавливаем статус "new" для нового проекта
                        from services.helpers.weeek_helper import update_project_status
                        status_updated = await update_project_status(str(project_id), "new")
                        if status_updated:
                            log.info(f"✅ [Сценарий 1] Статус проекта установлен на 'new'")
                        
                        # Создаем задачу "Согласовать КП"
                        await create_task(
                            project_id=str(project_id),
                            title="Согласовать КП",
                            description="Проверить и согласовать черновик коммерческого предложения"
                        )
                        log.info(f"✅ [Сценарий 1] Задача создана в WEEEK")
                    else:
                        log.warning(f"⚠️ [Сценарий 1] Проект создан, но ID не получен")
                        result["weeek_project_created"] = False
            
            # 4e. Уведомление консультанта в Telegram
            
            notification_parts = [
                f"🔥 *Новый теплый лид с HR Time*\n",
                f"{source_text}\n",
                f"*Заказ:* {title}",
                f"*Клиент:* {client_name}",
                f"*Email:* {client_email or 'Не указан'}",
                f"*Телефон:* {client_phone or 'Не указан'}",
                f"*Оценка:* {score:.2f} ({status})",
                f"*Категория:* {category}\n"
            ]
            
            # Добавляем информацию о распарсенных данных
            if parsed_order and parsed_order.get("parsed"):
                parsed = parsed_order["parsed"]
                if parsed.get("budget", {}).get("amount", 0) > 0:
                    budget = parsed["budget"]
                    notification_parts.append(f"*Бюджет:* {budget['amount']:.0f} {budget.get('currency', 'RUB')}")
                if parsed.get("deadline", {}).get("date"):
                    notification_parts.append(f"*Срок:* {parsed['deadline']['date']}")
            
            notification_parts.extend([
                "",
                "✅ Отклик и черновик КП отправлены",
                f"{'✅ Проект создан в WEEEK' if result.get('weeek_project_created') else '❌ Ошибка создания проекта в WEEEK'}\n",
                "Требует вашего ознакомления с КП."
            ])
            
            notification_text = "\n".join(notification_parts)
            
            result["notification_text"] = notification_text
            result["notification_sent"] = True  # Отправка будет выполнена вызывающим кодом
            log.info(f"✅ [Сценарий 1] Уведомление подготовлено")
            
            # Отправка лида в канал HRAI_ANovoselova_Лиды
            if telegram_bot:
                lead_info = {
                    "source": source_text,
                    "title": title,
                    "client_name": client_name,
                    "client_email": client_email,
                    "client_phone": client_phone,
                    "message": description,
                    "score": score,
                    "status": status,
                    "category": category
                }
                await send_lead_to_channel(telegram_bot, lead_info)
        else:
            log.info(f"❄️ [Сценарий 1] Холодный лид (score={score}). Действия не выполняются.")
            # Отправляем холодный лид в канал тоже
            if telegram_bot:
                lead_info = {
                    "source": source_text,
                    "title": title,
                    "client_name": client_name,
                    "client_email": client_email,
                    "client_phone": client_phone,
                    "message": description,
                    "score": score,
                    "status": status,
                    "category": category
                }
                await send_lead_to_channel(telegram_bot, lead_info)
        
        return result
        
    except Exception as e:
        log.error(f"❌ [Сценарий 1] Ошибка обработки заказа: {e}")
        import traceback
        log.error(f"❌ Traceback: {traceback.format_exc()}")
        return {"success": False, "error": str(e)}


# ===================== СЦЕНАРИЙ 2: Прямое письмо от лида =====================

async def process_lead_email(email_data: Dict, require_approval: bool = True, telegram_bot=None) -> Dict:
    """
    Обработка прямого письма от лида
    
    Шаги:
    1. Чтение письма
    2. Анализ и классификация
    3. Генерация черновика ответа с элементами КП
    4. Подтверждение консультанта в Telegram (если требуется)
    5. Отправка после подтверждения
    6. Создание проекта в WEEEK
    
    Args:
        email_data: Данные письма (subject, body, from, to)
        require_approval: Требовать ли подтверждение консультанта
        telegram_bot: Экземпляр Telegram бота для отправки подтверждения
    
    Returns:
        Словарь с результатами обработки
    """
    # Извлекаем данные письма (в начале для гарантированной отправки в канал)
    subject = email_data.get("subject", "")
    body = email_data.get("body", "")
    from_addr = email_data.get("from", "")
    request_text = f"{subject}\n\n{body}"
    
    # Классифицируем email через LLM перед отправкой в канал (три категории)
    classification = None
    if LLM_AVAILABLE:
        try:
            classification = await classify_email_type(subject, body)
            log.info(f"✅ [Сценарий 2] Email классифицирован как {classification.get('category', 'unknown')}")
        except Exception as e:
            log.error(f"❌ [Сценарий 2] Ошибка классификации email: {e}")
            classification = {"category": "service", "confidence": 0.5, "reason": "Ошибка классификации"}
    
    # Отправляем ВСЕ письма в канал сразу (до всех проверок и обработки)
    # Это гарантирует, что все письма попадут в канал, даже если модуль недоступен или произойдет ошибка
    if telegram_bot:
        try:
            lead_info = {
                "source": "📧 Email",
                "title": subject or "Без темы",
                "client_name": from_addr.split("@")[0] if from_addr else "Неизвестно",
                "client_email": from_addr or "",
                "client_phone": "",
                "message": body or "",
                "score": 0,
                "status": "info",  # Будет обновлен после обработки
                "category": "обработка...",
                "email_category": classification.get("category", "service") if classification else "service",
                "classification_reason": classification.get("reason", "") if classification else "",
                "classification_confidence": classification.get("confidence", 0.5) if classification else 0.5
            }
            await send_lead_to_channel(telegram_bot, lead_info)
            log.info(f"✅ [Сценарий 2] Письмо отправлено в канал лидов с категорией {lead_info['email_category']}")
        except Exception as e:
            log.error(f"❌ [Сценарий 2] Ошибка отправки письма в канал: {e}")
    
    # Проверка доступности модуля email (после отправки в канал)
    if not EMAIL_AVAILABLE:
        return {"success": False, "error": "Email модуль недоступен", "sent_to_channel": True}
    
    try:
        # Шаг 1: Классификация письма
        email_type = await classify_email(email_data)
        log.info(f"📧 [Сценарий 2] Письмо классифицировано как: {email_type}")
        
        # Шаг 2: Анализ запроса
        
        # RAG анализ
        rag_chain = get_rag_chain()
        rag_context = ""
        if rag_chain:
            try:
                rag_result = await rag_chain.query(request_text, use_rag=True, top_k=5)
                rag_context = rag_result.get("answer", "")
            except Exception as e:
                log.error(f"❌ [Сценарий 2] Ошибка RAG анализа: {e}")
        
        classification = await classify_request(request_text)
        log.info(f"✅ [Сценарий 2] Запрос классифицирован: {classification.get('category')}")
        
        # Шаг 3: Генерация черновика ответа с элементами КП
        proposal = await generate_proposal(
            lead_request=request_text,
            lead_contact={"email": from_addr, "name": from_addr.split("@")[0]},
            rag_results=None
        )
        
        log.info(f"✅ [Сценарий 2] Черновик ответа сгенерирован")
        
        result = {
            "success": True,
            "email_from": from_addr,
            "email_subject": subject,
            "classification": classification,
            "draft_proposal": proposal,
            "requires_approval": require_approval,
            "approved": False,
            "email_sent": False,
            "weeek_project_created": False
        }
        
        # Шаг 4: Подтверждение консультанта (если требуется)
        if require_approval and telegram_bot and TELEGRAM_CONSULTANT_CHAT_ID:
            approval_text = (
                f"📧 *Новое письмо от лида*\n\n"
                f"*От:* {from_addr}\n"
                f"*Тема:* {subject}\n\n"
                f"*Подготовлен ответ:*\n\n"
                f"{proposal[:500]}...\n\n"
                f"Отправить?"
            )
            
            # В реальной реализации здесь нужно добавить inline кнопки для подтверждения
            # Пока просто отправляем уведомление
            try:
                await telegram_bot.send_message(
                    chat_id=TELEGRAM_CONSULTANT_CHAT_ID,
                    text=approval_text,
                    parse_mode="Markdown"
                )
                result["approval_requested"] = True
                log.info(f"✅ [Сценарий 2] Запрос на подтверждение отправлен консультанту")
            except Exception as e:
                log.error(f"❌ [Сценарий 2] Ошибка отправки запроса на подтверждение: {e}")
                # Продолжаем без подтверждения
                result["approved"] = True
        else:
            # Без подтверждения - сразу отправляем
            result["approved"] = True
        
        # Шаг 5: Отправка ОТКЛЮЧЕНА - письма не должны отправляться автоматически
        # Письма только отправляются в канал для ручной обработки
        log.info(f"⚠️ [Сценарий 2] Автоматическая отправка ответа ОТКЛЮЧЕНА")
        log.info(f"⚠️ [Сценарий 2] Письмо отправлено только в канал, ответ не отправлен")
        result["email_sent"] = False
        result["auto_reply_disabled"] = True
        
        # Шаг 6: Создание проекта в WEEEK
        if WEEEK_AVAILABLE and result.get("email_sent"):
            project_name = f"{subject[:50]} — Email"
            project_description = f"Письмо от: {from_addr}\n\n{body[:500]}"
            
            weeek_project = await create_project(
                name=project_name,
                description=project_description
            )
            
            if weeek_project:
                project_id = weeek_project.get("id")
                if project_id:  # Проверяем, что project_id не None
                    result["weeek_project_id"] = project_id
                    result["weeek_project_created"] = True
                    log.info(f"✅ [Сценарий 2] Проект создан в WEEEK: {project_id}")
                    
                    # Автоматически устанавливаем статус "new" для нового проекта
                    from services.helpers.weeek_helper import update_project_status
                    status_updated = await update_project_status(str(project_id), "new")
                    if status_updated:
                        log.info(f"✅ [Сценарий 2] Статус проекта установлен на 'new'")
                else:
                    log.warning(f"⚠️ [Сценарий 2] Проект создан, но ID не получен")
                    result["weeek_project_created"] = False
        
        # Если письмо не является новым лидом, возвращаем результат (письмо уже отправлено в канал выше)
        if email_type != "new_lead":
            return {"success": False, "error": "Письмо не является новым лидом", "type": email_type, "sent_to_channel": True}
        
        return result
        
    except Exception as e:
        log.error(f"❌ [Сценарий 2] Ошибка обработки письма: {e}")
        import traceback
        log.error(f"❌ Traceback: {traceback.format_exc()}")
        return {"success": False, "error": str(e)}


# ===================== СЦЕНАРИЙ 3: Заявка с сайта-визитки (Telegram-бот) =====================

async def process_telegram_lead(
    user_message: str,
    user_id: int,
    user_name: str,
    telegram_bot=None
) -> Dict:
    """
    Обработка заявки от лида через Telegram бота
    
    Шаги:
    1. Приветствие и анализ запроса
    2. Обработка по стандартной цепочке (RAG + классификация + валидация)
    3. Коммуникация для уточнения деталей
    4. При положительной валидации - создание проекта в WEEEK и уведомление
    
    Args:
        user_message: Сообщение от пользователя
        user_id: ID пользователя в Telegram
        user_name: Имя пользователя
        telegram_bot: Экземпляр Telegram бота для отправки сообщений
    
    Returns:
        Словарь с результатами обработки
    """
    try:
        # Шаг 1: Приветствие и анализ
        log.info(f"💬 [Сценарий 3] Обработка запроса от пользователя {user_id}: {user_name}")
        
        # RAG анализ
        rag_chain = get_rag_chain()
        rag_response = ""
        if rag_chain:
            try:
                rag_result = await rag_chain.query(user_message, use_rag=True, top_k=5)
                rag_response = rag_result.get("answer", "")
                log.info(f"✅ [Сценарий 3] RAG анализ завершен")
            except Exception as e:
                log.error(f"❌ [Сценарий 3] Ошибка RAG анализа: {e}")
        
        # Классификация и валидация
        classification = await classify_request(user_message)
        validation = await validate_lead(user_message)
        
        score = validation.get("score", 0)
        status = validation.get("status", "cold")
        category = classification.get("category", "другое")
        
        log.info(f"✅ [Сценарий 3] Запрос классифицирован: {category}, валидация: {score} ({status})")
        
        result = {
            "success": True,
            "user_id": user_id,
            "user_name": user_name,
            "user_message": user_message,
            "rag_response": rag_response,
            "classification": classification,
            "validation": validation,
            "weeek_project_created": False,
            "auto_reply_sent": False
        }
        
        # Шаг 2: Немедленный автоматический ответ с подтверждением получения заявки
        if telegram_bot:
            auto_reply_text = (
                f"✅ Спасибо за вашу заявку, {user_name}!\n\n"
                f"Мы получили ваш запрос и уже обрабатываем его. "
                f"Наш консультант свяжется с вами в ближайшее время.\n\n"
                f"Ваш запрос: {user_message[:100]}{'...' if len(user_message) > 100 else ''}"
            )
            try:
                await telegram_bot.send_message(
                    chat_id=user_id,
                    text=auto_reply_text
                )
                result["auto_reply_sent"] = True
                log.info(f"✅ [Сценарий 3] Автоматический ответ отправлен пользователю {user_id}")
            except Exception as e:
                log.error(f"❌ [Сценарий 3] Ошибка отправки автоответа: {e}")
        
        # Шаг 3: Обработка по стандартной цепочке (RAG + классификация + валидация)
        # Ответ пользователю с деталями будет отправлен через основной обработчик бота
        
        # Шаг 4: При положительной валидации создаем проект в WEEEK
        if (score > 0.6 or status == "warm") and WEEEK_AVAILABLE:
            project_name = f"{user_name} — Telegram запрос"
            project_description = f"Запрос через Telegram бота\n\n{user_message}\n\nПользователь: {user_name} (ID: {user_id})"
            
            weeek_project = await create_project(
                name=project_name,
                description=project_description
            )
            
            if weeek_project:
                project_id = weeek_project.get("id")
                if project_id:  # Проверяем, что project_id не None
                    result["weeek_project_id"] = project_id
                    result["weeek_project_created"] = True
                    log.info(f"✅ [Сценарий 3] Проект создан в WEEEK: {project_id}")
                    
                    # Автоматически устанавливаем статус "new" для нового проекта
                    from services.helpers.weeek_helper import update_project_status
                    status_updated = await update_project_status(str(project_id), "new")
                    if status_updated:
                        log.info(f"✅ [Сценарий 3] Статус проекта установлен на 'new'")
                else:
                    log.warning(f"⚠️ [Сценарий 3] Проект создан, но ID не получен")
                    result["weeek_project_created"] = False
                
                # Уведомление консультанта
                if telegram_bot and TELEGRAM_CONSULTANT_CHAT_ID:
                    notification_text = (
                        f"💬 *Новый лид через Telegram*\n\n"
                        f"*Пользователь:* {user_name} (ID: {user_id})\n"
                        f"*Запрос:* {user_message[:200]}...\n"
                        f"*Оценка:* {score:.2f} ({status})\n"
                        f"*Категория:* {category}\n\n"
                        f"{'✅ Проект создан в WEEEK' if result.get('weeek_project_created') else '❌ Ошибка создания проекта в WEEEK'}"
                    )
                    try:
                        await telegram_bot.send_message(
                            chat_id=TELEGRAM_CONSULTANT_CHAT_ID,
                            text=notification_text,
                            parse_mode="Markdown"
                        )
                        log.info(f"✅ [Сценарий 3] Консультант уведомлен")
                    except Exception as e:
                        log.error(f"❌ [Сценарий 3] Ошибка уведомления консультанта: {e}")
            
            # Отправка лида в канал HRAI_ANovoselova_Лиды (для теплых лидов)
            if telegram_bot:
                lead_info = {
                    "source": "💬 Telegram бот",
                    "title": f"Запрос от {user_name}",
                    "client_name": user_name,
                    "client_email": "",
                    "client_phone": "",
                    "message": user_message,
                    "score": score,
                    "status": status,
                    "category": category
                }
                await send_lead_to_channel(telegram_bot, lead_info)
        else:
            # Отправляем холодный лид в канал тоже
            if telegram_bot:
                lead_info = {
                    "source": "💬 Telegram бот",
                    "title": f"Запрос от {user_name}",
                    "client_name": user_name,
                    "client_email": "",
                    "client_phone": "",
                    "message": user_message,
                    "score": score,
                    "status": status,
                    "category": category
                }
                await send_lead_to_channel(telegram_bot, lead_info)
        
        return result
        
    except Exception as e:
        log.error(f"❌ [Сценарий 3] Ошибка обработки Telegram лида: {e}")
        import traceback
        log.error(f"❌ Traceback: {traceback.format_exc()}")
        return {"success": False, "error": str(e)}


# ===================== СЦЕНАРИЙ 4: Напоминание и суммаризация по проекту =====================

async def check_upcoming_deadlines(telegram_bot=None, days_ahead: int = 1) -> List[Dict]:
    """
    Мониторинг задач с приближающимися дедлайнами и отправка напоминаний
    
    Args:
        telegram_bot: Экземпляр Telegram бота для отправки напоминаний
        days_ahead: Количество дней вперед для проверки (1 = завтра и сегодня)
    
    Returns:
        Список задач с приближающимися дедлайнами
    """
    if not WEEEK_AVAILABLE:
        return []
    
    try:
        log.info(f"⏰ [Сценарий 4] Проверка дедлайнов на ближайшие {days_ahead} дней")
        
        # Получаем задачи с дедлайнами
        upcoming_tasks = await get_project_deadlines(days_ahead=days_ahead + 1)  # +1 чтобы захватить сегодня
        
        if not upcoming_tasks:
            log.info(f"✅ [Сценарий 4] Нет задач с дедлайнами на ближайшие {days_ahead} дней")
            return []
        
        # Фильтруем задачи с дедлайном завтра или сегодня
        today = datetime.now().date()
        tomorrow = today + timedelta(days=1)
        
        urgent_tasks = []
        for task in upcoming_tasks:
            due_date_str = task.get("due_date")
            if not due_date_str:
                continue
            
            try:
                # Парсим дату (может быть в разных форматах)
                if "T" in due_date_str:
                    due_date = datetime.fromisoformat(due_date_str.replace("Z", "+00:00")).date()
                else:
                    due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()
                
                # Проверяем, попадает ли в диапазон (сегодня-завтра)
                if due_date <= tomorrow:
                    urgent_tasks.append(task)
            except Exception as e:
                log.warning(f"⚠️ [Сценарий 4] Ошибка парсинга даты {due_date_str}: {e}")
        
        if urgent_tasks and telegram_bot and TELEGRAM_CONSULTANT_CHAT_ID:
            # Формируем сообщение с напоминаниями
            reminder_text = "⏰ *Напоминание о дедлайнах*\n\n"
            
            for task in urgent_tasks[:10]:  # Максимум 10 задач
                task_name = task.get("name", "Задача")
                due_date_str = task.get("due_date", "")
                project_id = task.get("project_id", "")
                
                try:
                    if "T" in due_date_str:
                        due_date = datetime.fromisoformat(due_date_str.replace("Z", "+00:00")).date()
                    else:
                        due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()
                    
                    days_left = (due_date - today).days
                    if days_left == 0:
                        urgency = "❗ СЕГОДНЯ"
                    elif days_left == 1:
                        urgency = "⚠️ ЗАВТРА"
                    else:
                        urgency = f"📅 Через {days_left} дней"
                    
                    reminder_text += f"{urgency}: *{task_name}*\n"
                    if project_id:
                        reminder_text += f"  Проект ID: {project_id}\n"
                    reminder_text += "\n"
                except:
                    reminder_text += f"📅 *{task_name}* (дата: {due_date_str})\n\n"
            
            reminder_text += "\nСвяжитесь с клиентом для обновления статуса."
            
            try:
                await telegram_bot.send_message(
                    chat_id=TELEGRAM_CONSULTANT_CHAT_ID,
                    text=reminder_text,
                    parse_mode="Markdown"
                )
                log.info(f"✅ [Сценарий 4] Напоминания отправлены: {len(urgent_tasks)} задач")
            except Exception as e:
                log.error(f"❌ [Сценарий 4] Ошибка отправки напоминаний: {e}")
        
        return urgent_tasks
        
    except Exception as e:
        log.error(f"❌ [Сценарий 4] Ошибка проверки дедлайнов: {e}")
        import traceback
        log.error(f"❌ Traceback: {traceback.format_exc()}")
        return []


async def summarize_project_by_name(project_name: str, conversations: List[Dict]) -> Dict:
    """
    Суммаризация проекта по запросу консультанта
    
    Args:
        project_name: Название проекта
        conversations: Список сообщений переписки по проекту
    
    Returns:
        Словарь с суммаризацией
    """
    try:
        from summary_helper import summarize_project_conversation
        
        log.info(f"📊 [Сценарий 4] Генерация суммаризации для проекта: {project_name}")
        
        summary = await summarize_project_conversation(
            conversations=conversations,
            project_name=project_name
        )
        
        return {
            "success": True,
            "project_name": project_name,
            "summary": summary
        }
        
    except Exception as e:
        log.error(f"❌ [Сценарий 4] Ошибка суммаризации проекта: {e}")
        return {
            "success": False,
            "error": str(e)
        }


# ===================== Фоновая задача для мониторинга =====================

async def start_deadline_monitor(telegram_bot, check_interval_hours: int = 24):
    """
    Запуск фоновой задачи для мониторинга дедлайнов
    
    Args:
        telegram_bot: Экземпляр Telegram бота
        check_interval_hours: Интервал проверки в часах (по умолчанию 24 = раз в день)
    """
    log.info(f"🔄 [Сценарий 4] Запуск мониторинга дедлайнов (интервал: {check_interval_hours} часов)")
    
    while True:
        try:
            await check_upcoming_deadlines(telegram_bot=telegram_bot, days_ahead=1)
            await asyncio.sleep(check_interval_hours * 3600)  # Переводим часы в секунды
        except Exception as e:
            log.error(f"❌ [Сценарий 4] Ошибка в фоновой задаче мониторинга: {e}")
            await asyncio.sleep(3600)  # При ошибке ждем час перед повторной попыткой



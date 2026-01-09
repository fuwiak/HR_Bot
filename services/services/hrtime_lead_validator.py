"""
HR Time Lead Validator Service
Сервис для валидации лидов с возможностью задавать уточняющие вопросы
"""
import logging
from typing import Dict, Optional, List

log = logging.getLogger()

# Импорты
try:
    from services.agents.lead_processor import validate_lead
    from services.helpers.llm_api import LLMClient
    LLM_AVAILABLE = True
except ImportError as e:
    LLM_AVAILABLE = False
    log.warning(f"⚠️ LLM модуль недоступен: {e}")


# ===================== PROMPTS =====================

VALIDATION_QUESTIONS_PROMPT = """
Ты AI-ассистент для валидации лидов. Твоя задача - определить, нужны ли уточняющие вопросы для оценки лида.

Проанализируй запрос лида и определи:
1. Есть ли четкое техническое задание?
2. Указан ли бюджет или примерные рамки?
3. Указаны ли сроки?
4. Достаточно ли информации для оценки проекта?

Если информации недостаточно, сформулируй 1-3 уточняющих вопроса, которые помогут оценить лид.

Ответь ТОЛЬКО в формате JSON:
{{
    "needs_clarification": true/false,
    "questions": [
        "Вопрос 1",
        "Вопрос 2"
    ],
    "missing_info": ["бюджет", "сроки", "ТЗ"],
    "confidence": 0.0-1.0
}}

Запрос лида:
{{lead_request}}
"""


class HRTimeLeadValidator:
    """Сервис для валидации лидов с уточняющими вопросами"""
    
    def __init__(self):
        self.llm_client = None
        if LLM_AVAILABLE:
            try:
                self.llm_client = LLMClient()
            except Exception as e:
                log.error(f"❌ Ошибка инициализации LLMClient: {e}")
                self.llm_client = None
    
    async def validate_lead_with_questions(
        self,
        lead_request: str,
        parsed_order: Optional[Dict] = None
    ) -> Dict:
        """
        Валидирует лид и определяет, нужны ли уточняющие вопросы
        
        Args:
            lead_request: Текст запроса лида
            parsed_order: Распарсенные данные заказа (опционально)
        
        Returns:
            Словарь с результатами валидации:
            {
                "validation": Dict,  # Результат стандартной валидации
                "needs_clarification": bool,
                "questions": List[str],
                "missing_info": List[str],
                "can_ask_questions": bool  # Можно ли задавать вопросы на платформе
            }
        """
        try:
            # Стандартная валидация
            log.info("🔍 [Lead Validator] Валидация лида...")
            validation = await validate_lead(lead_request)
            
            # Определяем, нужны ли уточняющие вопросы
            needs_clarification = False
            questions = []
            missing_info = []
            
            # Проверяем распарсенные данные
            if parsed_order:
                parsed = parsed_order.get("parsed", {})
                
                # Проверяем наличие ключевой информации
                requirements = parsed.get("requirements", "")
                budget = parsed.get("budget", {})
                deadline = parsed.get("deadline", {})
                
                if not requirements or len(requirements.strip()) < 50:
                    needs_clarification = True
                    missing_info.append("ТЗ")
                    questions.append("Можете ли вы уточнить детали технического задания?")
                
                if not budget.get("amount", 0) and not budget.get("text"):
                    needs_clarification = True
                    missing_info.append("бюджет")
                    questions.append("Какой примерный бюджет на проект?")
                
                if not deadline.get("date") and not deadline.get("text"):
                    needs_clarification = True
                    missing_info.append("сроки")
                    questions.append("Какие сроки реализации проекта?")
            
            # Если LLM доступен, используем его для генерации вопросов
            if self.llm_client and needs_clarification:
                try:
                    prompt = VALIDATION_QUESTIONS_PROMPT.replace("{{lead_request}}", lead_request)
                    response = await self.llm_client.generate(
                        prompt=prompt,
                        system_prompt="Ты помощник для валидации лидов. Отвечай только в формате JSON.",
                        temperature=0.5,
                        max_tokens=1000
                    )
                    
                    if not response.error:
                        import json
                        try:
                            content = response.content.strip()
                            if "```json" in content:
                                content = content.split("```json")[1].split("```")[0].strip()
                            elif "```" in content:
                                content = content.split("```")[1].split("```")[0].strip()
                            
                            if "{" in content and "}" in content:
                                json_start = content.find("{")
                                json_end = content.rfind("}") + 1
                                json_str = content[json_start:json_end]
                                llm_result = json.loads(json_str)
                                
                                if llm_result.get("needs_clarification"):
                                    needs_clarification = True
                                    if llm_result.get("questions"):
                                        questions = llm_result["questions"]
                                    if llm_result.get("missing_info"):
                                        missing_info = llm_result["missing_info"]
                        except:
                            pass  # Используем вопросы, сгенерированные выше
                except Exception as e:
                    log.warning(f"⚠️ [Lead Validator] Ошибка генерации вопросов через LLM: {e}")
            
            # Определяем, можно ли задавать вопросы на платформе
            # Пока это placeholder - нужно проверить API HR Time
            can_ask_questions = False  # TODO: Проверить возможность отправки сообщений на платформе
            
            result = {
                "validation": validation,
                "needs_clarification": needs_clarification,
                "questions": questions[:3],  # Максимум 3 вопроса
                "missing_info": missing_info,
                "can_ask_questions": can_ask_questions
            }
            
            log.info(f"✅ [Lead Validator] Валидация завершена: needs_clarification={needs_clarification}")
            return result
            
        except Exception as e:
            log.error(f"❌ [Lead Validator] Ошибка валидации лида: {e}")
            import traceback
            log.error(f"❌ Traceback: {traceback.format_exc()}")
            return {
                "validation": {"score": 0.5, "status": "unknown"},
                "needs_clarification": False,
                "questions": [],
                "missing_info": [],
                "can_ask_questions": False,
                "error": str(e)
            }
    
    async def ask_clarification_questions(
        self,
        order_id: str,
        questions: List[str],
        client_email: Optional[str] = None
    ) -> Dict:
        """
        Задает уточняющие вопросы лиду (placeholder - пока не реализовано)
        
        Args:
            order_id: ID заказа
            questions: Список вопросов
            client_email: Email клиента (для отправки по email, если нельзя на платформе)
        
        Returns:
            Словарь с результатами:
            {
                "success": bool,
                "method": "platform" | "email" | "none",
                "error": Optional[str]
            }
        """
        # TODO: Реализовать отправку вопросов через HR Time API
        # Пока это placeholder
        
        log.info(f"💬 [Lead Validator] Попытка задать вопросы по заказу {order_id}")
        
        # Пробуем отправить через HR Time API (если доступно)
        try:
            from services.helpers.hrtime_helper import send_message
            
            # Формируем текст с вопросами
            questions_text = "Здравствуйте! Для более точной оценки проекта, уточните, пожалуйста:\n\n"
            for i, question in enumerate(questions, 1):
                questions_text += f"{i}. {question}\n"
            
            # Пробуем отправить через платформу
            sent = await send_message(order_id, questions_text, recipient_email=client_email)
            
            if sent:
                return {
                    "success": True,
                    "method": "platform" if not client_email else "email",
                    "error": None
                }
        except Exception as e:
            log.warning(f"⚠️ [Lead Validator] Не удалось отправить вопросы: {e}")
        
        # Если не удалось отправить, возвращаем информацию для ручной отправки
        return {
            "success": False,
            "method": "none",
            "error": "Не удалось отправить вопросы автоматически. Требуется ручная отправка.",
            "questions_text": "\n".join([f"{i+1}. {q}" for i, q in enumerate(questions)])
        }

"""
HR Time Order Adapter
Адаптер для парсинга и структурирования данных заказа с HR Time через LLM
"""
import logging
from typing import Dict, Optional, List
from datetime import datetime

log = logging.getLogger()

# Импорты для LLM
try:
    from services.helpers.llm_api import LLMClient
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False
    log.warning("⚠️ LLM модуль недоступен")


# ===================== PROMPTS =====================

ORDER_PARSING_PROMPT = """
Ты AI-ассистент для парсинга заказов с платформы HR Time. Твоя задача - извлечь структурированные данные из текста заказа.

Извлеки следующую информацию:
1. Текст ТЗ (техническое задание) - полный текст описания задачи
2. Бюджет - числовое значение и валюта (если указано)
3. Сроки - даты или временные рамки (если указано)
4. Контакты:
   - ФИО клиента (полное имя)
   - Телефон (в любом формате)
   - Email (если указан)

Ответь ТОЛЬКО в формате JSON:
{{
    "requirements": "полный текст ТЗ",
    "budget": {{
        "amount": 0.0,
        "currency": "RUB",
        "text": "текст с бюджетом из заказа"
    }},
    "deadline": {{
        "date": "YYYY-MM-DD или null",
        "text": "текст со сроками из заказа"
    }},
    "contacts": {{
        "full_name": "ФИО клиента",
        "phone": "телефон",
        "email": "email или null"
    }}
}}

Если какая-то информация не найдена, используй null для полей.

Текст заказа:
{{order_text}}
"""


# ===================== ADAPTER CLASS =====================

class HRTimeOrderAdapter:
    """Адаптер для парсинга заказов HR Time через LLM"""
    
    def __init__(self):
        self.llm_client = None
        if LLM_AVAILABLE:
            try:
                self.llm_client = LLMClient()
            except Exception as e:
                log.error(f"❌ Ошибка инициализации LLMClient: {e}")
                self.llm_client = None
    
    async def parse_order(self, order_data: Dict) -> Dict:
        """
        Парсит данные заказа через LLM, извлекая структурированную информацию
        
        Args:
            order_data: Словарь с данными заказа от HR Time API
        
        Returns:
            Словарь с распарсенными данными:
            {
                "requirements": str,
                "budget": {"amount": float, "currency": str, "text": str},
                "deadline": {"date": str, "text": str},
                "contacts": {"full_name": str, "phone": str, "email": str},
                "raw_data": Dict  # Исходные данные
            }
        """
        if not self.llm_client:
            log.warning("⚠️ LLM недоступен, используем базовый парсинг")
            return self._basic_parse(order_data)
        
        try:
            # Формируем текст заказа для анализа
            order_text = self._format_order_text(order_data)
            
            # Создаем промпт
            prompt = ORDER_PARSING_PROMPT.replace("{{order_text}}", order_text)
            
            # Вызываем LLM
            log.info("🔍 [HRTime Adapter] Парсинг заказа через LLM...")
            response = await self.llm_client.generate(
                prompt=prompt,
                system_prompt="Ты помощник для парсинга заказов. Отвечай только в формате JSON.",
                temperature=0.3,  # Низкая температура для точности
                max_tokens=2000
            )
            
            if response.error:
                log.error(f"❌ [HRTime Adapter] Ошибка LLM: {response.error}")
                return self._basic_parse(order_data)
            
            # Парсим JSON ответ
            import json
            try:
                # Извлекаем JSON из ответа
                content = response.content.strip()
                if "```json" in content:
                    # Удаляем markdown обертку
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()
                
                # Ищем JSON объект
                if "{" in content and "}" in content:
                    json_start = content.find("{")
                    json_end = content.rfind("}") + 1
                    json_str = content[json_start:json_end]
                    parsed_data = json.loads(json_str)
                else:
                    raise ValueError("JSON не найден в ответе")
                
                # Обогащаем данными из исходного заказа
                result = {
                    "requirements": parsed_data.get("requirements", order_data.get("description", "")),
                    "budget": parsed_data.get("budget", {
                        "amount": self._extract_budget_amount(order_data.get("budget")),
                        "currency": "RUB",
                        "text": str(order_data.get("budget", ""))
                    }),
                    "deadline": parsed_data.get("deadline", {
                        "date": self._parse_deadline_date(order_data.get("deadline")),
                        "text": str(order_data.get("deadline", ""))
                    }),
                    "contacts": parsed_data.get("contacts", {
                        "full_name": self._extract_full_name(order_data),
                        "phone": self._extract_phone(order_data),
                        "email": self._extract_email(order_data)
                    }),
                    "raw_data": order_data
                }
                
                log.info("✅ [HRTime Adapter] Заказ успешно распарсен через LLM")
                return result
                
            except json.JSONDecodeError as e:
                log.error(f"❌ [HRTime Adapter] Ошибка парсинга JSON: {e}")
                log.error(f"❌ Ответ LLM: {response.content[:500]}")
                return self._basic_parse(order_data)
                
        except Exception as e:
            log.error(f"❌ [HRTime Adapter] Ошибка парсинга заказа: {e}")
            import traceback
            log.error(f"❌ Traceback: {traceback.format_exc()}")
            return self._basic_parse(order_data)
    
    def _format_order_text(self, order_data: Dict) -> str:
        """Форматирует данные заказа в текст для анализа"""
        parts = []
        
        if order_data.get("title"):
            parts.append(f"Название: {order_data.get('title')}")
        
        if order_data.get("description"):
            parts.append(f"Описание: {order_data.get('description')}")
        
        if order_data.get("requirements"):
            parts.append(f"Требования: {order_data.get('requirements')}")
        
        if order_data.get("budget"):
            parts.append(f"Бюджет: {order_data.get('budget')}")
        
        if order_data.get("deadline"):
            parts.append(f"Сроки: {order_data.get('deadline')}")
        
        client = order_data.get("client", {})
        if client:
            client_parts = []
            if client.get("name"):
                client_parts.append(f"Имя: {client.get('name')}")
            if client.get("email"):
                client_parts.append(f"Email: {client.get('email')}")
            if client.get("phone"):
                client_parts.append(f"Телефон: {client.get('phone')}")
            if client_parts:
                parts.append(f"Клиент: {'; '.join(client_parts)}")
        
        return "\n\n".join(parts) if parts else str(order_data)
    
    def _basic_parse(self, order_data: Dict) -> Dict:
        """Базовый парсинг без LLM (fallback)"""
        client = order_data.get("client", {})
        
        return {
            "requirements": order_data.get("description", order_data.get("requirements", "")),
            "budget": {
                "amount": self._extract_budget_amount(order_data.get("budget")),
                "currency": "RUB",
                "text": str(order_data.get("budget", ""))
            },
            "deadline": {
                "date": self._parse_deadline_date(order_data.get("deadline")),
                "text": str(order_data.get("deadline", ""))
            },
            "contacts": {
                "full_name": client.get("name", ""),
                "phone": client.get("phone", ""),
                "email": client.get("email", "")
            },
            "raw_data": order_data
        }
    
    def _extract_budget_amount(self, budget_text: Optional[str]) -> float:
        """Извлекает числовое значение бюджета из текста"""
        if not budget_text:
            return 0.0
        
        import re
        # Ищем числа в тексте
        numbers = re.findall(r'[\d\s]+', str(budget_text).replace(' ', ''))
        if numbers:
            try:
                # Берем первое большое число (предполагаем, что это бюджет)
                for num_str in numbers:
                    num = float(num_str.replace(' ', ''))
                    if num > 1000:  # Предполагаем, что бюджет больше 1000
                        return num
                # Если не нашли большое число, берем последнее
                return float(numbers[-1].replace(' ', ''))
            except:
                pass
        
        return 0.0
    
    def _parse_deadline_date(self, deadline_text: Optional[str]) -> Optional[str]:
        """Парсит дату дедлайна из текста"""
        if not deadline_text:
            return None
        
        # Простой парсинг дат (можно улучшить)
        from datetime import datetime
        import re
        
        # Ищем дату в формате YYYY-MM-DD
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', str(deadline_text))
        if date_match:
            return date_match.group(1)
        
        # Ищем дату в формате DD.MM.YYYY
        date_match = re.search(r'(\d{2}\.\d{2}\.\d{4})', str(deadline_text))
        if date_match:
            date_str = date_match.group(1)
            try:
                dt = datetime.strptime(date_str, "%d.%m.%Y")
                return dt.strftime("%Y-%m-%d")
            except:
                pass
        
        return None
    
    def _extract_full_name(self, order_data: Dict) -> str:
        """Извлекает полное имя клиента"""
        client = order_data.get("client", {})
        return client.get("name", "")
    
    def _extract_phone(self, order_data: Dict) -> str:
        """Извлекает телефон клиента"""
        client = order_data.get("client", {})
        return client.get("phone", "")
    
    def _extract_email(self, order_data: Dict) -> str:
        """Извлекает email клиента"""
        client = order_data.get("client", {})
        return client.get("email", "")

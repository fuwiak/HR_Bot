"""
Сервис для формирования и отправки красивых email ответов
"""
import os
import tempfile
import logging
from typing import Dict, Optional, List
from datetime import datetime
from pathlib import Path

log = logging.getLogger(__name__)

# Импортируем функции отправки email
try:
    from services.helpers.email_helper import send_email
except ImportError:
    log.error("❌ Не удалось импортировать send_email")
    send_email = None

# Импортируем функции генерации документов
try:
    from services.agents.lead_processor import generate_proposal
    from services.helpers.summary_helper import generate_report
except ImportError:
    log.warning("⚠️ Функции генерации документов недоступны")
    generate_proposal = None
    generate_report = None


# HTML шаблоны для красивых писем
EMAIL_TEMPLATES = {
    "primary": """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            background-color: #ffffff;
            border-radius: 8px;
            padding: 30px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .header {{
            border-bottom: 3px solid #4a90e2;
            padding-bottom: 15px;
            margin-bottom: 20px;
        }}
        .header h1 {{
            color: #4a90e2;
            margin: 0;
            font-size: 24px;
        }}
        .content {{
            margin: 20px 0;
        }}
        .footer {{
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #e0e0e0;
            font-size: 12px;
            color: #666;
        }}
        .signature {{
            margin-top: 20px;
            color: #555;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Здравствуйте!</h1>
        </div>
        <div class="content">
            {content}
        </div>
        <div class="footer">
            <p>С уважением,<br>
            <strong>Анастасия Новоселова</strong><br>
            HR-консультант</p>
        </div>
    </div>
</body>
</html>
""",
    "followup": """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            background-color: #ffffff;
            border-radius: 8px;
            padding: 30px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .header {{
            border-bottom: 3px solid #50c878;
            padding-bottom: 15px;
            margin-bottom: 20px;
        }}
        .header h1 {{
            color: #50c878;
            margin: 0;
            font-size: 24px;
        }}
        .content {{
            margin: 20px 0;
        }}
        .footer {{
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #e0e0e0;
            font-size: 12px;
            color: #666;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Добрый день!</h1>
        </div>
        <div class="content">
            {content}
        </div>
        <div class="footer">
            <p>С уважением,<br>
            <strong>Анастасия Новоселова</strong><br>
            HR-консультант</p>
        </div>
    </div>
</body>
</html>
""",
    "with_document": """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            background-color: #ffffff;
            border-radius: 8px;
            padding: 30px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .header {{
            border-bottom: 3px solid #ff6b6b;
            padding-bottom: 15px;
            margin-bottom: 20px;
        }}
        .header h1 {{
            color: #ff6b6b;
            margin: 0;
            font-size: 24px;
        }}
        .content {{
            margin: 20px 0;
        }}
        .attachment-notice {{
            background-color: #f0f7ff;
            border-left: 4px solid #4a90e2;
            padding: 15px;
            margin: 20px 0;
            border-radius: 4px;
        }}
        .footer {{
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #e0e0e0;
            font-size: 12px;
            color: #666;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Добрый день!</h1>
        </div>
        <div class="content">
            {content}
        </div>
        <div class="attachment-notice">
            <strong>📎 Вложения:</strong> К письму прикреплены запрошенные документы.
        </div>
        <div class="footer">
            <p>С уважением,<br>
            <strong>Анастасия Новоселова</strong><br>
            HR-консультант</p>
        </div>
    </div>
</body>
</html>
"""
}


async def format_email_content(content: str, email_type: str = "primary") -> str:
    """
    Форматирует текст письма в красивый HTML
    
    Args:
        content: Текст письма
        email_type: Тип письма (primary, followup, with_document)
    
    Returns:
        HTML-форматированное письмо
    """
    template = EMAIL_TEMPLATES.get(email_type, EMAIL_TEMPLATES["primary"])
    
    # Преобразуем простой текст в HTML с сохранением переносов строк
    html_content = content.replace("\n", "<br>")
    
    return template.format(content=html_content)


async def save_document_to_file(content: str, document_type: str, email_id: Optional[str] = None) -> Optional[str]:
    """
    Сохраняет документ (КП, отчет) во временный файл
    
    Args:
        content: Содержимое документа
        document_type: Тип документа ('proposal', 'report')
        email_id: ID письма (для имени файла)
    
    Returns:
        Путь к сохраненному файлу или None при ошибке
    """
    try:
        # Создаем временную директорию для документов
        temp_dir = Path(tempfile.gettempdir()) / "hr_bot_documents"
        temp_dir.mkdir(exist_ok=True)
        
        # Формируем имя файла
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        email_suffix = f"_{email_id}" if email_id else ""
        
        if document_type == "proposal":
            filename = f"КП_{timestamp}{email_suffix}.txt"
        elif document_type == "report":
            filename = f"Отчет_{timestamp}{email_suffix}.txt"
        else:
            filename = f"Документ_{timestamp}{email_suffix}.txt"
        
        file_path = temp_dir / filename
        
        # Сохраняем содержимое
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        log.info(f"✅ Документ сохранен: {file_path}")
        return str(file_path)
        
    except Exception as e:
        log.error(f"❌ Ошибка сохранения документа: {e}")
        return None


async def generate_and_save_proposal(
    lead_request: str,
    lead_contact: Dict,
    email_id: Optional[str] = None
) -> Optional[str]:
    """
    Генерирует КП и сохраняет в файл
    
    Args:
        lead_request: Запрос от клиента
        lead_contact: Контактная информация
        email_id: ID письма
    
    Returns:
        Путь к файлу с КП или None
    """
    if not generate_proposal:
        log.error("❌ Функция generate_proposal недоступна")
        return None
    
    try:
        log.info("⏳ Генерирую коммерческое предложение...")
        proposal_text = await generate_proposal(lead_request, lead_contact)
        
        if not proposal_text:
            log.error("❌ Не удалось сгенерировать КП")
            return None
        
        file_path = await save_document_to_file(proposal_text, "proposal", email_id)
        return file_path
        
    except Exception as e:
        log.error(f"❌ Ошибка генерации КП: {e}")
        import traceback
        log.error(traceback.format_exc())
        return None


async def generate_and_save_report(
    project_data: Dict,
    email_id: Optional[str] = None
) -> Optional[str]:
    """
    Генерирует отчет и сохраняет в файл
    
    Args:
        project_data: Данные проекта
        email_id: ID письма
    
    Returns:
        Путь к файлу с отчетом или None
    """
    if not generate_report:
        log.error("❌ Функция generate_report недоступна")
        return None
    
    try:
        log.info("⏳ Генерирую отчет...")
        report_text = await generate_report(project_data)
        
        if not report_text:
            log.error("❌ Не удалось сгенерировать отчет")
            return None
        
        file_path = await save_document_to_file(report_text, "report", email_id)
        return file_path
        
    except Exception as e:
        log.error(f"❌ Ошибка генерации отчета: {e}")
        import traceback
        log.error(traceback.format_exc())
        return None


async def send_email_reply(
    to_email: str,
    subject: str,
    content: str,
    reply_type: str = "primary",
    attachments: Optional[List[str]] = None,
    original_email_id: Optional[str] = None
) -> bool:
    """
    Отправляет красивый email ответ
    
    Args:
        to_email: Email получателя
        subject: Тема письма
        content: Текст письма
        reply_type: Тип ответа ('primary', 'followup', 'with_document')
        attachments: Список путей к файлам для вложения
        original_email_id: ID исходного письма (для Re:)
    
    Returns:
        True при успехе, False при ошибке
    """
    if not send_email:
        log.error("❌ Функция send_email недоступна")
        return False
    
    try:
        # Формируем тему письма
        if original_email_id and not subject.startswith("Re:"):
            subject = f"Re: {subject}"
        
        # Форматируем содержимое в HTML
        email_type = "with_document" if attachments else reply_type
        html_body = await format_email_content(content, email_type)
        
        # Отправляем письмо
        log.info(f"📧 Отправляю ответ на {to_email}: {subject}")
        result = await send_email(
            to_email=to_email,
            subject=subject,
            body=html_body,
            is_html=True,
            attachments=attachments
        )
        
        if result:
            log.info(f"✅ Ответ успешно отправлен на {to_email}")
        else:
            log.error(f"❌ Не удалось отправить ответ на {to_email}")
        
        return result
        
    except Exception as e:
        log.error(f"❌ Ошибка отправки ответа: {e}")
        import traceback
        log.error(traceback.format_exc())
        return False


async def send_proposal_email(
    to_email: str,
    subject: str,
    lead_request: str,
    lead_contact: Dict,
    additional_message: Optional[str] = None,
    email_id: Optional[str] = None
) -> bool:
    """
    Генерирует и отправляет письмо с КП
    
    Args:
        to_email: Email получателя
        subject: Тема письма
        lead_request: Запрос от клиента
        lead_contact: Контактная информация
        additional_message: Дополнительное сообщение к письму
        email_id: ID исходного письма
    
    Returns:
        True при успехе, False при ошибке
    """
    try:
        # Генерируем и сохраняем КП
        proposal_path = await generate_and_save_proposal(lead_request, lead_contact, email_id)
        
        if not proposal_path:
            log.error("❌ Не удалось создать файл с КП")
            return False
        
        # Формируем текст письма
        if additional_message:
            content = additional_message + "\n\n" + "Прикрепляю коммерческое предложение по вашему запросу."
        else:
            content = (
                "Добрый день!\n\n"
                "Благодарю за ваш запрос. Прикрепляю коммерческое предложение "
                "с детальным описанием решения и этапов работы.\n\n"
                "Буду рада обсудить детали и ответить на ваши вопросы."
            )
        
        # Отправляем письмо с вложением
        result = await send_email_reply(
            to_email=to_email,
            subject=subject,
            content=content,
            reply_type="with_document",
            attachments=[proposal_path],
            original_email_id=email_id
        )
        
        # Удаляем временный файл после отправки
        try:
            if os.path.exists(proposal_path):
                os.remove(proposal_path)
                log.info(f"✅ Временный файл удален: {proposal_path}")
        except Exception as e:
            log.warning(f"⚠️ Не удалось удалить временный файл: {e}")
        
        return result
        
    except Exception as e:
        log.error(f"❌ Ошибка отправки письма с КП: {e}")
        import traceback
        log.error(traceback.format_exc())
        return False


async def send_report_email(
    to_email: str,
    subject: str,
    project_data: Dict,
    additional_message: Optional[str] = None,
    email_id: Optional[str] = None
) -> bool:
    """
    Генерирует и отправляет письмо с отчетом
    
    Args:
        to_email: Email получателя
        subject: Тема письма
        project_data: Данные проекта
        additional_message: Дополнительное сообщение к письму
        email_id: ID исходного письма
    
    Returns:
        True при успехе, False при ошибке
    """
    try:
        # Генерируем и сохраняем отчет
        report_path = await generate_and_save_report(project_data, email_id)
        
        if not report_path:
            log.error("❌ Не удалось создать файл с отчетом")
            return False
        
        # Формируем текст письма
        if additional_message:
            content = additional_message + "\n\n" + "Прикрепляю отчет по проекту."
        else:
            content = (
                "Добрый день!\n\n"
                "Прикрепляю отчет по проекту с информацией о текущем статусе, "
                "выполненных задачах и следующих шагах.\n\n"
                "Буду рада обсудить детали."
            )
        
        # Отправляем письмо с вложением
        result = await send_email_reply(
            to_email=to_email,
            subject=subject,
            content=content,
            reply_type="with_document",
            attachments=[report_path],
            original_email_id=email_id
        )
        
        # Удаляем временный файл после отправки
        try:
            if os.path.exists(report_path):
                os.remove(report_path)
                log.info(f"✅ Временный файл удален: {report_path}")
        except Exception as e:
            log.warning(f"⚠️ Не удалось удалить временный файл: {e}")
        
        return result
        
    except Exception as e:
        log.error(f"❌ Ошибка отправки письма с отчетом: {e}")
        import traceback
        log.error(traceback.format_exc())
        return False

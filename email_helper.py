"""
Email Helper Module
Работа с Email через IMAP (чтение) и SMTP (отправка) для Yandex
"""
import os
import logging
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header
from typing import List, Dict, Optional
from datetime import datetime
import asyncio

# Загружаем переменные окружения из .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv не установлен, используем системные переменные

log = logging.getLogger()

# ===================== CONFIGURATION =====================
YANDEX_EMAIL = os.getenv("YANDEX_EMAIL")
# Поддерживаем YANDEX_IMAP_PASSWORD (приоритет) или YANDEX_PASSWORD
YANDEX_PASSWORD = os.getenv("YANDEX_IMAP_PASSWORD") or os.getenv("YANDEX_PASSWORD")
YANDEX_IMAP_SERVER = os.getenv("YANDEX_IMAP_SERVER", "imap.yandex.ru")
YANDEX_SMTP_SERVER = os.getenv("YANDEX_SMTP_SERVER", "smtp.yandex.ru")
YANDEX_IMAP_PORT = int(os.getenv("YANDEX_IMAP_PORT", 993))
YANDEX_SMTP_PORT = int(os.getenv("YANDEX_SMTP_PORT", 465))

# Для async работы используем aiosmtplib для SMTP, для IMAP используем синхронную версию через asyncio.to_thread
# aiimaplib недоступен в PyPI, поэтому используем встроенный imaplib
try:
    import aiosmtplib
    ASYNC_SMTP_AVAILABLE = True
except ImportError:
    ASYNC_SMTP_AVAILABLE = False
    log.warning("⚠️ aiosmtplib не установлен. Для async SMTP установите: pip install aiosmtplib")
    # Используем синхронную версию через asyncio.to_thread

# ===================== EMAIL READING (IMAP) =====================

async def check_new_emails(folder: str = "INBOX", since_days: int = 1, limit: int = 10) -> List[Dict]:
    """
    Проверить новые письма через IMAP (async)
    
    Args:
        folder: Папка для проверки (по умолчанию INBOX)
        since_days: Количество дней назад для проверки
        limit: Максимальное количество писем
    
    Returns:
        Список словарей с информацией о письмах
    """
    if not YANDEX_EMAIL or not YANDEX_PASSWORD:
        log.error("❌ YANDEX_EMAIL или YANDEX_PASSWORD не установлены")
        return []
    
    # aiimaplib недоступен в PyPI, всегда используем синхронную версию через asyncio.to_thread
    # Это безопасно, так как операция выполняется в отдельном потоке и не блокирует event loop
    return await asyncio.to_thread(_check_new_emails_sync, folder, since_days, limit)

def _check_new_emails_sync(folder: str, since_days: int, limit: int) -> List[Dict]:
    """Синхронная версия проверки email через imaplib"""
    try:
        import imaplib
        
        imap = imaplib.IMAP4_SSL(YANDEX_IMAP_SERVER, YANDEX_IMAP_PORT)
        imap.login(YANDEX_EMAIL, YANDEX_PASSWORD)
        imap.select(folder)
        
        from datetime import datetime, timedelta
        date_since = (datetime.now() - timedelta(days=since_days)).strftime("%d-%b-%Y")
        status, messages = imap.search(None, "SINCE", date_since)
        
        if status != "OK":
            imap.logout()
            return []
        
        email_ids = messages[0].split()
        emails = []
        
        for email_id in email_ids[-limit:]:
            status, msg_data = imap.fetch(email_id, "(RFC822)")
            if status == "OK":
                email_message = email.message_from_bytes(msg_data[0][1])
                emails.append(_parse_email(email_message, email_id.decode()))
        
        imap.logout()
        return emails
    except Exception as e:
        log.error(f"❌ Ошибка чтения email (sync): {e}")
        return []

def _safe_decode(data: bytes, charset: str = None) -> str:
    """
    Безопасное декодирование байтов с поддержкой различных кодировок
    
    Args:
        data: Байты для декодирования
        charset: Предпочтительная кодировка (если известна)
    
    Returns:
        Декодированная строка
    """
    if not data:
        return ""
    
    if not isinstance(data, bytes):
        return str(data)
    
    # Список кодировок для попытки декодирования (в порядке приоритета)
    encodings = []
    
    if charset:
        encodings.append(charset.lower())
    
    # Добавляем стандартные кодировки
    encodings.extend([
        "utf-8",
        "windows-1251",  # Кириллица (Windows)
        "koi8-r",        # Кириллица (Unix)
        "cp1251",        # Альтернативное название для windows-1251
        "iso-8859-1",    # Latin-1
        "iso-8859-5",    # Кириллица (ISO)
        "latin1",
        "ascii"
    ])
    
    # Убираем дубликаты, сохраняя порядок
    seen = set()
    unique_encodings = []
    for enc in encodings:
        if enc not in seen:
            seen.add(enc)
            unique_encodings.append(enc)
    
    # Пробуем декодировать с каждой кодировкой
    for encoding in unique_encodings:
        try:
            return data.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            continue
    
    # Если ничего не помогло, используем errors='replace' или 'ignore'
    try:
        return data.decode("utf-8", errors="replace")
    except:
        return data.decode("utf-8", errors="ignore")

def _parse_email(email_message, email_id: str) -> Dict:
    """Парсинг email сообщения"""
    subject = ""
    from_addr = ""
    to_addr = ""
    body = ""
    date_str = ""
    
    # Декодирование subject
    try:
        subject_header = decode_header(email_message.get("Subject", ""))
        if subject_header and subject_header[0][0]:
            subject_data = subject_header[0][0]
            charset = subject_header[0][1] if len(subject_header[0]) > 1 else None
            if isinstance(subject_data, bytes):
                subject = _safe_decode(subject_data, charset)
            else:
                subject = str(subject_data)
    except Exception as e:
        log.warning(f"⚠️ Ошибка декодирования темы письма: {e}")
        subject = email_message.get("Subject", "Без темы")
    
    # Отправитель
    from_addr = email_message.get("From", "Неизвестно")
    
    # Получатель
    to_addr = email_message.get("To", "")
    
    # Дата
    date_str = email_message.get("Date", "")
    
    # Тело письма
    try:
        if email_message.is_multipart():
            for part in email_message.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain":
                    payload = part.get_payload(decode=True)
                    if payload:
                        # Получаем charset из заголовков части
                        charset = part.get_content_charset() or "utf-8"
                        body = _safe_decode(payload, charset)
                    break
        else:
            payload = email_message.get_payload(decode=True)
            if payload:
                # Получаем charset из заголовков письма
                charset = email_message.get_content_charset() or "utf-8"
                body = _safe_decode(payload, charset)
    except Exception as e:
        log.warning(f"⚠️ Ошибка декодирования тела письма: {e}")
        body = ""
    
    return {
        "id": email_id,
        "subject": subject,
        "from": from_addr,
        "to": to_addr,
        "body": body,
        "date": date_str,
        "raw": email_message
    }

# ===================== EMAIL SENDING (SMTP) =====================

async def send_email(
    to_email: str,
    subject: str,
    body: str,
    is_html: bool = False,
    attachments: Optional[List[str]] = None
) -> bool:
    """
    Отправить email через SMTP (async)
    
    Args:
        to_email: Email получателя
        subject: Тема письма
        body: Тело письма
        is_html: Использовать HTML формат
        attachments: Список путей к файлам для вложения
    
    Returns:
        True при успехе, False при ошибке
    """
    if not YANDEX_EMAIL or not YANDEX_PASSWORD:
        log.error("❌ YANDEX_EMAIL или YANDEX_PASSWORD не установлены")
        return False
    
    if ASYNC_SMTP_AVAILABLE:
        return await _send_email_async(to_email, subject, body, is_html, attachments)
    else:
        # Используем синхронную версию через asyncio.to_thread
        return await asyncio.to_thread(_send_email_sync, to_email, subject, body, is_html, attachments)

async def _send_email_async(to_email: str, subject: str, body: str, is_html: bool, attachments: Optional[List[str]]) -> bool:
    """Async версия отправки email через aiosmtplib"""
    try:
        import aiosmtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        message = MIMEMultipart()
        message["From"] = YANDEX_EMAIL
        message["To"] = to_email
        message["Subject"] = subject
        
        message.attach(MIMEText(body, "html" if is_html else "plain"))
        
        await aiosmtplib.send(
            message,
            hostname=YANDEX_SMTP_SERVER,
            port=YANDEX_SMTP_PORT,
            username=YANDEX_EMAIL,
            password=YANDEX_PASSWORD,
            use_tls=True
        )
        
        log.info(f"✅ Email отправлен: {to_email} - {subject}")
        return True
    except Exception as e:
        log.error(f"❌ Ошибка отправки email (async): {e}")
        import traceback
        log.error(f"❌ Traceback: {traceback.format_exc()}")
        return False

def _send_email_sync(to_email: str, subject: str, body: str, is_html: bool, attachments: Optional[List[str]]) -> bool:
    """Синхронная версия отправки email через smtplib"""
    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        message = MIMEMultipart()
        message["From"] = YANDEX_EMAIL
        message["To"] = to_email
        message["Subject"] = subject
        
        message.attach(MIMEText(body, "html" if is_html else "plain"))
        
        with smtplib.SMTP_SSL(YANDEX_SMTP_SERVER, YANDEX_SMTP_PORT) as server:
            server.login(YANDEX_EMAIL, YANDEX_PASSWORD)
            server.send_message(message)
        
        log.info(f"✅ Email отправлен: {to_email} - {subject}")
        return True
    except Exception as e:
        log.error(f"❌ Ошибка отправки email (sync): {e}")
        return False

# ===================== EMAIL CLASSIFICATION =====================

async def classify_email(email_data: Dict) -> str:
    """
    Классифицировать email (новый лид, продолжение диалога, служебная информация)
    
    Args:
        email_data: Словарь с данными письма
    
    Returns:
        Категория: "new_lead", "followup", "service"
    """
    # Простая эвристическая классификация
    # В реальной версии можно использовать LLM для более точной классификации
    
    subject = email_data.get("subject", "").lower()
    body = email_data.get("body", "").lower()
    from_addr = email_data.get("from", "").lower()
    
    # Ключевые слова для нового лида
    lead_keywords = ["запрос", "консультация", "помощь", "нужна помощь", "интерес", "предложение"]
    
    # Ключевые слова для продолжения диалога
    followup_keywords = ["re:", "fwd:", "ответ", "продолжение", "следующий шаг"]
    
    if any(keyword in subject for keyword in followup_keywords) or any(keyword in body[:200] for keyword in followup_keywords):
        return "followup"
    
    if any(keyword in subject for keyword in lead_keywords) or any(keyword in body[:200] for keyword in lead_keywords):
        return "new_lead"
    
    # По умолчанию служебная информация
    return "service"


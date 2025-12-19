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

# Логируем настройки для диагностики (без пароля) - ТОЛЬКО ПРИ ПЕРВОМ ИМПОРТЕ
if not hasattr(log, '_email_config_logged'):
    log.info(f"📧 SMTP настройки: email={YANDEX_EMAIL}, server={YANDEX_SMTP_SERVER}, port={YANDEX_SMTP_PORT}, password_set={bool(YANDEX_PASSWORD)}")
    if not YANDEX_EMAIL or not YANDEX_PASSWORD:
        log.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА: YANDEX_EMAIL или YANDEX_PASSWORD не установлены!")
        log.error(f"   YANDEX_EMAIL: {YANDEX_EMAIL or 'НЕ УСТАНОВЛЕН'}")
        log.error(f"   YANDEX_PASSWORD: {'УСТАНОВЛЕН' if YANDEX_PASSWORD else 'НЕ УСТАНОВЛЕН'}")
        log.error(f"   YANDEX_IMAP_PASSWORD: {'УСТАНОВЛЕН' if os.getenv('YANDEX_IMAP_PASSWORD') else 'НЕ УСТАНОВЛЕН'}")
        log.error(f"   Проверьте Railway Variables: YANDEX_EMAIL и YANDEX_IMAP_PASSWORD должны быть установлены!")
        log.error(f"   См. инструкцию: RAILWAY_EMAIL_FIX.md")
    log._email_config_logged = True

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
        
        # Берем последние N писем (самые новые) и разворачиваем, чтобы самое новое было первым
        recent_ids = email_ids[-limit:] if limit > 0 else email_ids
        recent_ids = list(reversed(recent_ids))  # Разворачиваем, чтобы самое новое было первым
        
        for email_id in recent_ids:
            status, msg_data = imap.fetch(email_id, "(RFC822)")
            if status == "OK":
                email_message = email.message_from_bytes(msg_data[0][1])
                emails.append(_parse_email(email_message, email_id.decode()))
        
        imap.logout()
        return emails  # Теперь самое новое письмо первое в списке
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

def _decode_email_address(email_str: str) -> str:
    """Декодирует email адрес из формата encoded (например, =?UTF-8?B?...)"""
    if not email_str or "=?" not in email_str:
        return email_str
    
    try:
        from email.header import decode_header
        import re
        
        decoded_parts = decode_header(email_str)
        decoded_email = ""
        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                decoded_email += part.decode(encoding or 'utf-8')
            else:
                decoded_email += str(part)
        
        # Извлекаем email адрес из строки вида "Имя <email@domain.com>"
        email_match = re.search(r'<([^>]+)>', decoded_email)
        if email_match:
            return email_match.group(1)
        else:
            # Пробуем найти email адрес в строке
            email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', decoded_email)
            if email_match:
                return email_match.group(0)
            return decoded_email.split()[-1] if decoded_email.split() else email_str
    except Exception as e:
        log.warning(f"⚠️ Ошибка декодирования email адреса: {e}, используем исходный: {email_str}")
        return email_str

async def send_email(
    to_email: str,
    subject: str,
    body: str,
    is_html: bool = False,
    attachments: Optional[List[str]] = None
) -> bool:
    """
    Отправить email через SMTP или Resend API (fallback для Railway)
    
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
    
    # Декодируем адрес получателя, если он в формате encoded
    to_email = _decode_email_address(to_email)
    
    # Пробуем сначала через Resend API (если доступен) - работает на Railway
    RESEND_API_KEY = os.getenv("RESEND_API_KEY")
    if RESEND_API_KEY:
        try:
            result = await _send_email_resend(to_email, subject, body, is_html)
            if result:
                return True
            log.warning("⚠️ Resend API не смог отправить, пробуем SMTP...")
        except Exception as e:
            log.warning(f"⚠️ Ошибка Resend API: {e}, пробуем SMTP...")
    
    # Fallback на SMTP (может не работать на Railway бесплатном плане)
    log.info("🔄 Использую синхронную версию SMTP...")
    result = await asyncio.to_thread(_send_email_sync, to_email, subject, body, is_html, attachments)
    
    # Если SMTP не работает (Railway блокирует порты), логируем предупреждение
    if not result:
        log.error("❌ Не удалось отправить email через SMTP")
        log.error("💡 Railway блокирует порты SMTP (465, 587) на бесплатных планах")
        log.error("💡 Решения:")
        log.error("   1. Используйте Resend API (добавьте RESEND_API_KEY в Railway Variables)")
        log.error("   2. Обновите Railway план до Pro (разблокирует SMTP порты)")
        log.error("   3. Используйте другой сервис: SendGrid, Mailgun, Postmark")
    
    return result

async def _send_email_resend(to_email: str, subject: str, body: str, is_html: bool = False) -> bool:
    """Отправка email через Resend API (работает на Railway)"""
    try:
        import aiohttp
        import json
        
        RESEND_API_KEY = os.getenv("RESEND_API_KEY")
        if not RESEND_API_KEY:
            return False
        
        # Адрес уже декодирован в send_email()
        
        url = "https://api.resend.com/emails"
        headers = {
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # Для Resend можно использовать подтвержденный домен или их домен
        # Если домен не подтвержден, можно использовать домен Resend (например, onboarding@resend.dev)
        # Но для начала пробуем использовать Yandex email - если домен подтвержден в Resend, будет работать
        from_email = YANDEX_EMAIL
        
        # Можно настроить альтернативный email для Resend через переменную окружения
        RESEND_FROM_EMAIL = os.getenv("RESEND_FROM_EMAIL")
        if RESEND_FROM_EMAIL:
            from_email = RESEND_FROM_EMAIL
            log.info(f"📧 Использую RESEND_FROM_EMAIL: {from_email}")
        
        payload = {
            "from": f"HR Bot <{from_email}>",
            "to": [to_email],
            "subject": subject,
        }
        
        # Добавляем текст или HTML в зависимости от формата
        # Resend поддерживает оба формата одновременно
        if is_html:
            payload["html"] = body
            # Resend автоматически создаст text версию из HTML, но можно добавить явно
            payload["text"] = body  # Простая версия без HTML тегов
        else:
            payload["text"] = body
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status == 200:
                    response_data = await response.json()
                    email_id = response_data.get("id", "unknown")
                    log.info(f"✅ Email отправлен через Resend API (ID: {email_id}): {to_email} - {subject}")
                    return True
                else:
                    # Получаем текст ошибки
                    error_text = await response.text()
                    error_message = error_text
                    
                    # Пробуем распарсить JSON ошибки
                    try:
                        import json
                        error_json = json.loads(error_text)
                        error_message = error_json.get("message", error_text)
                    except:
                        pass
                    
                    log.error(f"❌ Ошибка Resend API ({response.status}): {error_message}")
                    
                    # Специальная обработка ошибок
                    if response.status == 403:
                        log.error("💡 Проверьте API ключ - возможно он неверный или истек")
                    elif response.status == 422:
                        log.error("💡 Проверьте формат email адресов или подтвердите домен в Resend")
                        log.error("💡 Можно использовать RESEND_FROM_EMAIL=onboarding@resend.dev в Railway Variables")
                    
                    return False
                    
    except ImportError:
        log.warning("⚠️ aiohttp не установлен. Для Resend API установите: pip install aiohttp")
        return False
    except Exception as e:
        log.error(f"❌ Ошибка отправки через Resend API: {e}")
        return False

async def _send_email_async(to_email: str, subject: str, body: str, is_html: bool, attachments: Optional[List[str]]) -> bool:
    """Async версия отправки email через aiosmtplib с fallback на синхронную версию"""
    try:
        import aiosmtplib
        import ssl
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        message = MIMEMultipart()
        message["From"] = YANDEX_EMAIL
        message["To"] = to_email
        message["Subject"] = subject
        
        message.attach(MIMEText(body, "html" if is_html else "plain"))
        
        # Создаем SSL контекст
        ssl_context = ssl.create_default_context()
        
        # Пробуем порт 465 (SMTP_SSL) - основной вариант
        log.info(f"🔄 Попытка подключения к {YANDEX_SMTP_SERVER}:465 (SSL, async)...")
        try:
            smtp = aiosmtplib.SMTP(
                hostname=YANDEX_SMTP_SERVER,
                port=465,
                timeout=30,
                use_tls=False,  # Для порта 465 не используем STARTTLS
                tls_context=ssl_context
            )
            
            try:
                await smtp.connect()
                await smtp.login(YANDEX_EMAIL, YANDEX_PASSWORD)
                await smtp.send_message(message)
                await smtp.quit()
                
                log.info(f"✅ Email отправлен (async, порт 465): {to_email} - {subject}")
                return True
            except Exception as e:
                try:
                    await smtp.quit()
                except:
                    pass
                raise
        
        except (TimeoutError, OSError, ConnectionError) as e:
            error_str = str(e).lower()
            log.warning(f"⚠️ Не удалось подключиться к порту 465 (async): {e}")
            
            # Если порт 465 недоступен, пробуем порт 587 с STARTTLS
            if "network is unreachable" in error_str or "timed out" in error_str or "connection refused" in error_str or "timeout" in error_str:
                log.info("🔄 Пробую альтернативный порт 587 (STARTTLS, async)...")
                try:
                    smtp = aiosmtplib.SMTP(
                        hostname=YANDEX_SMTP_SERVER,
                        port=587,
                        timeout=30,
                        use_tls=True,  # Для порта 587 используем STARTTLS
                        tls_context=ssl_context
                    )
                    
                    try:
                        await smtp.connect()
                        await smtp.login(YANDEX_EMAIL, YANDEX_PASSWORD)
                        await smtp.send_message(message)
                        await smtp.quit()
                        
                        log.info(f"✅ Email отправлен (async, порт 587): {to_email} - {subject}")
                        return True
                    except Exception as e2:
                        try:
                            await smtp.quit()
                        except:
                            pass
                        raise
                except Exception as e2:
                    log.error(f"❌ Ошибка при подключении к порту 587 (async): {e2}")
                    # Пробрасываем дальше для fallback на sync версию
            else:
                # Для других ошибок пробрасываем дальше
                raise
        
    except Exception as e:
        log.warning(f"⚠️ Ошибка отправки email (async): {e}")
        
        # При любой ошибке пробуем синхронную версию (более надежную)
        log.info("🔄 Пробую отправить через синхронный SMTP (fallback)...")
        try:
            result = await asyncio.to_thread(_send_email_sync, to_email, subject, body, is_html, attachments)
            if result:
                log.info("✅ Email успешно отправлен через синхронный SMTP")
            return result
        except Exception as sync_error:
            log.error(f"❌ Ошибка отправки email (sync fallback): {sync_error}")
            import traceback
            log.error(f"❌ Traceback: {traceback.format_exc()}")
            return False

def _send_email_sync(to_email: str, subject: str, body: str, is_html: bool, attachments: Optional[List[str]]) -> bool:
    """Синхронная версия отправки email через smtplib - точно как в test_email_simple.py"""
    import smtplib
    import socket
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    
    # Проверяем, что все переменные установлены
    if not YANDEX_EMAIL or not YANDEX_PASSWORD:
        log.error(f"❌ YANDEX_EMAIL или YANDEX_PASSWORD не установлены!")
        log.error(f"   YANDEX_EMAIL: {YANDEX_EMAIL or 'НЕ УСТАНОВЛЕН'}")
        log.error(f"   YANDEX_PASSWORD: {'УСТАНОВЛЕН' if YANDEX_PASSWORD else 'НЕ УСТАНОВЛЕН'}")
        log.error(f"   YANDEX_IMAP_PASSWORD: {'УСТАНОВЛЕН' if os.getenv('YANDEX_IMAP_PASSWORD') else 'НЕ УСТАНОВЛЕН'}")
        log.error(f"   YANDEX_PASSWORD (old): {'УСТАНОВЛЕН' if os.getenv('YANDEX_PASSWORD') else 'НЕ УСТАНОВЛЕН'}")
        log.error(f"   Проверьте Railway Variables: YANDEX_EMAIL и YANDEX_IMAP_PASSWORD должны быть установлены!")
        return False
    
    log.info(f"📧 Отправка email: от={YANDEX_EMAIL}, к={to_email}, тема={subject}, server={YANDEX_SMTP_SERVER}, port=465/587")
    
    message = MIMEMultipart()
    message["From"] = YANDEX_EMAIL
    message["To"] = to_email
    message["Subject"] = subject
    
    message.attach(MIMEText(body, "html" if is_html else "plain"))
    
    # Устанавливаем таймаут для соединения
    socket.setdefaulttimeout(30)  # 30 секунд
    
    # Попытка 1: Порт 465 (SMTP_SSL) - точно как в тестовом скрипте
    log.info(f"🔄 Попытка 1: Порт 465 (SMTP_SSL)...")
    try:
        server = smtplib.SMTP_SSL(YANDEX_SMTP_SERVER, 465, timeout=30)
        server.login(YANDEX_EMAIL, YANDEX_PASSWORD)
        server.send_message(message)
        server.quit()
        log.info(f"✅ Email отправлен (sync, порт 465): {to_email} - {subject}")
        return True
    except socket.timeout as e:
        log.warning(f"⚠️ Таймаут на порту 465: {e}")
    except OSError as e:
        log.warning(f"⚠️ Ошибка сети на порту 465: {e}")
    except smtplib.SMTPAuthenticationError as e:
        log.error(f"❌ Ошибка авторизации на порту 465: {e}")
        return False  # Авторизация не пройдет и на другом порту
    except Exception as e:
        log.warning(f"⚠️ Ошибка на порту 465: {e}")
    
    # Попытка 2: Порт 587 (STARTTLS) - точно как в тестовом скрипте
    log.info(f"🔄 Попытка 2: Порт 587 (STARTTLS)...")
    try:
        server = smtplib.SMTP(YANDEX_SMTP_SERVER, 587, timeout=30)
        server.starttls()
        server.login(YANDEX_EMAIL, YANDEX_PASSWORD)
        server.send_message(message)
        server.quit()
        log.info(f"✅ Email отправлен (sync, порт 587): {to_email} - {subject}")
        return True
    except socket.timeout as e:
        log.error(f"❌ Таймаут на порту 587: {e}")
    except OSError as e:
        log.error(f"❌ Ошибка сети на порту 587: {e}")
    except smtplib.SMTPAuthenticationError as e:
        log.error(f"❌ Ошибка авторизации на порту 587: {e}")
        return False
    except Exception as e:
        log.error(f"❌ Ошибка на порту 587: {e}")
    
    # Если дошли сюда - не удалось отправить
    log.error(f"❌ Не удалось отправить email через оба порта")
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


"""
Скрипт для переноса функций из app_old.py в handlers модули
"""
import re
import sys
from pathlib import Path

def extract_function(content, func_name):
    """Извлечь функцию из содержимого файла"""
    # Паттерн для поиска функции
    pattern = rf'^(async )?def {func_name}\s*\([^)]*\):'
    
    lines = content.split('\n')
    start_idx = None
    
    # Находим начало функции
    for i, line in enumerate(lines):
        if re.match(pattern, line):
            start_idx = i
            break
    
    if start_idx is None:
        return None
    
    # Находим конец функции (следующая функция или секция)
    indent_level = len(lines[start_idx]) - len(lines[start_idx].lstrip())
    end_idx = start_idx + 1
    
    for i in range(start_idx + 1, len(lines)):
        line = lines[i]
        # Пустая строка или комментарий - продолжаем
        if not line.strip() or line.strip().startswith('#'):
            continue
        # Секция (=====)
        if line.strip().startswith('# ====='):
            break
        # Следующая функция на том же уровне
        if re.match(r'^(async )?def \w+', line):
            current_indent = len(line) - len(line.lstrip())
            if current_indent <= indent_level:
                break
        end_idx = i + 1
    
    return '\n'.join(lines[start_idx:end_idx])

def get_imports_for_function(func_code):
    """Определить необходимые импорты для функции"""
    imports = set()
    
    # Telegram imports
    if 'Update' in func_code or 'ContextTypes' in func_code:
        imports.add('from telegram import Update')
        imports.add('from telegram.ext import ContextTypes')
    if 'InlineKeyboardButton' in func_code or 'InlineKeyboardMarkup' in func_code:
        imports.add('from telegram import InlineKeyboardButton, InlineKeyboardMarkup')
    if 'CallbackQuery' in func_code:
        imports.add('from telegram import CallbackQuery')
    if 'ChatAction' in func_code:
        imports.add('from telegram.constants import ChatAction')
    
    # Storage imports
    if 'add_email_subscriber' in func_code:
        imports.add('from telegram_bot.storage.email_subscribers import add_email_subscriber')
    if 'get_history' in func_code or 'get_recent_history' in func_code:
        imports.add('from telegram_bot.storage.memory import get_history, get_recent_history')
    if 'UserPhone' in func_code or 'get_user_phone' in func_code:
        imports.add('from telegram_bot.storage.user_data import UserPhone, get_user_phone')
    if 'UserBookingData' in func_code or 'get_user_booking_data' in func_code:
        imports.add('from telegram_bot.storage.user_data import UserBookingData, get_user_booking_data')
    
    # Integrations
    if 'get_services' in func_code or 'get_masters' in func_code:
        imports.add('from telegram_bot.integrations.google_sheets import get_services, get_masters')
    if 'search_service' in func_code or 'QDRANT_AVAILABLE' in func_code:
        imports.add('from telegram_bot.integrations.qdrant import search_service, QDRANT_AVAILABLE')
    if 'openrouter_chat' in func_code:
        imports.add('from telegram_bot.integrations.openrouter import openrouter_chat')
    
    # NLP
    if 'is_booking' in func_code:
        imports.add('from telegram_bot.nlp.intent_classifier import is_booking')
    if 'parse_booking_message' in func_code:
        imports.add('from telegram_bot.nlp.booking_parser import parse_booking_message')
    if 'remove_markdown' in func_code:
        imports.add('from telegram_bot.nlp.text_utils import remove_markdown')
    
    # Services
    if 'create_real_booking' in func_code or 'create_booking_from_parsed_data' in func_code:
        imports.add('from telegram_bot.services.booking_service import create_real_booking, create_booking_from_parsed_data')
    
    # Logging
    imports.add('import logging')
    
    return sorted(imports)

# Читаем app_old.py
app_old_path = Path(__file__).parent / 'app_old.py'
with open(app_old_path, 'r', encoding='utf-8') as f:
    app_old_content = f.read()

# Функции для переноса
functions_to_migrate = {
    'basic': ['start', 'menu', 'status_command', 'myid_command'],
    'rag': ['rag_search_command', 'rag_stats_command', 'rag_docs_command'],
    'weeek': [
        'weeek_info_command', 'weeek_create_task_command', 'weeek_projects_command',
        'weeek_create_project_command', 'weeek_update_command', 'weeek_tasks_command'
    ],
    'yadisk': ['yadisk_list_command', 'yadisk_search_command', 'yadisk_recent_command'],
    'email': ['email_check_command', 'email_draft_command', 'unsubscribe_command'],
    'tools': ['summary_command', 'demo_proposal_command', 'hypothesis_command', 'report_command', 'upload_document_command'],
}

print("Начинаю перенос функций...")
for module_name, func_names in functions_to_migrate.items():
    print(f"\nМодуль: {module_name}")
    module_path = Path(__file__).parent / 'handlers' / 'commands' / f'{module_name}.py'
    
    # Собираем все функции
    all_imports = set()
    all_functions = []
    
    for func_name in func_names:
        func_code = extract_function(app_old_content, func_name)
        if func_code:
            all_functions.append(func_code)
            imports = get_imports_for_function(func_code)
            all_imports.update(imports)
            print(f"  ✅ {func_name}")
        else:
            print(f"  ❌ {func_name} - не найдена")
    
    # Формируем содержимое файла
    file_content = f'"""\n{module_name.capitalize()} команды\n"""\n'
    file_content += '\n'.join(sorted(all_imports)) + '\n\n'
    file_content += 'log = logging.getLogger(__name__)\n\n'
    file_content += '\n\n'.join(all_functions) + '\n'
    
    # Записываем файл
    with open(module_path, 'w', encoding='utf-8') as f:
        f.write(file_content)
    
    print(f"  ✅ Файл {module_path} обновлен")

print("\n✅ Перенос завершен!")

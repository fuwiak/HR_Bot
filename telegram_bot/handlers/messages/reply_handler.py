"""
Обработчик сообщений (основная функция reply)
"""
import sys
from pathlib import Path
from telegram import Update
from telegram.ext import ContextTypes
import logging

# Добавляем корневую директорию проекта в sys.path
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

log = logging.getLogger(__name__)

# Импортируем функцию reply из app_old.py (временно)
# TODO: Перенести reply и все вспомогательные функции в отдельные модули
# reply очень большая функция (1102 строки) и использует много вспомогательных функций
app_old_path = project_root / "telegram_bot" / "app_old.py"
import importlib.util
spec = importlib.util.spec_from_file_location("app_old_handlers", app_old_path)
app_old_handlers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app_old_handlers)

# Экспортируем функцию
reply = app_old_handlers.reply

__all__ = ['reply']

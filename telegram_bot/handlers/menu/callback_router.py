"""
Роутер для callback кнопок
"""
# Временно импортируем из старого файла
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

app_old_path = project_root / "telegram_bot" / "app_old.py"

import importlib.util
spec = importlib.util.spec_from_file_location("app_old_handlers", app_old_path)
app_old_handlers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app_old_handlers)

# Экспортируем функцию
button_callback = app_old_handlers.button_callback

__all__ = ['button_callback']

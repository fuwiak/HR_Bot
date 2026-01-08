"""
Загрузчик конфигурации из YAML файлов
"""
import os
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional

log = logging.getLogger(__name__)

# Путь к директории с конфигами
CONFIG_DIR = Path(__file__).parent

# Кэш загруженных конфигов
_config_cache: Dict[str, Dict[str, Any]] = {}


def _expand_env_vars(value: Any) -> Any:
    """Рекурсивно заменяет переменные окружения в значениях"""
    if isinstance(value, str):
        # Обработка ${VAR} и ${VAR:-default}
        import re
        
        def replace_env(match):
            var_expr = match.group(1)
            if ':-' in var_expr:
                var_name, default = var_expr.split(':-', 1)
                return os.getenv(var_name, default)
            else:
                return os.getenv(var_expr, '')
        
        # Заменяем ${VAR} и ${VAR:-default}
        value = re.sub(r'\$\{([^}]+)\}', replace_env, value)
        
        # Если значение пустое после замены, возвращаем None
        if not value:
            return None
        
        return value
    elif isinstance(value, dict):
        return {k: _expand_env_vars(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [_expand_env_vars(item) for item in value]
    else:
        return value


def load_config(config_name: str) -> Dict[str, Any]:
    """
    Загрузить конфигурацию из YAML файла
    
    Args:
        config_name: Имя конфига (без расширения .yaml)
    
    Returns:
        Словарь с конфигурацией
    """
    if config_name in _config_cache:
        return _config_cache[config_name]
    
    config_path = CONFIG_DIR / f"{config_name}.yaml"
    
    if not config_path.exists():
        log.warning(f"⚠️ Конфиг {config_name}.yaml не найден в {CONFIG_DIR}")
        return {}
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        if config is None:
            config = {}
        
        # Заменяем переменные окружения
        config = _expand_env_vars(config)
        
        # Кэшируем
        _config_cache[config_name] = config
        
        log.info(f"✅ Загружен конфиг {config_name}.yaml")
        return config
    
    except Exception as e:
        log.error(f"❌ Ошибка загрузки конфига {config_name}.yaml: {e}")
        return {}


def get_config_value(config_name: str, key_path: str, default: Any = None) -> Any:
    """
    Получить значение из конфига по пути
    
    Args:
        config_name: Имя конфига
        key_path: Путь к значению через точку (например: "qdrant.collection_name")
        default: Значение по умолчанию
    
    Returns:
        Значение из конфига или default
    """
    config = load_config(config_name)
    
    keys = key_path.split('.')
    value = config
    
    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            return default
    
    return value


def reload_config(config_name: Optional[str] = None):
    """Перезагрузить конфиг(и) из файлов"""
    if config_name:
        if config_name in _config_cache:
            del _config_cache[config_name]
        load_config(config_name)
    else:
        _config_cache.clear()
        log.info("🔄 Все конфиги перезагружены")

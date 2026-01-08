"""
Управление whitelist источников для RAG.
Фильтрация документов по source_url.
"""

import yaml
import logging
from typing import List, Set, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class WhitelistManager:
    """Менеджер для работы с whitelist источников"""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = Path(config_path)
        self.allowed_domains: Set[str] = set()
        self.allowed_urls: Set[str] = set()
        self.load_config()
    
    def load_config(self) -> None:
        """Загружает whitelist из config.yaml"""
        try:
            if not self.config_path.exists():
                logger.warning(f"Config file {self.config_path} not found")
                return
            
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
            
            whitelist = config.get("whitelist", [])
            
            for url in whitelist:
                url = url.strip().rstrip("/")
                if url:
                    self.allowed_urls.add(url)
                    # Извлекаем домен
                    domain = self._extract_domain(url)
                    if domain:
                        self.allowed_domains.add(domain)
            
            logger.info(
                f"Loaded whitelist: {len(self.allowed_urls)} URLs, "
                f"{len(self.allowed_domains)} domains"
            )
            
        except Exception as e:
            logger.error(f"Error loading whitelist: {str(e)}")
    
    def _extract_domain(self, url: str) -> Optional[str]:
        """Извлекает домен из URL"""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc
            # Убираем www. если есть
            if domain.startswith("www."):
                domain = domain[4:]
            return domain
        except Exception:
            return None
    
    def is_allowed(self, url: str) -> bool:
        """
        Проверяет, разрешен ли источник по whitelist.
        
        Args:
            url: URL источника для проверки
        
        Returns:
            True если источник разрешен, False иначе
        """
        if not url:
            return False
        
        url = url.strip().rstrip("/")
        
        # Точное совпадение с URL
        if url in self.allowed_urls:
            return True
        
        # Проверка по домену (для HTTP/HTTPS URL)
        domain = self._extract_domain(url)
        if domain and domain in self.allowed_domains:
            return True
        
        # Проверка для file:// URL (Excel файлы)
        if url.startswith("file://"):
            # Проверяем, есть ли file:// URL в whitelist
            for allowed_url in self.allowed_urls:
                if allowed_url.startswith("file://"):
                    # Сравниваем пути файлов
                    file_path = url.replace("file://", "")
                    allowed_path = allowed_url.replace("file://", "")
                    # Проверяем, совпадает ли имя файла или путь
                    if file_path.endswith(allowed_path) or allowed_path in file_path:
                        return True
        
        # Проверка, начинается ли URL с разрешенного префикса
        for allowed_url in self.allowed_urls:
            if url.startswith(allowed_url):
                return True
        
        return False
    
    def filter_sources(self, sources: List[dict]) -> List[dict]:
        """
        Фильтрует список источников по whitelist.
        
        Args:
            sources: Список источников с полем source_url или url
        
        Returns:
            Отфильтрованный список разрешенных источников
        """
        filtered = []
        
        for source in sources:
            url = source.get("source_url") or source.get("url") or ""
            if self.is_allowed(url):
                filtered.append(source)
            else:
                logger.debug(f"Filtered out source: {url}")
        
        return filtered
    
    def get_allowed_urls(self) -> List[str]:
        """Возвращает список всех разрешенных URL"""
        return sorted(list(self.allowed_urls))
    
    def get_allowed_domains(self) -> List[str]:
        """Возвращает список всех разрешенных доменов"""
        return sorted(list(self.allowed_domains))
    
    def add_url(self, url: str) -> None:
        """Добавляет URL в whitelist"""
        url = url.strip().rstrip("/")
        if url:
            self.allowed_urls.add(url)
            domain = self._extract_domain(url)
            if domain:
                self.allowed_domains.add(domain)
            logger.info(f"Added to whitelist: {url}")
    
    def remove_url(self, url: str) -> None:
        """Удаляет URL из whitelist"""
        url = url.strip().rstrip("/")
        if url in self.allowed_urls:
            self.allowed_urls.remove(url)
            domain = self._extract_domain(url)
            if domain:
                # Проверяем, нет ли других URL с этим доменом
                has_other = any(
                    self._extract_domain(u) == domain 
                    for u in self.allowed_urls
                )
                if not has_other:
                    self.allowed_domains.discard(domain)
            logger.info(f"Removed from whitelist: {url}")


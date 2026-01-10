"""
Модуль для скрапинга страниц из whitelist для загрузки в RAG.
"""

import logging
import httpx
from typing import List, Dict, Any, Optional
from pathlib import Path
from urllib.parse import urljoin, urlparse
import re

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class WebScraper:
    """Скрапер для загрузки контента с веб-страниц из whitelist"""
    
    def __init__(self, timeout: int = 30, max_content_length: int = 10 * 1024 * 1024):
        """
        Инициализирует скрапер.
        
        Args:
            timeout: Таймаут запроса в секундах
            max_content_length: Максимальный размер контента в байтах (10MB по умолчанию)
        """
        self.timeout = timeout
        self.max_content_length = max_content_length
        self.client = httpx.AsyncClient(
            timeout=self.timeout,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
        )
    
    async def scrape_url(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Скрапит одну страницу.
        
        Args:
            url: URL страницы для скрапинга
        
        Returns:
            Словарь с контентом и метаданными или None при ошибке
        """
        try:
            logger.info(f"Scraping URL: {url}")
            
            response = await self.client.get(url)
            response.raise_for_status()
            
            # Проверяем размер контента
            content_length = len(response.content)
            if content_length > self.max_content_length:
                logger.warning(f"Content too large ({content_length} bytes), skipping: {url}")
                return None
            
            # Проверяем Content-Type
            content_type = response.headers.get("Content-Type", "").lower()
            if "text/html" not in content_type:
                logger.warning(f"Not HTML content ({content_type}), skipping: {url}")
                return None
            
            # Парсим HTML
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Удаляем ненужные элементы (скрипты, стили, навигация)
            for tag in soup.find_all(["script", "style", "nav", "header", "footer", "aside"]):
                tag.decompose()
            
            # Извлекаем текст
            title = soup.find("title")
            title_text = title.get_text(strip=True) if title else ""
            
            # Ищем основной контент (article, main, или body)
            main_content = (
                soup.find("article") or
                soup.find("main") or
                soup.find("div", class_=re.compile(r"content|article|main", re.I)) or
                soup.find("body")
            )
            
            if main_content:
                text = main_content.get_text(separator="\n", strip=True)
            else:
                text = soup.get_text(separator="\n", strip=True)
            
            # Очищаем текст (убираем лишние пробелы и переносы)
            lines = [line.strip() for line in text.split("\n") if line.strip()]
            text = "\n".join(lines)
            
            # Ограничиваем размер текста (первые 50000 символов)
            if len(text) > 50000:
                text = text[:50000] + "... [content truncated]"
            
            if not text or len(text) < 100:
                logger.warning(f"Content too short, skipping: {url}")
                return None
            
            return {
                "url": url,
                "title": title_text,
                "text": text,
                "content_length": len(text),
                "status_code": response.status_code
            }
            
        except httpx.TimeoutException:
            logger.error(f"Timeout scraping URL: {url}")
            return None
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error {e.response.status_code} scraping URL: {url}")
            return None
        except Exception as e:
            logger.error(f"Error scraping URL {url}: {str(e)}")
            return None
    
    async def scrape_multiple_urls(self, urls: List[str]) -> List[Dict[str, Any]]:
        """
        Скрапит несколько URL параллельно.
        
        Args:
            urls: Список URL для скрапинга
        
        Returns:
            Список словарей с контентом
        """
        import asyncio
        
        tasks = [self.scrape_url(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Фильтруем None и исключения
        scraped = []
        for result in results:
            if isinstance(result, dict):
                scraped.append(result)
            elif isinstance(result, Exception):
                logger.error(f"Exception during scraping: {str(result)}")
        
        return scraped
    
    def extract_links(self, url: str, html_content: str) -> List[str]:
        """
        Извлекает ссылки со страницы (для дальнейшего скрапинга).
        
        Args:
            url: Базовый URL страницы
            html_content: HTML контент страницы
        
        Returns:
            Список абсолютных URL ссылок
        """
        try:
            soup = BeautifulSoup(html_content, "html.parser")
            links = []
            
            for link in soup.find_all("a", href=True):
                href = link["href"]
                absolute_url = urljoin(url, href)
                
                # Фильтруем только HTTP/HTTPS ссылки
                if absolute_url.startswith("http"):
                    parsed = urlparse(absolute_url)
                    # Можно добавить фильтрацию по домену
                    links.append(absolute_url)
            
            return list(set(links))  # Убираем дубликаты
            
        except Exception as e:
            logger.error(f"Error extracting links from {url}: {str(e)}")
            return []
    
    async def close(self):
        """Закрывает HTTP клиент"""
        await self.client.aclose()


async def scrape_whitelist_urls(
    whitelist_urls: List[str],
    max_pages: int = 50,
    qdrant_loader=None
) -> int:
    """
    Скрапит страницы из whitelist и загружает в Qdrant.
    
    Args:
        whitelist_urls: Список URL из whitelist
        max_pages: Максимальное количество страниц для скрапинга
        qdrant_loader: Экземпляр QdrantLoader для загрузки в БД
    
    Returns:
        Количество загруженных страниц
    """
    if not qdrant_loader:
        from qdrant_loader import QdrantLoader
        qdrant_loader = QdrantLoader()
    
    scraper = WebScraper()
    
    try:
        # Фильтруем только HTTP/HTTPS URL
        web_urls = [url for url in whitelist_urls if url.startswith("http")]
        
        if not web_urls:
            logger.warning("No web URLs in whitelist to scrape")
            return 0
        
        # Ограничиваем количество URL
        urls_to_scrape = web_urls[:max_pages]
        
        logger.info(f"Scraping {len(urls_to_scrape)} URLs from whitelist...")
        
        # Скрапим URL
        scraped_pages = await scraper.scrape_multiple_urls(urls_to_scrape)
        
        if not scraped_pages:
            logger.warning("No pages scraped successfully")
            return 0
        
        # Загружаем в Qdrant
        loaded_count = 0
        for page in scraped_pages:
            try:
                metadata = {
                    "source_url": page["url"],
                    "source_type": "web_scraped",
                    "title": page.get("title", ""),
                    "content_length": page.get("content_length", 0)
                }
                
                chunks = qdrant_loader.load_document(
                    text=page["text"],
                    metadata=metadata,
                    filter_by_whitelist=True  # Проверяем whitelist
                )
                
                if chunks > 0:
                    loaded_count += 1
                    logger.info(f"Loaded {chunks} chunks from {page['url']}")
                    
            except Exception as e:
                logger.error(f"Error loading page {page.get('url')} to Qdrant: {str(e)}")
                continue
        
        logger.info(f"Successfully loaded {loaded_count} pages from whitelist to Qdrant")
        return loaded_count
        
    finally:
        await scraper.close()


if __name__ == "__main__":
    import asyncio
    try:
        from services.rag.whitelist import WhitelistManager
    except ImportError:
        from whitelist import WhitelistManager
    
    async def main():
        whitelist = WhitelistManager()
        urls = whitelist.get_allowed_urls()
        
        print(f"Scraping {len(urls)} URLs from whitelist...")
        loaded = await scrape_whitelist_urls(urls, max_pages=20)
        print(f"Loaded {loaded} pages to Qdrant")
    
    asyncio.run(main())










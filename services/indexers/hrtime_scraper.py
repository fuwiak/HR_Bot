"""
Скрапер для сайта HR Time и профиля консультанта
Скрапит информацию с hrtime.ru для добавления в RAG базу знаний
"""
import logging
import httpx
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, urlparse
import re
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class HRTimeScraper:
    """Скрапер для сайта HR Time"""
    
    def __init__(self, timeout: int = 30, max_content_length: int = 10 * 1024 * 1024):
        """
        Инициализирует скрапер.
        
        Args:
            timeout: Таймаут запроса в секундах
            max_content_length: Максимальный размер контента в байтах (10MB по умолчанию)
        """
        self.timeout = timeout
        self.max_content_length = max_content_length
        self.base_url = "https://hrtime.ru"
        self.client = httpx.AsyncClient(
            timeout=self.timeout,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
        )
    
    async def scrape_profile(self, profile_id: str) -> Optional[Dict[str, Any]]:
        """
        Скрапит профиль консультанта на HR Time.
        
        Args:
            profile_id: ID профиля (например, "29664")
        
        Returns:
            Словарь с данными профиля или None при ошибке
        """
        try:
            profile_url = f"{self.base_url}/profile.php?userid={profile_id}"
            logger.info(f"Scraping HR Time profile: {profile_url}")
            
            response = await self.client.get(profile_url)
            response.raise_for_status()
            
            # Проверяем размер контента
            content_length = len(response.content)
            if content_length > self.max_content_length:
                logger.warning(f"Content too large ({content_length} bytes), skipping: {profile_url}")
                return None
            
            # Парсим HTML
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Удаляем ненужные элементы
            for tag in soup.find_all(["script", "style", "nav", "header", "footer", "aside"]):
                tag.decompose()
            
            # Извлекаем информацию о профиле
            profile_data = {
                "url": profile_url,
                "profile_id": profile_id,
                "title": "",
                "text": "",
                "services": [],
                "description": "",
                "content_length": 0,
                "status_code": response.status_code
            }
            
            # Извлекаем заголовок
            title_tag = soup.find("title")
            if title_tag:
                profile_data["title"] = title_tag.get_text(strip=True)
            
            # Ищем основной контент профиля
            main_content = (
                soup.find("div", class_=re.compile(r"profile|content|main", re.I)) or
                soup.find("main") or
                soup.find("article") or
                soup.find("body")
            )
            
            if main_content:
                # Извлекаем описание профиля
                description_tag = (
                    main_content.find("div", class_=re.compile(r"description|about|bio", re.I)) or
                    main_content.find("p", class_=re.compile(r"description|about", re.I))
                )
                if description_tag:
                    profile_data["description"] = description_tag.get_text(separator="\n", strip=True)
                
                # Извлекаем список услуг
                services_section = main_content.find("div", class_=re.compile(r"services|uslugi", re.I))
                if services_section:
                    service_links = services_section.find_all("a", href=re.compile(r"/usluga/"))
                    for link in service_links:
                        service_name = link.get_text(strip=True)
                        service_url = urljoin(self.base_url, link.get("href", ""))
                        if service_name:
                            profile_data["services"].append({
                                "name": service_name,
                                "url": service_url
                            })
                
                # Извлекаем весь текст
                text = main_content.get_text(separator="\n", strip=True)
            else:
                text = soup.get_text(separator="\n", strip=True)
            
            # Очищаем текст
            lines = [line.strip() for line in text.split("\n") if line.strip()]
            text = "\n".join(lines)
            
            # Добавляем информацию об услугах в текст
            if profile_data["services"]:
                services_text = "\n\nУслуги консультанта:\n"
                for service in profile_data["services"]:
                    services_text += f"- {service['name']} ({service['url']})\n"
                text = f"{text}\n{services_text}"
            
            # Ограничиваем размер текста
            if len(text) > 50000:
                text = text[:50000] + "... [content truncated]"
            
            profile_data["text"] = text
            profile_data["content_length"] = len(text)
            
            if not text or len(text) < 100:
                logger.warning(f"Content too short, skipping: {profile_url}")
                return None
            
            logger.info(f"Successfully scraped profile {profile_id}: {len(text)} characters")
            return profile_data
            
        except httpx.TimeoutException:
            logger.error(f"Timeout scraping HR Time profile: {profile_id}")
            return None
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error {e.response.status_code} scraping HR Time profile: {profile_id}")
            return None
        except Exception as e:
            logger.error(f"Error scraping HR Time profile {profile_id}: {str(e)}")
            return None
    
    async def scrape_service(self, service_url: str) -> Optional[Dict[str, Any]]:
        """
        Скрапит страницу услуги на HR Time.
        
        Args:
            service_url: URL услуги (может быть относительным или абсолютным)
        
        Returns:
            Словарь с данными услуги или None при ошибке
        """
        try:
            # Преобразуем относительный URL в абсолютный
            if not service_url.startswith("http"):
                service_url = urljoin(self.base_url, service_url)
            
            logger.info(f"Scraping HR Time service: {service_url}")
            
            response = await self.client.get(service_url)
            response.raise_for_status()
            
            # Проверяем размер контента
            content_length = len(response.content)
            if content_length > self.max_content_length:
                logger.warning(f"Content too large ({content_length} bytes), skipping: {service_url}")
                return None
            
            # Парсим HTML
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Удаляем ненужные элементы
            for tag in soup.find_all(["script", "style", "nav", "header", "footer", "aside"]):
                tag.decompose()
            
            # Извлекаем информацию об услуге
            service_data = {
                "url": service_url,
                "title": "",
                "text": "",
                "price": "",
                "description": "",
                "content_length": 0,
                "status_code": response.status_code
            }
            
            # Извлекаем заголовок
            title_tag = soup.find("title")
            if title_tag:
                service_data["title"] = title_tag.get_text(strip=True)
            
            # Ищем основной контент
            main_content = (
                soup.find("div", class_=re.compile(r"service|content|main|article", re.I)) or
                soup.find("main") or
                soup.find("article") or
                soup.find("body")
            )
            
            if main_content:
                # Извлекаем описание услуги
                description_tag = (
                    main_content.find("div", class_=re.compile(r"description|about|content", re.I)) or
                    main_content.find("p", class_=re.compile(r"description|about", re.I))
                )
                if description_tag:
                    service_data["description"] = description_tag.get_text(separator="\n", strip=True)
                
                # Ищем цену
                price_tag = (
                    main_content.find("div", class_=re.compile(r"price|cost|стоимость", re.I)) or
                    main_content.find("span", class_=re.compile(r"price|cost", re.I))
                )
                if price_tag:
                    service_data["price"] = price_tag.get_text(strip=True)
                
                # Извлекаем весь текст
                text = main_content.get_text(separator="\n", strip=True)
            else:
                text = soup.get_text(separator="\n", strip=True)
            
            # Добавляем цену в текст, если найдена
            if service_data["price"]:
                text = f"Стоимость: {service_data['price']}\n\n{text}"
            
            # Очищаем текст
            lines = [line.strip() for line in text.split("\n") if line.strip()]
            text = "\n".join(lines)
            
            # Ограничиваем размер текста
            if len(text) > 50000:
                text = text[:50000] + "... [content truncated]"
            
            service_data["text"] = text
            service_data["content_length"] = len(text)
            
            if not text or len(text) < 100:
                logger.warning(f"Content too short, skipping: {service_url}")
                return None
            
            logger.info(f"Successfully scraped service: {len(text)} characters")
            return service_data
            
        except httpx.TimeoutException:
            logger.error(f"Timeout scraping HR Time service: {service_url}")
            return None
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error {e.response.status_code} scraping HR Time service: {service_url}")
            return None
        except Exception as e:
            logger.error(f"Error scraping HR Time service {service_url}: {str(e)}")
            return None
    
    async def scrape_website_pages(self, max_pages: int = 10) -> List[Dict[str, Any]]:
        """
        Скрапит основные страницы сайта HR Time.
        
        Args:
            max_pages: Максимальное количество страниц для скрапинга
        
        Returns:
            Список словарей с данными страниц
        """
        pages_to_scrape = [
            f"{self.base_url}/",
            f"{self.base_url}/about",
            f"{self.base_url}/services",
            f"{self.base_url}/contacts",
        ]
        
        # Ограничиваем количество страниц
        pages_to_scrape = pages_to_scrape[:max_pages]
        
        results = []
        for url in pages_to_scrape:
            try:
                logger.info(f"Scraping HR Time page: {url}")
                
                response = await self.client.get(url)
                response.raise_for_status()
                
                # Проверяем размер контента
                content_length = len(response.content)
                if content_length > self.max_content_length:
                    logger.warning(f"Content too large ({content_length} bytes), skipping: {url}")
                    continue
                
                # Парсим HTML
                soup = BeautifulSoup(response.text, "html.parser")
                
                # Удаляем ненужные элементы
                for tag in soup.find_all(["script", "style", "nav", "header", "footer", "aside"]):
                    tag.decompose()
                
                # Извлекаем текст
                title_tag = soup.find("title")
                title_text = title_tag.get_text(strip=True) if title_tag else ""
                
                main_content = (
                    soup.find("main") or
                    soup.find("article") or
                    soup.find("div", class_=re.compile(r"content|main", re.I)) or
                    soup.find("body")
                )
                
                if main_content:
                    text = main_content.get_text(separator="\n", strip=True)
                else:
                    text = soup.get_text(separator="\n", strip=True)
                
                # Очищаем текст
                lines = [line.strip() for line in text.split("\n") if line.strip()]
                text = "\n".join(lines)
                
                # Ограничиваем размер текста
                if len(text) > 50000:
                    text = text[:50000] + "... [content truncated]"
                
                if text and len(text) >= 100:
                    results.append({
                        "url": url,
                        "title": title_text,
                        "text": text,
                        "content_length": len(text),
                        "status_code": response.status_code
                    })
                    logger.info(f"Successfully scraped page: {url} ({len(text)} characters)")
                
            except Exception as e:
                logger.error(f"Error scraping HR Time page {url}: {str(e)}")
                continue
        
        return results
    
    async def close(self):
        """Закрывает HTTP клиент"""
        await self.client.aclose()


async def scrape_hrtime_to_qdrant(
    profile_id: str = "29664",
    qdrant_loader=None,
    max_services: int = 20
) -> int:
    """
    Скрапит профиль и услуги HR Time и загружает в Qdrant.
    
    Args:
        profile_id: ID профиля на HR Time
        qdrant_loader: Экземпляр QdrantLoader для загрузки в БД
        max_services: Максимальное количество услуг для скрапинга
    
    Returns:
        Количество загруженных документов
    """
    if not qdrant_loader:
        from services.rag.qdrant_loader import QdrantLoader
        qdrant_loader = QdrantLoader()
    
    scraper = HRTimeScraper()
    loaded_count = 0
    
    try:
        # Скрапим профиль
        profile_data = await scraper.scrape_profile(profile_id)
        if profile_data:
            try:
                metadata = {
                    "source_url": profile_data["url"],
                    "source_type": "hrtime_profile",
                    "title": profile_data.get("title", f"Профиль HR Time {profile_id}"),
                    "profile_id": profile_id,
                    "content_length": profile_data.get("content_length", 0)
                }
                
                chunks = qdrant_loader.load_document(
                    text=profile_data["text"],
                    metadata=metadata,
                    filter_by_whitelist=False  # HR Time не в whitelist, но разрешаем загрузку
                )
                
                if chunks > 0:
                    loaded_count += 1
                    logger.info(f"Loaded {chunks} chunks from HR Time profile {profile_id}")
                    
                    # Скрапим услуги из профиля
                    services = profile_data.get("services", [])
                    for service in services[:max_services]:
                        service_data = await scraper.scrape_service(service["url"])
                        if service_data:
                            try:
                                service_metadata = {
                                    "source_url": service_data["url"],
                                    "source_type": "hrtime_service",
                                    "title": service_data.get("title", service["name"]),
                                    "profile_id": profile_id,
                                    "service_name": service["name"],
                                    "price": service_data.get("price", ""),
                                    "content_length": service_data.get("content_length", 0)
                                }
                                
                                service_chunks = qdrant_loader.load_document(
                                    text=service_data["text"],
                                    metadata=service_metadata,
                                    filter_by_whitelist=False
                                )
                                
                                if service_chunks > 0:
                                    loaded_count += 1
                                    logger.info(f"Loaded {service_chunks} chunks from HR Time service: {service['name']}")
                                    
                            except Exception as e:
                                logger.error(f"Error loading HR Time service {service['url']} to Qdrant: {str(e)}")
                                continue
                                
            except Exception as e:
                logger.error(f"Error loading HR Time profile to Qdrant: {str(e)}")
        
        # Скрапим основные страницы сайта
        website_pages = await scraper.scrape_website_pages(max_pages=5)
        for page in website_pages:
            try:
                page_metadata = {
                    "source_url": page["url"],
                    "source_type": "hrtime_website",
                    "title": page.get("title", "HR Time"),
                    "content_length": page.get("content_length", 0)
                }
                
                page_chunks = qdrant_loader.load_document(
                    text=page["text"],
                    metadata=page_metadata,
                    filter_by_whitelist=False
                )
                
                if page_chunks > 0:
                    loaded_count += 1
                    logger.info(f"Loaded {page_chunks} chunks from HR Time page: {page['url']}")
                    
            except Exception as e:
                logger.error(f"Error loading HR Time page {page.get('url')} to Qdrant: {str(e)}")
                continue
        
        logger.info(f"Successfully loaded {loaded_count} documents from HR Time to Qdrant")
        return loaded_count
        
    finally:
        await scraper.close()


if __name__ == "__main__":
    import asyncio
    
    async def main():
        profile_id = "29664"  # ID профиля Анастасии Новосёловой
        loaded = await scrape_hrtime_to_qdrant(profile_id=profile_id, max_services=10)
        print(f"Loaded {loaded} documents from HR Time to Qdrant")
    
    asyncio.run(main())

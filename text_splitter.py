"""
Легкая реализация text splitter без зависимостей от langchain.
Замена для RecursiveCharacterTextSplitter из langchain-text-splitters.
"""

from typing import List, Callable, Tuple


class RecursiveCharacterTextSplitter:
    """
    Легкая реализация рекурсивного разбиения текста на чанки.
    Аналог RecursiveCharacterTextSplitter из langchain-text-splitters.
    """
    
    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        length_function: Callable[[str], int] = len,
        separators: List[str] = None
    ):
        """
        Args:
            chunk_size: Максимальный размер чанка
            chunk_overlap: Перекрытие между чанками
            length_function: Функция для подсчета длины текста
            separators: Список разделителей для разбиения (по приоритету)
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.length_function = length_function
        self.separators = separators or ["\n\n", "\n", " ", ""]
    
    def split_text(self, text: str) -> List[str]:
        """
        Разбивает текст на чанки с использованием рекурсивного подхода.
        
        Args:
            text: Текст для разбиения
            
        Returns:
            Список чанков текста
        """
        if not text:
            return []
        
        # Если текст меньше chunk_size, возвращаем как есть
        if self.length_function(text) <= self.chunk_size:
            return [text]
        
        chunks = []
        current_text = text
        
        while current_text:
            # Пытаемся найти подходящий разделитель
            chunk, remaining = self._split_text_recursive(
                current_text,
                self.separators
            )
            
            if chunk:
                chunks.append(chunk)
            
            if not remaining or remaining == current_text:
                # Если не удалось разбить, берем chunk_size символов
                if self.length_function(current_text) > self.chunk_size:
                    chunk = current_text[:self.chunk_size]
                    chunks.append(chunk)
                    current_text = current_text[self.chunk_size - self.chunk_overlap:]
                else:
                    chunks.append(current_text)
                    break
            else:
                current_text = remaining
        
        # Объединяем маленькие чанки
        return self._merge_small_chunks(chunks)
    
    def _split_text_recursive(
        self,
        text: str,
        separators: List[str]
    ) -> Tuple[str, str]:
        """
        Рекурсивно разбивает текст используя разделители по приоритету.
        
        Args:
            text: Текст для разбиения
            separators: Список разделителей
            
        Returns:
            Кортеж (chunk, remaining_text)
        """
        if not separators:
            # Если разделителей нет, берем chunk_size символов
            if self.length_function(text) <= self.chunk_size:
                return text, ""
            return text[:self.chunk_size], text[self.chunk_size:]
        
        separator = separators[0]
        remaining_separators = separators[1:]
        
        if separator == "":
            # Последний разделитель - разбиваем по символам
            if self.length_function(text) <= self.chunk_size:
                return text, ""
            return text[:self.chunk_size], text[self.chunk_size:]
        
        # Ищем разделитель в тексте
        if separator in text:
            splits = text.split(separator)
            current_chunk = ""
            
            for i, split in enumerate(splits):
                # Добавляем разделитель обратно (кроме последнего)
                if i < len(splits) - 1:
                    test_chunk = current_chunk + split + separator
                else:
                    test_chunk = current_chunk + split
                
                if self.length_function(test_chunk) <= self.chunk_size:
                    current_chunk = test_chunk
                else:
                    # Текущий чанк готов
                    if current_chunk:
                        remaining = separator.join(splits[i:])
                        return current_chunk, remaining
                    else:
                        # Даже один split слишком большой, рекурсивно разбиваем
                        return self._split_text_recursive(
                            split,
                            remaining_separators
                        )
            
            # Весь текст поместился в один чанк
            return current_chunk, ""
        else:
            # Разделитель не найден, пробуем следующий
            return self._split_text_recursive(text, remaining_separators)
    
    def _merge_small_chunks(self, chunks: List[str]) -> List[str]:
        """
        Объединяет маленькие чанки для оптимизации.
        
        Args:
            chunks: Список чанков
            
        Returns:
            Оптимизированный список чанков
        """
        if not chunks:
            return []
        
        merged = []
        current_chunk = ""
        
        for chunk in chunks:
            test_chunk = current_chunk + "\n\n" + chunk if current_chunk else chunk
            
            if self.length_function(test_chunk) <= self.chunk_size:
                current_chunk = test_chunk
            else:
                if current_chunk:
                    merged.append(current_chunk)
                current_chunk = chunk
        
        if current_chunk:
            merged.append(current_chunk)
        
        return merged
    
    def create_documents(self, texts: List[str]) -> List[dict]:
        """
        Создает документы из списка текстов.
        Совместимо с API langchain.
        
        Args:
            texts: Список текстов
            
        Returns:
            Список словарей с ключом 'page_content'
        """
        documents = []
        for text in texts:
            chunks = self.split_text(text)
            for chunk in chunks:
                documents.append({"page_content": chunk})
        return documents

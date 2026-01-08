# Добавляем функцию для индексации сообщений
def index_message_to_qdrant(text: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
    """
    Индексировать сообщение Telegram в Qdrant для RAG
    
    Args:
        text: Текст сообщения
        metadata: Метаданные сообщения (user_id, message_id, etc.)
    
    Returns:
        True если успешно, False при ошибке
    """
    if not text or not text.strip():
        return False
    
    try:
        # Генерируем эмбеддинг
        embedding = generate_embedding(text)
        if not embedding:
            log.warning("⚠️ Не удалось сгенерировать эмбеддинг для сообщения")
            return False
        
        # Получаем клиент Qdrant
    client = get_qdrant_client()
    if not client:
            log.warning("⚠️ Qdrant клиент недоступен")
            return False
        
        # Убеждаемся что коллекция существует
        if not ensure_collection():
            log.error("❌ Не удалось создать/проверить коллекцию")
            return False
        
        # Подготавливаем метаданные
        payload = {
            "source": "telegram_message",
            "text": text,
            "timestamp": datetime.now().isoformat()
        }
        if metadata:
            payload.update(metadata)
        
        # Генерируем ID для точки
        import hashlib
        text_hash = hashlib.md5(f"{text}{metadata.get('message_id', '')}".encode()).hexdigest()
        point_id = int(text_hash[:8], 16)
        
        # Добавляем точку в Qdrant
        client.upsert(
            collection_name=COLLECTION_NAME,
            points=[
                PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload=payload
                )
            ]
        )
        
        log.info(f"✅ Сообщение индексировано в Qdrant (point_id={point_id})")
        return True
        
    except Exception as e:
        log.error(f"❌ Ошибка индексации сообщения в Qdrant: {e}")
        import traceback
        log.error(f"❌ Traceback: {traceback.format_exc()}")
        return False

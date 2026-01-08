"""
Обработчики сообщений
"""
from .reply_handler import reply
from .document_handler import handle_document

__all__ = ['reply', 'handle_document']

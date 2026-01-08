"""
Модели базы данных
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

log = logging.getLogger(__name__)


class UserModel:
    """Модель пользователя"""
    
    def __init__(
        self,
        user_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        phone: Optional[str] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None
    ):
        self.user_id = user_id
        self.username = username
        self.first_name = first_name
        self.last_name = last_name
        self.phone = phone
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "username": self.username,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "phone": self.phone,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserModel":
        return cls(
            user_id=data.get("user_id"),
            username=data.get("username"),
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
            phone=data.get("phone"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at")
        )


class MessageModel:
    """Модель сообщения"""
    
    def __init__(
        self,
        id: Optional[int] = None,
        user_id: int = None,
        role: str = "user",
        content: str = "",
        platform: str = "telegram",
        created_at: Optional[datetime] = None
    ):
        self.id = id
        self.user_id = user_id
        self.role = role
        self.content = content
        self.platform = platform
        self.created_at = created_at or datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "role": self.role,
            "content": self.content,
            "platform": self.platform,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MessageModel":
        return cls(
            id=data.get("id"),
            user_id=data.get("user_id"),
            role=data.get("role", "user"),
            content=data.get("content", ""),
            platform=data.get("platform", "telegram"),
            created_at=data.get("created_at")
        )


class BookingModel:
    """Модель записи/бронирования"""
    
    def __init__(
        self,
        id: Optional[int] = None,
        user_id: int = None,
        service_name: str = "",
        master_name: str = "",
        date_time: Optional[datetime] = None,
        client_name: str = "",
        client_phone: str = "",
        status: str = "pending",
        created_at: Optional[datetime] = None
    ):
        self.id = id
        self.user_id = user_id
        self.service_name = service_name
        self.master_name = master_name
        self.date_time = date_time
        self.client_name = client_name
        self.client_phone = client_phone
        self.status = status
        self.created_at = created_at or datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "service_name": self.service_name,
            "master_name": self.master_name,
            "date_time": self.date_time.isoformat() if self.date_time else None,
            "client_name": self.client_name,
            "client_phone": self.client_phone,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BookingModel":
        return cls(
            id=data.get("id"),
            user_id=data.get("user_id"),
            service_name=data.get("service_name", ""),
            master_name=data.get("master_name", ""),
            date_time=data.get("date_time"),
            client_name=data.get("client_name", ""),
            client_phone=data.get("client_phone", ""),
            status=data.get("status", "pending"),
            created_at=data.get("created_at")
        )


class ServiceModel:
    """Модель услуги"""
    
    def __init__(
        self,
        id: Optional[int] = None,
        title: str = "",
        price: int = 0,
        price_str: str = "",
        duration: int = 0,
        master: str = "",
        description: str = "",
        category: str = ""
    ):
        self.id = id
        self.title = title
        self.price = price
        self.price_str = price_str
        self.duration = duration
        self.master = master
        self.description = description
        self.category = category
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "price": self.price,
            "price_str": self.price_str,
            "duration": self.duration,
            "master": self.master,
            "description": self.description,
            "category": self.category
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ServiceModel":
        return cls(
            id=data.get("id"),
            title=data.get("title", ""),
            price=data.get("price", 0),
            price_str=data.get("price_str", ""),
            duration=data.get("duration", 0),
            master=data.get("master", ""),
            description=data.get("description", ""),
            category=data.get("category", "")
        )

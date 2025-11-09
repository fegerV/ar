from sqlalchemy import create_engine, Column, String, DateTime, Boolean, Integer, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker
from datetime import datetime
from pydantic import BaseModel
from typing import Optional, List, Generator
import os
from dotenv import load_dotenv

from app.config import settings
from logging_setup import get_logger

logger = get_logger(__name__)

load_dotenv()


def _build_database_url() -> str:
    """Resolve database URL for notifications storage."""
    env_url = os.getenv("NOTIFICATIONS_DATABASE_URL") or os.getenv("DATABASE_URL")
    if env_url:
        if env_url.startswith("sqlite:///") and not env_url.startswith("sqlite:////"):
            relative_path = env_url.replace("sqlite:///", "", 1)
            resolved_path = (settings.BASE_DIR / relative_path).resolve()
            return f"sqlite:///{resolved_path.as_posix()}"
        return env_url
    return f"sqlite:///{settings.DB_PATH.as_posix()}"


DATABASE_URL = _build_database_url()

engine_kwargs = {}
if DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    user_id = Column(String, nullable=True) # ID пользователя, если уведомление персонализировано
    notification_type = Column(String, default="info")  # info, success, warning, error
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)  # Время, после которого уведомление считается устаревшим


class NotificationCreate(BaseModel):
    title: str
    message: str
    user_id: Optional[str] = None
    notification_type: Optional[str] = "info"


class NotificationUpdate(BaseModel):
    is_read: Optional[bool] = None


class NotificationResponse(BaseModel):
    id: int
    title: str
    message: str
    user_id: Optional[str]
    notification_type: str
    is_read: bool
    created_at: datetime
    expires_at: Optional[datetime]

    class Config:
        orm_mode = True


# Создание таблицы уведомлений
Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_notification(db: Session, notification: NotificationCreate) -> Notification:
    """Создает новое уведомление"""
    try:
        db_notification = Notification(
            title=notification.title,
            message=notification.message,
            user_id=notification.user_id,
            notification_type=notification.notification_type
        )
        db.add(db_notification)
        db.commit()
        db.refresh(db_notification)
        return db_notification
    except Exception as e:
        logger.error(f"Error creating notification: {e}")
        db.rollback()
        raise


def get_notifications(
    db: Session,
    user_id: Optional[str] = None,
    limit: int = 100,
    unread_only: bool = False,
) -> List[Notification]:
    """Получает список уведомлений"""
    try:
        query = db.query(Notification)
        
        if user_id:
            query = query.filter(Notification.user_id == user_id)
        
        if unread_only:
            query = query.filter(Notification.is_read == False)
        
        query = query.order_by(Notification.created_at.desc())
        query = query.limit(limit)
        
        return query.all()
    except Exception as e:
        logger.error(f"Error getting notifications: {e}")
        raise


def get_notification(db: Session, notification_id: int) -> Optional[Notification]:
    """Получает конкретное уведомление"""
    try:
        return db.query(Notification).filter(Notification.id == notification_id).first()
    except Exception as e:
        logger.error(f"Error getting notification {notification_id}: {e}")
        raise


def update_notification(
    db: Session,
    notification_id: int,
    notification_update: NotificationUpdate,
) -> Optional[Notification]:
    """Обновляет уведомление (например, помечает как прочитанное)"""
    try:
        db_notification = db.query(Notification).filter(Notification.id == notification_id).first()
        if db_notification:
            if notification_update.is_read is not None:
                db_notification.is_read = notification_update.is_read
            db.commit()
            db.refresh(db_notification)
        return db_notification
    except Exception as e:
        logger.error(f"Error updating notification {notification_id}: {e}")
        db.rollback()
        raise


def delete_notification(db: Session, notification_id: int) -> Optional[Notification]:
    """Удаляет уведомление"""
    try:
        db_notification = db.query(Notification).filter(Notification.id == notification_id).first()
        if db_notification:
            db.delete(db_notification)
            db.commit()
        return db_notification
    except Exception as e:
        logger.error(f"Error deleting notification {notification_id}: {e}")
        db.rollback()
        raise


def mark_all_as_read(db: Session, user_id: Optional[str] = None) -> None:
    """Помечает все уведомления как прочитанные"""
    try:
        query = db.query(Notification).filter(Notification.is_read == False)
        
        if user_id:
            query = query.filter(Notification.user_id == user_id)
        
        query.update({Notification.is_read: True})
        db.commit()
    except Exception as e:
        logger.error(f"Error marking notifications as read: {e}")
        db.rollback()
        raise


def send_notification(title: str, message: str, user_id: Optional[str] = None, notification_type: str = "info"):
    """Вспомогательная функция для отправки уведомлений"""
    try:
        db = next(get_db())
        try:
            notification_data = NotificationCreate(
                title=title,
                message=message,
                user_id=user_id,
                notification_type=notification_type
            )
            return create_notification(db, notification_data)
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error sending notification: {e}")
        raise


def get_user_unread_count(db: Session, user_id: str) -> int:
    """Получает количество непрочитанных уведомлений для пользователя"""
    try:
        return db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.is_read == False
        ).count()
    except Exception as e:
        logger.error(f"Error getting unread count for user {user_id}: {e}")
        raise


def cleanup_expired_notifications(db: Session) -> None:
    """Удаляет устаревшие уведомления"""
    try:
        from datetime import datetime
        current_time = datetime.utcnow()
        expired_notifications = db.query(Notification).filter(
            Notification.expires_at != None,
            Notification.expires_at < current_time
        ).all()
        
        for notification in expired_notifications:
            db.delete(notification)
        
        db.commit()
    except Exception as e:
        logger.error(f"Error cleaning up expired notifications: {e}")
        db.rollback()
        raise
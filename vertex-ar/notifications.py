from sqlalchemy import create_engine, Column, String, DateTime, Boolean, Integer, Text, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker
from datetime import datetime
from pydantic import BaseModel
from typing import Optional, List, Generator, Dict, Any
import os
from dotenv import load_dotenv
import enum
import csv
import json
from io import StringIO

from app.config import settings
from logging_setup import get_logger

logger = get_logger(__name__)

load_dotenv()


class NotificationPriority(enum.Enum):
    """Notification priority levels."""
    IGNORE = "ignore"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class NotificationStatus(enum.Enum):
    """Notification processing status."""
    NEW = "new"
    READ = "read"
    PROCESSED = "processed"
    ARCHIVED = "archived"


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
    priority = Column(Enum(NotificationPriority), default=NotificationPriority.MEDIUM)
    status = Column(Enum(NotificationStatus), default=NotificationStatus.NEW)
    is_read = Column(Boolean, default=False)
    source = Column(String, nullable=True)  # Источник события (сервис, модуль)
    service_name = Column(String, nullable=True)  # Имя сервиса
    event_data = Column(Text, nullable=True)  # JSON с детальными данными события
    group_id = Column(String, nullable=True)  # ID для группировки одинаковых алертов
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)  # Время, после которого уведомление считается устаревшим
    processed_at = Column(DateTime, nullable=True)  # Время обработки уведомления


class NotificationCreate(BaseModel):
    title: str
    message: str
    user_id: Optional[str] = None
    notification_type: Optional[str] = "info"
    priority: Optional[NotificationPriority] = NotificationPriority.MEDIUM
    source: Optional[str] = None
    service_name: Optional[str] = None
    event_data: Optional[Dict[str, Any]] = None
    group_id: Optional[str] = None
    expires_at: Optional[datetime] = None


class NotificationUpdate(BaseModel):
    is_read: Optional[bool] = None
    status: Optional[NotificationStatus] = None
    priority: Optional[NotificationPriority] = None
    processed_at: Optional[datetime] = None


class NotificationFilter(BaseModel):
    """Filter parameters for notifications."""
    user_id: Optional[str] = None
    notification_type: Optional[str] = None
    priority: Optional[NotificationPriority] = None
    status: Optional[NotificationStatus] = None
    source: Optional[str] = None
    service_name: Optional[str] = None
    group_id: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    search: Optional[str] = None  # Поиск по title и message


class NotificationResponse(BaseModel):
    id: int
    title: str
    message: str
    user_id: Optional[str]
    notification_type: str
    priority: NotificationPriority
    status: NotificationStatus
    is_read: bool
    source: Optional[str]
    service_name: Optional[str]
    event_data: Optional[Dict[str, Any]]
    group_id: Optional[str]
    created_at: datetime
    expires_at: Optional[datetime]
    processed_at: Optional[datetime]

    class Config:
        from_attributes = True


class NotificationGroup(BaseModel):
    """Represents a group of aggregated notifications."""
    group_id: str
    title: str
    message: str
    notification_type: str
    priority: NotificationPriority
    source: Optional[str]
    service_name: Optional[str]
    count: int
    first_created_at: datetime
    last_created_at: datetime
    notifications: List[NotificationResponse] = []


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
        # Auto-generate group_id if not provided based on title, type, source, service
        group_id = notification.group_id
        if not group_id:
            group_parts = [notification.title, notification.notification_type]
            if notification.source:
                group_parts.append(notification.source)
            if notification.service_name:
                group_parts.append(notification.service_name)
            group_id = "|".join(group_parts).lower().replace(" ", "_")
        
        db_notification = Notification(
            title=notification.title,
            message=notification.message,
            user_id=notification.user_id,
            notification_type=notification.notification_type,
            priority=notification.priority,
            source=notification.source,
            service_name=notification.service_name,
            event_data=json.dumps(notification.event_data) if notification.event_data else None,
            group_id=group_id,
            expires_at=notification.expires_at
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
    filters: Optional[NotificationFilter] = None,
    limit: int = 100,
    offset: int = 0,
) -> List[Notification]:
    """Получает список уведомлений с фильтрацией"""
    try:
        query = db.query(Notification)
        
        if filters:
            if filters.user_id:
                query = query.filter(Notification.user_id == filters.user_id)
            
            if filters.notification_type:
                query = query.filter(Notification.notification_type == filters.notification_type)
            
            if filters.priority:
                query = query.filter(Notification.priority == filters.priority)
            
            if filters.status:
                query = query.filter(Notification.status == filters.status)
            
            if filters.source:
                query = query.filter(Notification.source == filters.source)
            
            if filters.service_name:
                query = query.filter(Notification.service_name == filters.service_name)
            
            if filters.group_id:
                query = query.filter(Notification.group_id == filters.group_id)
            
            if filters.date_from:
                query = query.filter(Notification.created_at >= filters.date_from)
            
            if filters.date_to:
                query = query.filter(Notification.created_at <= filters.date_to)
            
            if filters.search:
                search_term = f"%{filters.search}%"
                query = query.filter(
                    (Notification.title.ilike(search_term)) |
                    (Notification.message.ilike(search_term))
                )
        
        query = query.order_by(Notification.created_at.desc())
        query = query.limit(limit).offset(offset)
        
        return query.all()
    except Exception as e:
        logger.error(f"Error getting notifications: {e}")
        raise


def get_notifications_filtered(
    db: Session,
    user_id: Optional[str] = None,
    limit: int = 100,
    unread_only: bool = False,
) -> List[Notification]:
    """Legacy function for backward compatibility."""
    filters = NotificationFilter(
        user_id=user_id,
        status=NotificationStatus.NEW if unread_only else None
    )
    return get_notifications(db, filters, limit)


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
            if notification_update.status is not None:
                db_notification.status = notification_update.status
                if notification_update.status == NotificationStatus.PROCESSED and not db_notification.processed_at:
                    db_notification.processed_at = datetime.utcnow()
            if notification_update.priority is not None:
                db_notification.priority = notification_update.priority
            if notification_update.processed_at is not None:
                db_notification.processed_at = notification_update.processed_at
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


def delete_all_notifications(db: Session, user_id: Optional[str] = None) -> int:
    """Удаляет все уведомления или уведомления конкретного пользователя"""
    try:
        query = db.query(Notification)

        if user_id:
            query = query.filter(Notification.user_id == user_id)

        deleted = query.delete(synchronize_session=False)
        db.commit()
        return deleted
    except Exception as e:
        logger.error(f"Error deleting notifications: {e}")
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


def send_notification(
    title: str, 
    message: str, 
    user_id: Optional[str] = None, 
    notification_type: str = "info",
    priority: Optional[NotificationPriority] = None,
    source: Optional[str] = None,
    service_name: Optional[str] = None,
    event_data: Optional[Dict[str, Any]] = None,
    group_id: Optional[str] = None
):
    """Вспомогательная функция для отправки уведомлений"""
    try:
        db = next(get_db())
        try:
            notification_data = NotificationCreate(
                title=title,
                message=message,
                user_id=user_id,
                notification_type=notification_type,
                priority=priority or NotificationPriority.MEDIUM,
                source=source,
                service_name=service_name,
                event_data=event_data,
                group_id=group_id
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
        logger.info(f"Cleaned up {len(expired_notifications)} expired notifications")
    except Exception as e:
        logger.error(f"Error cleaning up expired notifications: {e}")
        db.rollback()
        raise


def get_notification_groups(
    db: Session,
    filters: Optional[NotificationFilter] = None,
    limit: int = 50,
) -> List[NotificationGroup]:
    """Получает сгруппированные уведомления"""
    try:
        from sqlalchemy import func
        
        # Base query for grouping
        query = db.query(
            Notification.group_id,
            Notification.title,
            Notification.message,
            Notification.notification_type,
            Notification.priority,
            Notification.source,
            Notification.service_name,
            func.count(Notification.id).label('count'),
            func.min(Notification.created_at).label('first_created_at'),
            func.max(Notification.created_at).label('last_created_at')
        ).filter(
            Notification.group_id.isnot(None)
        ).group_by(
            Notification.group_id,
            Notification.title,
            Notification.message,
            Notification.notification_type,
            Notification.priority,
            Notification.source,
            Notification.service_name
        )
        
        # Apply filters
        if filters:
            if filters.user_id:
                query = query.filter(Notification.user_id == filters.user_id)
            if filters.notification_type:
                query = query.filter(Notification.notification_type == filters.notification_type)
            if filters.priority:
                query = query.filter(Notification.priority == filters.priority)
            if filters.source:
                query = query.filter(Notification.source == filters.source)
            if filters.service_name:
                query = query.filter(Notification.service_name == filters.service_name)
            if filters.date_from:
                query = query.filter(Notification.created_at >= filters.date_from)
            if filters.date_to:
                query = query.filter(Notification.created_at <= filters.date_to)
        
        query = query.order_by(func.max(Notification.created_at).desc())
        query = query.limit(limit)
        
        groups = []
        for row in query.all():
            group = NotificationGroup(
                group_id=row.group_id,
                title=row.title,
                message=row.message,
                notification_type=row.notification_type,
                priority=row.priority,
                source=row.source,
                service_name=row.service_name,
                count=row.count,
                first_created_at=row.first_created_at,
                last_created_at=row.last_created_at
            )
            groups.append(group)
        
        return groups
    except Exception as e:
        logger.error(f"Error getting notification groups: {e}")
        raise


def get_group_notifications(
    db: Session,
    group_id: str,
    limit: int = 100,
) -> List[Notification]:
    """Получает все уведомления в конкретной группе"""
    try:
        return db.query(Notification).filter(
            Notification.group_id == group_id
        ).order_by(
            Notification.created_at.desc()
        ).limit(limit).all()
    except Exception as e:
        logger.error(f"Error getting group notifications for {group_id}: {e}")
        raise


def export_notifications_to_csv(
    db: Session,
    filters: Optional[NotificationFilter] = None,
    limit: int = 1000,
) -> str:
    """Экспортирует уведомления в CSV формат"""
    try:
        notifications = get_notifications(db, filters, limit)
        
        output = StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow([
            'ID', 'Title', 'Message', 'User ID', 'Type', 'Priority', 'Status',
            'Is Read', 'Source', 'Service Name', 'Group ID', 'Created At',
            'Expires At', 'Processed At'
        ])
        
        # Data rows
        for notification in notifications:
            writer.writerow([
                notification.id,
                notification.title,
                notification.message,
                notification.user_id,
                notification.notification_type,
                notification.priority.value if notification.priority else None,
                notification.status.value if notification.status else None,
                notification.is_read,
                notification.source,
                notification.service_name,
                notification.group_id,
                notification.created_at.isoformat() if notification.created_at else None,
                notification.expires_at.isoformat() if notification.expires_at else None,
                notification.processed_at.isoformat() if notification.processed_at else None
            ])
        
        return output.getvalue()
    except Exception as e:
        logger.error(f"Error exporting notifications to CSV: {e}")
        raise


def export_notifications_to_json(
    db: Session,
    filters: Optional[NotificationFilter] = None,
    limit: int = 1000,
) -> str:
    """Экспортирует уведомления в JSON формат"""
    try:
        notifications = get_notifications(db, filters, limit)
        
        export_data = []
        for notification in notifications:
            item = {
                'id': notification.id,
                'title': notification.title,
                'message': notification.message,
                'user_id': notification.user_id,
                'notification_type': notification.notification_type,
                'priority': notification.priority.value if notification.priority else None,
                'status': notification.status.value if notification.status else None,
                'is_read': notification.is_read,
                'source': notification.source,
                'service_name': notification.service_name,
                'event_data': json.loads(notification.event_data) if notification.event_data else None,
                'group_id': notification.group_id,
                'created_at': notification.created_at.isoformat() if notification.created_at else None,
                'expires_at': notification.expires_at.isoformat() if notification.expires_at else None,
                'processed_at': notification.processed_at.isoformat() if notification.processed_at else None
            }
            export_data.append(item)
        
        return json.dumps(export_data, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error exporting notifications to JSON: {e}")
        raise


def update_notification_priority(
    db: Session,
    notification_id: int,
    priority: NotificationPriority,
) -> Optional[Notification]:
    """Обновляет приоритет уведомления"""
    try:
        return update_notification(
            db,
            notification_id,
            NotificationUpdate(priority=priority)
        )
    except Exception as e:
        logger.error(f"Error updating notification priority: {e}")
        raise


def bulk_update_notifications_status(
    db: Session,
    notification_ids: List[int],
    status: NotificationStatus,
) -> int:
    """Массово обновляет статус уведомлений"""
    try:
        query = db.query(Notification).filter(Notification.id.in_(notification_ids))
        
        update_data = {'status': status}
        if status == NotificationStatus.PROCESSED:
            update_data['processed_at'] = datetime.utcnow()
        
        updated_count = query.update(update_data, synchronize_session=False)
        db.commit()
        
        logger.info(f"Bulk updated {updated_count} notifications to status {status.value}")
        return updated_count
    except Exception as e:
        logger.error(f"Error bulk updating notifications status: {e}")
        db.rollback()
        raise


def get_notification_statistics(
    db: Session,
    filters: Optional[NotificationFilter] = None,
) -> Dict[str, Any]:
    """Получает статистику по уведомлениям"""
    try:
        from sqlalchemy import func
        
        query = db.query(Notification)
        
        # Apply filters
        if filters:
            if filters.user_id:
                query = query.filter(Notification.user_id == filters.user_id)
            if filters.date_from:
                query = query.filter(Notification.created_at >= filters.date_from)
            if filters.date_to:
                query = query.filter(Notification.created_at <= filters.date_to)
        
        total_count = query.count()
        
        # Count by priority
        priority_stats = db.query(
            Notification.priority,
            func.count(Notification.id).label('count')
        ).filter(
            Notification.priority.isnot(None)
        ).group_by(Notification.priority).all()
        
        # Count by status
        status_stats = db.query(
            Notification.status,
            func.count(Notification.id).label('count')
        ).filter(
            Notification.status.isnot(None)
        ).group_by(Notification.status).all()
        
        # Count by type
        type_stats = db.query(
            Notification.notification_type,
            func.count(Notification.id).label('count')
        ).group_by(Notification.notification_type).all()
        
        return {
            'total_count': total_count,
            'by_priority': {p.value: c for p, c in priority_stats},
            'by_status': {s.value: c for s, c in status_stats},
            'by_type': {t: c for t, c in type_stats}
        }
    except Exception as e:
        logger.error(f"Error getting notification statistics: {e}")
        raise
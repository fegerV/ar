from notifications import send_notification as original_send_notification
from typing import Optional

import structlog

logger = structlog.get_logger(__name__)

class NotificationHandler:
    """Класс для унифицированной обработки уведомлений"""
    
    @staticmethod
    def send_login_notification(username: str, success: bool, current_user: Optional[str] = None):
        """Отправляет уведомление о попытке входа"""
        if success:
            title = "Успешный вход"
            message = f"Пользователь {username} успешно вошел в систему"
            notification_type = "success"
        else:
            title = "Ошибка входа"
            message = f"Неудачная попытка входа для пользователя {username}"
            notification_type = "error"
        
        NotificationHandler._send_notification(
            title=title,
            message=message,
            user_id=current_user or username,
            notification_type=notification_type
        )
    
    @staticmethod
    def send_upload_notification(user: str, record_id: Optional[str] = None, success: bool = True, error_message: Optional[str] = None):
        """Отправляет уведомление о загрузке файлов"""
        if success and record_id:
            title = "Загрузка завершена"
            message = f"Файлы успешно загружены и NFT создан с ID: {record_id}"
            notification_type = "success"
        elif error_message:
            title = "Ошибка загрузки"
            message = f"Пользователь {user} попытался загрузить файлы с ошибкой: {error_message}"
            notification_type = "error"
        else:
            title = "Ошибка загрузки"
            message = f"Пользователь {user} попытался загрузить недействительные файлы"
            notification_type = "error"
        
        NotificationHandler._send_notification(
            title=title,
            message=message,
            user_id=user,
            notification_type=notification_type
        )
    
    @staticmethod
    def send_delete_notification(user: str, record_id: str, success: bool = True):
        """Отправляет уведомление об удалении записи"""
        if success:
            title = "Удаление завершено"
            message = f"Запись с ID: {record_id} успешно удалена"
            notification_type = "info"
        else:
            title = "Ошибка удаления"
            message = f"Пользователь {user} попытался удалить несуществующую запись с ID: {record_id}"
            notification_type = "error"
        
        NotificationHandler._send_notification(
            title=title,
            message=message,
            user_id=user,
            notification_type=notification_type
        )
    
    @staticmethod
    def send_file_access_notification(filename: str, user_id: Optional[str] = None, notification_type: str = "error", action: str = "получения"):
        """Отправляет уведомление о проблемах с доступом к файлам"""
        title = f"Ошибка {action} файла"
        message = f"Файл {filename} не найден в хранилище MinIO"
        
        NotificationHandler._send_notification(
            title=title,
            message=message,
            user_id=user_id,
            notification_type=notification_type
        )
    
    @staticmethod
    def send_ar_page_notification(record_id: str, user_id: Optional[str] = None):
        """Отправляет уведомление о запросе несуществующей AR-страницы"""
        title = "Ошибка AR-страницы"
        message = f"Запрошена AR-страница для несуществующей записи с ID: {record_id}"
        
        NotificationHandler._send_notification(
            title=title,
            message=message,
            user_id=user_id,
            notification_type="error"
        )
    
    @staticmethod
    def _send_notification(title: str, message: str, user_id: Optional[str] = None, notification_type: str = "info"):
        """Внутренний метод для отправки уведомлений"""
        try:
            original_send_notification(
                title=title,
                message=message,
                user_id=user_id,
                notification_type=notification_type
            )
            logger.info(f"Notification sent: {title}")
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
import os
from contextlib import contextmanager
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from logging_setup import get_logger
from minio import Minio
from minio.error import S3Error

logger = get_logger(__name__)

load_dotenv()


class MinIOStorage:
    """Унифицированный класс для работы с MinIO хранилищем"""

    def __init__(self):
        self._load_config()
        self._initialize_client()
        self._ensure_bucket_exists()

    def _load_config(self):
        """Загружает конфигурацию из переменных окружения"""
        original_endpoint = os.getenv("MINIO_ENDPOINT", "localhost:9000")

        # Убедимся, что MINIO_ENDPOINT не содержит http:// префикс
        if original_endpoint.startswith("http://") or original_endpoint.startswith("https://"):
            self.minio_endpoint = original_endpoint.split("://")[1]
        else:
            self.minio_endpoint = original_endpoint

        self.access_key = os.getenv("MINIO_ACCESS_KEY", "admin")
        self.secret_key = os.getenv("MINIO_SECRET_KEY", "password123")
        self.bucket_name = os.getenv("MINIO_BUCKET", "vertex-art-bucket")
        self.secure = os.getenv("MINIO_SECURE", "false").lower() == "true"

    def _initialize_client(self):
        """Инициализирует MinIO клиент"""
        self.client = Minio(self.minio_endpoint, access_key=self.access_key, secret_key=self.secret_key, secure=self.secure)

    def _ensure_bucket_exists(self):
        """Проверяет существование бакета и создает его при необходимости"""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                logger.info(f"Бакет {self.bucket_name} создан")
            else:
                logger.info(f"Бакет {self.bucket_name} уже существует")
        except S3Error as e:
            logger.error(f"Ошибка при работе с бакетом: {e}")
            raise

    def _handle_s3_error(self, operation: str, error: S3Error, object_name: str = None) -> None:
        """Унифицированная обработка ошибок S3"""
        error_msg = f"Ошибка при {operation}"
        if object_name:
            error_msg += f" файла {object_name}"
        error_msg += f": {error}"
        logger.error(error_msg)

    def upload_file(
        self, file_content: bytes, object_name: str, content_type: str = "application/octet-stream"
    ) -> Optional[str]:
        """Загружает содержимое файла в MinIO"""
        try:
            result = self.client.put_object(
                self.bucket_name, object_name, data=bytes(file_content), length=len(file_content), content_type=content_type
            )
            logger.info(f"Файл {object_name} загружен в {self.bucket_name}")
            return f"http://{self.minio_endpoint}/{self.bucket_name}/{result.object_name}"
        except S3Error as e:
            self._handle_s3_error("загрузке", e, object_name)
            return None

    def download_file(self, object_name: str) -> Optional[bytes]:
        """Скачивает содержимое файла из MinIO"""
        try:
            response = self.client.get_object(self.bucket_name, object_name)
            try:
                content = response.read()
                logger.info(f"Файл {object_name} успешно получен, размер: {len(content)} байт")
                return content
            finally:
                response.close()
                response.release_conn()
        except S3Error as e:
            self._handle_s3_error("получении", e, object_name)
            return None
        except Exception as e:
            logger.error(f"Общая ошибка при получении файла {object_name}: {e}")
            return None

    def delete_file(self, object_name: str) -> bool:
        """Удаляет файл из MinIO"""
        try:
            self.client.remove_object(self.bucket_name, object_name)
            logger.info(f"Файл {object_name} удален")
            return True
        except S3Error as e:
            self._handle_s3_error("удалении", e, object_name)
            return False

    def file_exists(self, object_name: str) -> bool:
        """Проверяет существование файла в MinIO"""
        try:
            self.client.stat_object(self.bucket_name, object_name)
            return True
        except S3Error:
            return False

    def get_file_url(self, object_name: str) -> Optional[str]:
        """Получает URL для файла в MinIO"""
        if self.file_exists(object_name):
            return f"http://{self.minio_endpoint}/{self.bucket_name}/{object_name}"
        return None

    def get_nft_marker_urls(self, record_id: str) -> Dict[str, Optional[str]]:
        """Получает URL для NFT-маркеров из MinIO"""
        try:
            marker_extensions = ["iset", "fset", "fset3"]
            marker_urls = {}

            for ext in marker_extensions:
                file_name = f"nft-markers/{record_id}.{ext}"
                marker_urls[ext] = self.get_file_url(file_name)

                if marker_urls[ext] is None:
                    logger.warning(f"NFT marker file {file_name} not found in MinIO storage")

            return marker_urls
        except Exception as e:
            logger.error(f"Ошибка при получении URL NFT-маркеров: {e}")
            return {"iset": None, "fset": None, "fset3": None}

    def upload_file_from_path(self, file_path: str, object_name: str, content_type: str = None) -> Optional[str]:
        """Загружает файл по пути в MinIO"""
        try:
            if content_type is None:
                import mimetypes

                content_type, _ = mimetypes.guess_type(file_path)

            result = self.client.fput_object(
                self.bucket_name, object_name, file_path, content_type=content_type or "application/octet-stream"
            )
            logger.info(f"Файл {file_path} загружен как {object_name}")
            return f"http://{self.minio_endpoint}/{self.bucket_name}/{result.object_name}"
        except S3Error as e:
            self._handle_s3_error("загрузке", e, object_name)
            return None


# Глобальный экземпляр для использования в приложении
import os


def _get_storage():
    """Get or create storage instance"""
    global storage
    if "storage" not in globals() or storage is None:
        storage = MinIOStorage()
    return storage


# Initialize storage if not in test mode
if os.getenv("RUNNING_TESTS") != "1":
    storage = MinIOStorage()
else:
    storage = None


def upload_file(file_content: bytes, object_name: str, content_type: str = "application/octet-stream") -> Optional[str]:
    """Загружает содержимое файла в MinIO (обратная совместимость)"""
    s = storage if storage is not None else _get_storage()
    return s.upload_file(file_content, object_name, content_type)


def get_file(object_name: str) -> Optional[bytes]:
    """Получает содержимое файла из MinIO (обратная совместимость)"""
    s = storage if storage is not None else _get_storage()
    return s.download_file(object_name)


def delete_file(object_name: str) -> bool:
    """Удаляет файл из MinIO (обратная совместимость)"""
    s = storage if storage is not None else _get_storage()
    return s.delete_file(object_name)


def get_nft_marker_urls(record_id: str) -> Dict[str, Optional[str]]:
    """Получает URL для NFT-маркеров из MinIO (обратная совместимость)"""
    s = storage if storage is not None else _get_storage()
    return s.get_nft_marker_urls(record_id)

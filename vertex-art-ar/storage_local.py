import os
import uuid
from typing import Optional
from dotenv import load_dotenv
import logging

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LocalStorage:
    def __init__(self):
        self.bucket_name = os.getenv("MINIO_BUCKET", "vertex-art-bucket")
        self.storage_path = os.path.join(".", self.bucket_name)
        
        # Создаем директорию для хранения файлов, если она не существует
        os.makedirs(self.storage_path, exist_ok=True)
        logger.info(f"LocalStorage initialized with path: {self.storage_path}")

    def upload_file(self, file_content: bytes, file_name: str, content_type: str = "application/octet-stream") -> str:
        """Загружает файл в локальное хранилище"""
        try:
            file_path = os.path.join(self.storage_path, file_name)
            
            # Записываем файл
            with open(file_path, 'wb') as f:
                f.write(file_content)
            
            logger.info(f"File {file_name} uploaded successfully to {file_path}")
            return f"file://{file_path}"
        except Exception as e:
            logger.error(f"Error uploading file {file_name}: {str(e)}")
            raise e

    def delete_file(self, file_name: str) -> bool:
        """Удаляет файл из локального хранилища"""
        try:
            file_path = os.path.join(self.storage_path, file_name)
            
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"File {file_name} deleted successfully")
                return True
            else:
                logger.warning(f"File {file_name} not found for deletion")
                return False
        except Exception as e:
            logger.error(f"Error deleting file {file_name}: {str(e)}")
            return False

    def get_file(self, file_name: str) -> Optional[bytes]:
        """Получает содержимое файла из локального хранилища"""
        try:
            file_path = os.path.join(self.storage_path, file_name)
            
            if os.path.exists(file_path):
                with open(file_path, 'rb') as f:
                    content = f.read()
                logger.info(f"File {file_name} retrieved successfully")
                return content
            else:
                logger.warning(f"File {file_name} not found")
                return None
        except Exception as e:
            logger.error(f"Error retrieving file {file_name}: {str(e)}")
            return None

    def file_exists(self, file_name: str) -> bool:
        """Проверяет существование файла в локальном хранилище"""
        file_path = os.path.join(self.storage_path, file_name)
        return os.path.exists(file_path)

# Создаем глобальный экземпляр локального хранилища
local_storage = LocalStorage()

# Функции для совместимости с оригинальным storage.py
def upload_file(file_content: bytes, file_name: str, content_type: str = "application/octet-stream") -> str:
    return local_storage.upload_file(file_content, file_name, content_type)

def delete_file(file_name: str) -> bool:
    return local_storage.delete_file(file_name)

def get_file(file_name: str) -> Optional[bytes]:
    return local_storage.get_file(file_name)

def file_exists(file_name: str) -> bool:
    return local_storage.file_exists(file_name)
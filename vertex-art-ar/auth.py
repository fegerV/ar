from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from passlib.context import CryptContext
import os
from datetime import datetime, timedelta
from jose import JWTError, jwt
from typing import Optional

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Basic HTTP authentication scheme
security = HTTPBasic()

# Get admin credentials from environment variables
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "secret")  # Вместо хеша пароля, будем использовать простой пароль из .env
ADMIN_PASSWORD_HASH = os.getenv("ADMIN_PASSWORD_HASH")
SECRET_KEY = os.getenv("SECRET_KEY", "your-super-secret-key-here")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)

def authenticate_user(username: str, password: str) -> bool:
    """
    Проверяет, соответствует ли имя пользователя и пароль учетным данным администратора
    """
    if username != ADMIN_USERNAME:
        return False

    if ADMIN_PASSWORD_HASH:
        return verify_password(password, ADMIN_PASSWORD_HASH)

    if ADMIN_PASSWORD and ADMIN_PASSWORD.startswith('$2b$'):
        return verify_password(password, ADMIN_PASSWORD)

    return password == (ADMIN_PASSWORD or "")

def authenticate_admin(username: str, password: str) -> bool:
    """Псевдоним для аутентификации администратора"""
    return authenticate_user(username, password)

def create_access_token(data: dict) -> str:
    """
    Создает JWT токен с заданными данными
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> Optional[str]:
    """
    Проверяет JWT токен и возвращает имя пользователя
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
        return username
    except JWTError:
        return None

async def get_current_user(request: Request) -> str:
    """
    Получает текущего пользователя из токена
    """
    token = request.cookies.get("access_token")
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    username = verify_token(token)
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return username

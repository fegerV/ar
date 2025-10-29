from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import uuid
from sqlalchemy import create_engine, Column, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./vertex_art.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class NFTRecord(Base):
    __tablename__ = "nft_records"

    id = Column(String, primary_key=True, index=True)
    image_url = Column(String, nullable=False)
    video_url = Column(String, nullable=False)
    nft_url = Column(String, nullable=False)
    qr_code = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    image_preview_url = Column(String, nullable=True)
    video_preview_url = Column(String, nullable=True)


class AREntryBase(BaseModel):
    """Base model for AR entry."""
    image_key: str
    video_key: str
    nft_prefix: str


class AREntryCreate(AREntryBase):
    """Model for creating AR entry."""
    pass  # This can be extended with additional validation or fields if needed


class AREntryUpdate(BaseModel):
    """Model for updating AR entry."""
    image_key: Optional[str] = None
    video_key: Optional[str] = None
    nft_prefix: Optional[str] = None
    status: Optional[str] = None


class AREntryInDBBase(AREntryBase):
    """Base model for AR entry in database."""
    id: int
    uuid: str
    created_at: datetime
    status: str

    class Config:
        orm_mode = True


class AREntry(AREntryInDBBase):
    """Model for AR entry."""
    pass  # This can be extended with additional methods or fields if needed


class AREntryInDB(AREntryInDBBase):
    """Model for AR entry in database with all fields."""
    image_preview_url: Optional[str] = None
    video_preview_url: Optional[str] = None
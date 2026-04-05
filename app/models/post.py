import enum
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.models.base import Base


class PostStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    PUBLISHED = "published"
    FAILED = "failed"


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    ig_account_id = Column(Integer, ForeignKey("instagram_accounts.id"), nullable=False)
    media_file_id = Column(Integer, ForeignKey("media_files.id"), nullable=False)
    caption = Column(Text, nullable=True)
    status = Column(Enum(PostStatus), default=PostStatus.PENDING, nullable=False)
    ig_container_id = Column(String, nullable=True)
    ig_media_id = Column(String, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    published_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="posts")
    instagram_account = relationship("InstagramAccount", back_populates="posts")
    media_file = relationship("MediaFile", back_populates="posts")

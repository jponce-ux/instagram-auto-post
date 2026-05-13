from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.models.base import Base


class InstagramAccount(Base):
    __tablename__ = "instagram_accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    instagram_account_id = Column(String, unique=True, nullable=False)
    username = Column(String, nullable=True)
    access_token = Column(String, nullable=False)
    token_expires_at = Column(DateTime(timezone=True), nullable=False)
    is_active = Column(Boolean, server_default="true", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="instagram_accounts")
    posts = relationship("Post", back_populates="instagram_account")

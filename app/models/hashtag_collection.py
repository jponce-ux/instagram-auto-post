from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.models.base import Base


class HashtagCollection(Base):
    """Collection of hashtags that can be reused across posts."""
    
    __tablename__ = "hashtag_collections"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)
    hashtags = Column(Text, nullable=False)  # Comma-separated hashtags
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User", back_populates="hashtag_collections")

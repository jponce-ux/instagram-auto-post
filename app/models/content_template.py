from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.models.base import Base


class ContentTemplate(Base):
    """Reusable caption template with {{placeholder}} syntax."""
    
    __tablename__ = "content_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)
    caption_template = Column(Text, nullable=False)  # With {{placeholder}} syntax
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User", back_populates="content_templates")

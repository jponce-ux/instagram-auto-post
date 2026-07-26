from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Time
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.models.base import Base


class RecurringSchedule(Base):
    """Recurring post schedule that auto-creates scheduled posts."""
    
    __tablename__ = "recurring_schedules"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    ig_account_id = Column(Integer, ForeignKey("instagram_accounts.id"), nullable=False)
    frequency = Column(String(20), nullable=False)  # "daily", "weekly"
    time_of_day = Column(Time, nullable=False)
    day_of_week = Column(Integer, nullable=True)  # 0-6 for weekly (0=Monday)
    template_id = Column(Integer, ForeignKey("content_templates.id"), nullable=True)
    hashtag_collection_id = Column(Integer, ForeignKey("hashtag_collections.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    last_run_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User", back_populates="recurring_schedules")
    instagram_account = relationship("InstagramAccount", back_populates="recurring_schedules")
    template = relationship("ContentTemplate")
    hashtag_collection = relationship("HashtagCollection")

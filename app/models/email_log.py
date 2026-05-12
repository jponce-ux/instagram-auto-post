"""Email log model for tracking email send history.

Stores a record of every email sent through the system, including
status tracking (queued → sent/failed), timestamps, and metadata.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.base import Base


class EmailStatus:
    """Email status constants."""
    QUEUED = "queued"
    SENT = "sent"
    DELIVERED = "delivered"
    BOUNCED = "bounced"
    FAILED = "failed"


class EmailLog(Base):
    __tablename__ = "email_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    email_type = Column(String(50), nullable=False, index=True)
    to_email = Column(String(255), nullable=False)
    from_email = Column(String(255), nullable=False)
    status = Column(String(20), nullable=False, default=EmailStatus.QUEUED, index=True)
    message_id = Column(String(255), nullable=True)
    template_name = Column(String(100), nullable=True)
    metadata_ = Column("metadata", JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    queued_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    sent_at = Column(DateTime(timezone=True), nullable=True)
    failed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", backref="email_logs")

    @classmethod
    def get_by_user(cls, db_session, user_id: int, limit: int = 50):
        """Get email logs for a specific user, ordered by queued_at descending."""
        from sqlalchemy import select

        stmt = (
            select(cls)
            .where(cls.user_id == user_id)
            .order_by(cls.queued_at.desc())
            .limit(limit)
        )
        return db_session.execute(stmt).scalars().all()

    @classmethod
    def get_by_status(cls, db_session, status: str, limit: int = 50):
        """Get email logs filtered by status."""
        from sqlalchemy import select

        stmt = (
            select(cls)
            .where(cls.status == status)
            .order_by(cls.queued_at.desc())
            .limit(limit)
        )
        return db_session.execute(stmt).scalars().all()

    @classmethod
    def check_idempotency(cls, db_session, user_id: int, email_type: str, hours: int = 24):
        """
        Check if a successful email of the same type was sent recently.

        Returns True if a successful email exists within the time window,
        False otherwise.
        """
        from datetime import datetime, timedelta, timezone
        from sqlalchemy import select

        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        stmt = (
            select(cls)
            .where(
                cls.user_id == user_id,
                cls.email_type == email_type,
                cls.status == EmailStatus.SENT,
                cls.sent_at >= cutoff,
            )
        )
        result = db_session.execute(stmt).scalar_one_or_none()
        return result is not None

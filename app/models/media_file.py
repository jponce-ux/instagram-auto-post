from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.models.base import Base


class MediaFile(Base):
    """
    MediaFile model for tracking file ownership in MinIO storage.

    Each uploaded file is scoped to a specific user and tracked in the database
    for authorization purposes.
    """

    __tablename__ = "media_files"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, nullable=False)  # {user_id}/{uuid}.{ext}
    original_filename = Column(String, nullable=False)
    content_type = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

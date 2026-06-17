from sqlalchemy import Column, String, Boolean, Integer, DateTime, ARRAY, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from backend.database import Base
import uuid

class UserProfile(Base):
    __tablename__ = "user_profiles"

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id             = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    role_title          = Column(String)
    skills_summary      = Column(String)
    experience_years    = Column(Integer)
    inclusion_keywords  = Column(ARRAY(String), nullable=False, default=list)
    exclusion_keywords  = Column(ARRAY(String), nullable=False, default=list)
    salary_min          = Column(Integer)
    salary_max          = Column(Integer)
    work_type           = Column(String, nullable=False, default="remote")
    preferred_regions   = Column(ARRAY(String), nullable=False, default=list)
    alerts_paused       = Column(Boolean, nullable=False, default=False)
    onboarding_complete = Column(Boolean, nullable=False, default=False)
    updated_at          = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

class NotificationSettings(Base):
    __tablename__ = "notification_settings"

    id                 = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id            = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    channels           = Column(ARRAY(String), nullable=False, default=lambda: ["email"])
    frequency          = Column(String, nullable=False, default="immediate")
    telegram_chat_id   = Column(String)
    telegram_connected = Column(Boolean, nullable=False, default=False)
    telegram_token     = Column(String)
    telegram_token_exp = Column(DateTime(timezone=True))

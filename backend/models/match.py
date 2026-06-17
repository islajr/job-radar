from sqlalchemy import Column, String, DateTime, Float, ForeignKey, Integer, func, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from backend.database import Base
import uuid

class UserMatch(Base):
    __tablename__ = "user_matches"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id      = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    listing_id   = Column(UUID(as_uuid=True), ForeignKey("listings.id", ondelete="CASCADE"), nullable=False)
    match_score  = Column(Float)
    match_reason = Column(String)
    notified_at  = Column(DateTime(timezone=True))
    created_at   = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "listing_id", name="uq_user_listing_match"),
        Index("idx_matches_user_id", user_id),
        Index("idx_matches_unnotified", user_id, postgresql_where=(notified_at == None)),
    )

class ScraperRun(Base):
    __tablename__ = "scraper_runs"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    board          = Column(String, nullable=False)
    started_at     = Column(DateTime(timezone=True), nullable=False)
    completed_at   = Column(DateTime(timezone=True))
    listings_found = Column(Integer, nullable=False, default=0)
    new_listings   = Column(Integer, nullable=False, default=0)
    errors         = Column(String)
    status         = Column(String, nullable=False, default="running")

    __table_args__ = (
        Index("idx_scraper_runs_board", board, started_at.desc()),
    )

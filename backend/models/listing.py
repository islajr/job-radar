from sqlalchemy import Column, String, DateTime, func, Index
from sqlalchemy.dialects.postgresql import UUID
from backend.database import Base
import uuid

class Listing(Base):
    __tablename__ = "listings"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    board           = Column(String, nullable=False)
    title           = Column(String, nullable=False)
    company         = Column(String)
    location        = Column(String)
    description     = Column(String)
    url             = Column(String, nullable=False)
    salary_text     = Column(String)
    posted_at       = Column(DateTime(timezone=True))
    fingerprint     = Column(String, unique=True, nullable=False)
    fetched_at      = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_listings_fetched_at", fetched_at.desc()),
    )

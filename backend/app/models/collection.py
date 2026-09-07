from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from app.models.base import Base


class Collection(Base):
    __tablename__ = "collections"

    id = Column(Integer, primary_key=True, autoincrement=True)
    platform_id = Column(Integer, ForeignKey("platforms.id"), nullable=False, index=True)
    started_at = Column(DateTime, nullable=False)
    ended_at = Column(DateTime, nullable=True)
    status = Column(String(20), nullable=False)
    records_collected = Column(Integer, default=0, nullable=True)

    # Relationships
    platform = relationship("Platform", back_populates="collections")

    def __repr__(self) -> str:
        return f"<Collection(id={self.id}, platform_id={self.platform_id}, status='{self.status}')>"

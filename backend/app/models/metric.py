from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer
from sqlalchemy.orm import relationship
from app.models.base import Base


class PostMetric(Base):
    __tablename__ = "post_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False, index=True)
    collected_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    likes = Column(Integer, default=0, nullable=True)
    comments = Column(Integer, default=0, nullable=True)
    shares = Column(Integer, default=0, nullable=True)
    views = Column(Integer, default=0, nullable=True)

    # Relationships
    post = relationship("Post", back_populates="metrics")

    def __repr__(self) -> str:
        return f"<PostMetric(id={self.id}, post_id={self.post_id}, likes={self.likes})>"

from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship
from app.models.base import Base


class Sentiment(Base):
    __tablename__ = "sentiments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False, index=True)
    label = Column(String(20), nullable=False)
    score = Column(Numeric(5, 4), nullable=True)
    model = Column(String(100), nullable=True)
    analyzed_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    post = relationship("Post", back_populates="sentiments")

    def __repr__(self) -> str:
        return f"<Sentiment(id={self.id}, post_id={self.post_id}, label='{self.label}', score={self.score})>"

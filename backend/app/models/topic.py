from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from app.models.base import Base


class PostTopic(Base):
    __tablename__ = "post_topics"

    post_id = Column(Integer, ForeignKey("posts.id"), primary_key=True)
    topic_id = Column(Integer, ForeignKey("topics.id"), primary_key=True)

    def __repr__(self) -> str:
        return f"<PostTopic(post_id={self.post_id}, topic_id={self.topic_id})>"


class Topic(Base):
    __tablename__ = "topics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    posts = relationship("Post", secondary="post_topics", back_populates="topics")

    def __repr__(self) -> str:
        return f"<Topic(id={self.id}, name='{self.name}')>"

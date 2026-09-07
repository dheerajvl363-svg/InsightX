from datetime import datetime
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text as sa_text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.models.base import Base


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    platform_id = Column(Integer, ForeignKey("platforms.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    external_post_id = Column(String(255), nullable=False)
    text = Column(Text, nullable=True)
    posted_at = Column(DateTime, nullable=False, index=True)
    collected_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    # Phase 2 extensions
    url = Column(String(512), nullable=True)
    language = Column(String(10), nullable=True, index=True)
    metadata_ = Column("metadata", JSONB, nullable=False, server_default=sa_text("'{}'::jsonb"), default=dict)
    raw_payload = Column("raw_payload", JSONB, nullable=False, server_default=sa_text("'{}'::jsonb"), default=dict)

    __table_args__ = (
        UniqueConstraint("platform_id", "external_post_id", name="posts_platform_id_external_post_id_key"),
    )

    # Convenience property to access metadata without conflicting with Base.metadata
    @property
    def post_metadata(self) -> dict:
        return self.metadata_ or {}

    @post_metadata.setter
    def post_metadata(self, val: dict) -> None:
        self.metadata_ = val

    # Relationships
    platform = relationship("Platform", back_populates="posts")
    user = relationship("User", back_populates="posts")
    metrics = relationship("PostMetric", back_populates="post", cascade="all, delete-orphan")
    sentiments = relationship("Sentiment", back_populates="post", cascade="all, delete-orphan")
    topics = relationship("Topic", secondary="post_topics", back_populates="posts")

    def __repr__(self) -> str:
        return f"<Post(id={self.id}, platform_id={self.platform_id}, external_post_id='{self.external_post_id}')>"

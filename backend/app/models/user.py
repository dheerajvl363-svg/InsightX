from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship
from app.models.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    platform_id = Column(Integer, ForeignKey("platforms.id"), nullable=False)
    username = Column(String(100), nullable=False)
    display_name = Column(String(150), nullable=True)
    followers_count = Column(Integer, default=0, nullable=True)
    following_count = Column(Integer, default=0, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=True)

    __table_args__ = (
        UniqueConstraint("platform_id", "username", name="users_platform_id_username_key"),
    )

    # Relationships
    platform = relationship("Platform", back_populates="users")
    posts = relationship("Post", back_populates="user")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, platform_id={self.platform_id}, username='{self.username}')>"

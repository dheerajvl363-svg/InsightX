from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.models.base import Base


class Platform(Base):
    __tablename__ = "platforms"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False, unique=True, index=True)

    # Relationships
    users = relationship("User", back_populates="platform", cascade="all, delete-orphan")
    posts = relationship("Post", back_populates="platform", cascade="all, delete-orphan")
    collections = relationship("Collection", back_populates="platform", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Platform(id={self.id}, name='{self.name}')>"

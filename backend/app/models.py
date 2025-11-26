from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=True)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_pro = Column(Boolean, default=False)  # Free vs Pro user
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship: এক ইউজারের অনেক API Key থাকতে পারে
    api_keys = relationship("ApiKey", back_populates="owner")

class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    exchange = Column(String)  # e.g., Binance, KuCoin
    api_key = Column(String)   # Public Key
    secret_key = Column(String) # Encrypted Secret Key
    is_enabled = Column(Boolean, default=True)
    user_id = Column(Integer, ForeignKey("users.id"))

    owner = relationship("User", back_populates="api_keys")
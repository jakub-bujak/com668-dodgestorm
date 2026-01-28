from sqlalchemy import Column, Integer, String, DateTime, func
from .sql_db import Base

class User(Base):
    __tablename__ = "Users"   # matches dbo.Users

    UserId = Column(Integer, primary_key=True, index=True)
    Username = Column(String(64), unique=True, index=True, nullable=False)
    PasswordHash = Column(String(255), nullable=False)
    CreatedAt = Column(DateTime, server_default=func.now(), nullable=False)

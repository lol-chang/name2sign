from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    kakao_id = Column(String, unique=True, index=True)
    email = Column(String)
    nickname = Column(String)
    profile_image = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow) 
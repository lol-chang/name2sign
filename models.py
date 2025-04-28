from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.sql import func
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    kakao_id = Column(String, unique=True, index=True)
    email = Column(String, index=True)
    nickname = Column(String)
    profile_image = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_active = Column(Boolean, default=True)

    def to_dict(self):
        """사용자 정보를 딕셔너리로 변환"""
        return {
            "id": self.id,
            "kakao_id": self.kakao_id,
            "email": self.email,
            "nickname": self.nickname,
            "profile_image": self.profile_image,
            "is_active": self.is_active
        } 
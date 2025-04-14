from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class UserBase(BaseModel):
    email: Optional[str] = None
    name: Optional[str] = None

class UserCreate(UserBase):
    kakao_id: str

class UserResponse(UserBase):
    id: int
    kakao_id: str
    created_at: datetime

    class Config:
        from_attributes = True

class UserInDB(UserResponse):
    pass 
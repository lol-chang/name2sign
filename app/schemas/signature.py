from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class SignatureBase(BaseModel):
    font_style: str
    color: str

class SignatureCreate(SignatureBase):
    user_id: int

class SignatureResponse(SignatureBase):
    id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True

class SignatureInDB(SignatureResponse):
    pass 
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..models.signature import Signature
from ..models.user import User
from ..schemas.signature import SignatureCreate, SignatureResponse

router = APIRouter()

@router.post("/signatures/", response_model=SignatureResponse)
async def create_signature(
    signature: SignatureCreate,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == signature.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    db_signature = Signature(
        user_id=signature.user_id,
        font_style=signature.font_style,
        color=signature.color
    )
    db.add(db_signature)
    db.commit()
    db.refresh(db_signature)
    
    return db_signature

@router.get("/signatures/{user_id}", response_model=List[SignatureResponse])
async def get_user_signatures(user_id: int, db: Session = Depends(get_db)):
    signatures = db.query(Signature).filter(Signature.user_id == user_id).all()
    return signatures 
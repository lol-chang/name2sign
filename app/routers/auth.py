from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..services.kakao import KakaoService
from ..models.user import User
from ..schemas.user import UserResponse

router = APIRouter()
kakao_service = KakaoService()

@router.get("/login")
async def login():
    return {"url": kakao_service.get_oauth_url()}

@router.get("/callback", response_model=UserResponse)
async def kakao_callback(code: str, db: Session = Depends(get_db)):
    try:
        # Get access token
        token_data = kakao_service.get_access_token(code)
        access_token = token_data.get("access_token")
        
        if not access_token:
            raise HTTPException(status_code=400, detail="Failed to get access token")
        
        # Get user info
        user_info = kakao_service.get_user_info(access_token)
        kakao_id = str(user_info.get("id"))
        email = user_info.get("kakao_account", {}).get("email")
        name = user_info.get("properties", {}).get("nickname")
        
        # Find or create user
        user = db.query(User).filter(User.kakao_id == kakao_id).first()
        if not user:
            user = User(
                kakao_id=kakao_id,
                email=email,
                name=name
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        
        return user
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) 
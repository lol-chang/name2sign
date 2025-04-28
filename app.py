# app.py
from fastapi import FastAPI, Request, Response, Depends, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv
from jose import jwt
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
import os
import requests

# 데이터베이스 및 모델 임포트
from database import engine, get_db, Base
from models import User

# .env 파일 로드
load_dotenv()

# 데이터베이스 테이블 생성
Base.metadata.create_all(bind=engine)

# 환경 변수 불러오기
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

KAKAO_CLIENT_ID = os.getenv("KAKAO_CLIENT_ID")
KAKAO_CLIENT_SECRET = os.getenv("KAKAO_CLIENT_SECRET")
KAKAO_REDIRECT_URI = os.getenv("KAKAO_REDIRECT_URI")

KAKAO_ADMIN_KEY = os.getenv("KAKAO_ADMIN_KEY")
KAKAO_PAY_CID = os.getenv("KAKAO_PAY_CID")
BASE_URL = os.getenv("BASE_URL")

app = FastAPI()

# 정적 파일 설정
app.mount("/static", StaticFiles(directory="static"), name="static")

# 템플릿 설정
templates = Jinja2Templates(directory="templates")

# JWT 토큰 생성
def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt

# JWT 토큰 검증
def verify_token(token: str):
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid Token")

# 쿠키에서 현재 사용자 가져오기
def get_current_user(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return verify_token(token)

# 카카오 로그인
@app.get("/login")
def login():
    kakao_auth_url = (
        f"https://kauth.kakao.com/oauth/authorize?"
        f"response_type=code&client_id={KAKAO_CLIENT_ID}&redirect_uri={KAKAO_REDIRECT_URI}"
        f"&prompt=login"  # 항상 로그인 화면을 보여주는 옵션 추가
    )
    return RedirectResponse(kakao_auth_url)

# 로그인 후 콜백
@app.get("/callback")
def callback(code: str, response: Response, db: Session = Depends(get_db)):
    print(f"받은 인증 코드: {code}")
    token_url = "https://kauth.kakao.com/oauth/token"
    token_data = {
        "grant_type": "authorization_code",
        "client_id": KAKAO_CLIENT_ID,
        "redirect_uri": KAKAO_REDIRECT_URI,
        "code": code,
        "client_secret": KAKAO_CLIENT_SECRET
    }
    token_res = requests.post(token_url, data=token_data)
    token_json = token_res.json()
    
    print(f"토큰 응답: {token_json}")
    
    access_token = token_json.get("access_token")
    if not access_token:
        raise HTTPException(status_code=400, detail="Failed to get Kakao token")

    # 사용자 정보 가져오기
    user_info = requests.get(
        "https://kapi.kakao.com/v2/user/me",
        headers={"Authorization": f"Bearer {access_token}"}
    ).json()

    print(f"사용자 정보: {user_info}")

    kakao_id = str(user_info.get("id"))
    
    # 카카오 계정 정보 가져오기
    kakao_account = user_info.get("kakao_account", {})
    profile = kakao_account.get("profile", {})
    
    # 데이터베이스에서 회원 정보 조회
    user = db.query(User).filter(User.kakao_id == kakao_id).first()
    
    # 회원 정보가 없으면 신규 등록
    if not user:
        user = User(
            kakao_id=kakao_id,
            email=kakao_account.get("email"),
            nickname=profile.get("nickname"),
            profile_image=profile.get("profile_image_url")
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"신규 사용자가 등록되었습니다: {user.to_dict()}")
    else:
        # 기존 회원 정보 업데이트
        user.email = kakao_account.get("email", user.email)
        user.nickname = profile.get("nickname", user.nickname)
        user.profile_image = profile.get("profile_image_url", user.profile_image)
        db.commit()
        db.refresh(user)
        print(f"사용자 정보가 업데이트되었습니다: {user.to_dict()}")
    
    # JWT 토큰에 저장할 추가 정보
    user_data = user.to_dict()

    # JWT 생성
    jwt_token = create_access_token(data=user_data)

    # 쿠키 저장
    response = RedirectResponse(url="/profile")
    response.set_cookie(key="access_token", value=jwt_token, httponly=True)
    return response

# 프로필 확인
@app.get("/profile")
def profile(request: Request, user=Depends(get_current_user)):
    return templates.TemplateResponse("profile.html", {
        "request": request,
        "nickname": user.get("nickname", "사용자"),
        "profile_image": user.get("profile_image", ""),
        "email": user.get("email", "이메일 정보 없음"),
        "kakao_id": user.get("kakao_id", "")
    })

# 로그아웃
@app.get("/logout")
def logout(response: Response):
    response = RedirectResponse(url="/")
    response.delete_cookie(key="access_token")
    return response

# 사용자 목록 조회
@app.get("/users")
def list_users(request: Request, db: Session = Depends(get_db)):
    users = db.query(User).all()
    return templates.TemplateResponse("users.html", {
        "request": request,
        "users": users
    })

# 카카오페이 결제 준비
@app.post("/pay")
def prepare_payment(user=Depends(get_current_user)):
    kakao_pay_url = "https://kapi.kakao.com/v1/payment/ready"
    headers = {
        "Authorization": f"KakaoAK {KAKAO_ADMIN_KEY}",
        "Content-type": "application/x-www-form-urlencoded;charset=utf-8"
    }
    params = {
        "cid": KAKAO_PAY_CID,
        "partner_order_id": "order_id_1234",
        "partner_user_id": str(user["kakao_id"]),
        "item_name": "Test Item",
        "quantity": 1,
        "total_amount": 1000,
        "vat_amount": 100,
        "tax_free_amount": 0,
        "approval_url": BASE_URL + "/pay/success",
        "cancel_url": BASE_URL + "/pay/cancel",
        "fail_url": BASE_URL + "/pay/fail"
    }
    res = requests.post(kakao_pay_url, headers=headers, data=params)
    payment_info = res.json()
    
    # 결제 페이지로 리다이렉트
    redirect_url = payment_info.get("next_redirect_pc_url")
    if not redirect_url:
        raise HTTPException(status_code=400, detail="결제 준비 실패")
    
    return RedirectResponse(url=redirect_url)

# 결제 콜백
@app.get("/pay/success")
def pay_success(request: Request):
    return templates.TemplateResponse("payment_result.html", {
        "request": request,
        "result_type": "성공",
        "message": "결제가 성공적으로 완료되었습니다."
    })

@app.get("/pay/cancel")
def pay_cancel(request: Request):
    return templates.TemplateResponse("payment_result.html", {
        "request": request,
        "result_type": "취소",
        "message": "결제가 취소되었습니다."
    })

@app.get("/pay/fail")
def pay_fail(request: Request):
    return templates.TemplateResponse("payment_result.html", {
        "request": request,
        "result_type": "실패",
        "message": "결제 처리 중 오류가 발생했습니다."
    })

# 회원 탈퇴
@app.post("/delete-account")
def delete_account(request: Request, response: Response, db: Session = Depends(get_db)):
    try:
        # 현재 로그인된 사용자 정보 가져오기
        user_data = get_current_user(request)
        kakao_id = user_data.get("kakao_id")
        
        if not kakao_id:
            raise HTTPException(status_code=400, detail="유효하지 않은 사용자 정보입니다.")
        
        # 사용자 정보 DB에서 찾기
        user = db.query(User).filter(User.kakao_id == kakao_id).first()
        
        if not user:
            raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
        
        # 연결 해제를 위해 카카오에 요청 (선택적)
        try:
            # 카카오 연결 해제 API 호출
            headers = {
                "Authorization": f"KakaoAK {KAKAO_ADMIN_KEY}"
            }
            data = {
                "target_id_type": "user_id",
                "target_id": kakao_id
            }
            requests.post(
                "https://kapi.kakao.com/v1/user/unlink",
                headers=headers,
                data=data
            )
        except Exception as e:
            print(f"카카오 계정 연결 해제 중 오류 발생: {str(e)}")
            # 카카오 연결 해제가 실패해도 계속 진행
        
        # DB에서 사용자 삭제
        db.delete(user)
        db.commit()
        
        # 로그아웃 처리 (쿠키 삭제)
        response = RedirectResponse(url="/", status_code=303)
        response.delete_cookie(key="access_token")
        
        return response
        
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"회원 탈퇴 처리 중 오류가 발생했습니다: {str(e)}")

# 메인 페이지
@app.get("/")
def main_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request}) 
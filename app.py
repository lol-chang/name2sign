# app.py
from fastapi import FastAPI, Request, Response, Depends, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv
from jose import jwt
from datetime import datetime, timedelta
import os
import requests

# .env 파일 로드
load_dotenv()

# 환경 변수 불러오기
DATABASE_URL = os.getenv("DATABASE_URL")
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
def callback(code: str, response: Response):
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

    kakao_id = user_info.get("id")
    
    # 카카오 계정 정보 가져오기
    kakao_account = user_info.get("kakao_account", {})
    profile = kakao_account.get("profile", {})
    
    # JWT 토큰에 저장할 추가 정보
    user_data = {
        "kakao_id": kakao_id,
        "nickname": profile.get("nickname", "사용자"),
        "profile_image": profile.get("profile_image_url", ""),
        "email": kakao_account.get("email", "")
    }

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

# 메인 페이지
@app.get("/")
def main_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request}) 
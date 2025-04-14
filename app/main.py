from fastapi import FastAPI, Request, Depends, HTTPException, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from .config import settings
from .auth import Auth
from .database import get_db, engine
from .models import Base, User
import requests
from datetime import datetime, timedelta
from itsdangerous import URLSafeSerializer

# 데이터베이스 테이블 생성
Base.metadata.create_all(bind=engine)

app = FastAPI()

# URL 안전한 시리얼라이저 생성
serializer = URLSafeSerializer(settings.secret_key)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 정적 파일 설정
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Jinja2 템플릿 설정
templates = Jinja2Templates(directory="app/static")

# Auth 인스턴스 생성
auth_handler = Auth()

# OAuth2 스키마 설정
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

@app.get("/")
async def read_root(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "KAKAO_CLIENT_ID": settings.kakao_client_id,
            "user_info": None,
            "jwt_token": None
        }
    )

@app.get("/callback")
async def kakao_callback_get(request: Request, response: Response, db: Session = Depends(get_db)):
    try:
        # 인가 코드 받기
        code = request.query_params.get("code")
        if not code:
            raise HTTPException(status_code=400, detail="Authorization code not provided")

        # 토큰 받기
        token_url = "https://kauth.kakao.com/oauth/token"
        data = {
            "grant_type": "authorization_code",
            "client_id": settings.kakao_client_id,
            "client_secret": settings.kakao_client_secret,
            "code": code,
            "redirect_uri": settings.kakao_redirect_uri
        }
        
        token_response = requests.post(token_url, data=data)
        if token_response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to get Kakao access token")
        
        token_json = token_response.json()
        kakao_access_token = token_json.get('access_token')
        
        # 사용자 정보 가져오기
        user_info_url = "https://kapi.kakao.com/v2/user/me"
        headers = {
            "Authorization": f"Bearer {kakao_access_token}",
            "Content-type": "application/x-www-form-urlencoded;charset=utf-8"
        }
        
        user_info_response = requests.get(user_info_url, headers=headers)
        if user_info_response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to get Kakao user info")
        
        user_info = user_info_response.json()
        
        # 필요한 사용자 정보 추출
        kakao_account = user_info.get("kakao_account", {})
        profile = kakao_account.get("profile", {})
        
        kakao_id = str(user_info.get("id"))
        email = kakao_account.get("email")
        nickname = profile.get("nickname")
        profile_image = profile.get("profile_image_url")

        # DB에서 사용자 찾기 또는 생성
        user = db.query(User).filter(User.kakao_id == kakao_id).first()
        
        if not user:
            user = User(
                kakao_id=kakao_id,
                email=email,
                nickname=nickname,
                profile_image=profile_image
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        else:
            user.email = email
            user.nickname = nickname
            user.profile_image = profile_image
            db.commit()

        # 사용자 정보로 JWT 토큰 생성
        user_data = {
            "id": user.id,
            "kakao_id": user.kakao_id,
            "nickname": user.nickname,
            "email": user.email,
            "profile_image": user.profile_image
        }
        
        jwt_token = auth_handler.encode_token(user_data)
        
        # JWT 토큰을 쿠키에 설정
        response = RedirectResponse(url="/")
        response.set_cookie(
            key="access_token",
            value=f"Bearer {jwt_token}",
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=7200  # 2시간
        )
        
        return response

    except Exception as e:
        print(f"Error in callback: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/user")
async def get_user(request: Request):
    try:
        # 쿠키에서 토큰 추출
        auth_cookie = request.cookies.get("access_token")
        if not auth_cookie or not auth_cookie.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
        
        token = auth_cookie.split(" ")[1]
        user_data = auth_handler.decode_token(token)
        return JSONResponse(content=user_data)
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))

@app.post("/api/signatures")
async def save_signature(request: Request):
    try:
        # 쿠키에서 토큰 추출
        auth_cookie = request.cookies.get("access_token")
        if not auth_cookie or not auth_cookie.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
        
        token = auth_cookie.split(" ")[1]
        user_data = auth_handler.decode_token(token)
        
        data = await request.json()
        # 여기에 서명 저장 로직 구현
        return {"message": "서명이 성공적으로 저장되었습니다."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/profile")
async def profile_page(request: Request):
    try:
        # 쿠키에서 토큰 추출
        auth_cookie = request.cookies.get("access_token")
        if not auth_cookie or not auth_cookie.startswith("Bearer "):
            return RedirectResponse(url="/")
        
        token = auth_cookie.split(" ")[1]
        user_data = auth_handler.decode_token(token)
        
        return templates.TemplateResponse(
            "profile.html",
            {
                "request": request,
                "user_info": user_data
            }
        )
    except Exception:
        return RedirectResponse(url="/")

@app.post("/logout")
async def logout(request: Request):
    try:
        # 쿠키에서 토큰 추출
        auth_cookie = request.cookies.get("access_token")
        if auth_cookie and auth_cookie.startswith("Bearer "):
            token = auth_cookie.split(" ")[1]
            user_data = auth_handler.decode_token(token)
            
            # 카카오 로그아웃
            try:
                user = user_data  # JWT 토큰에서 얻은 사용자 정보 사용
                kakao_logout_url = "https://kapi.kakao.com/v1/user/logout"
                headers = {
                    "Authorization": f"Bearer {user.get('access_token')}",
                }
                requests.post(kakao_logout_url, headers=headers)
            except:
                pass  # 카카오 로그아웃 실패해도 계속 진행
    except:
        pass  # 토큰 디코딩 실패해도 계속 진행

    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie("access_token")
    return response

@app.post("/api/payment/prepare")
async def prepare_payment(request: Request, response: Response):
    try:
        # 사용자 인증 확인
        auth_cookie = request.cookies.get("access_token")
        if not auth_cookie or not auth_cookie.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="로그인이 필요합니다")
        
        token = auth_cookie.split(" ")[1]
        user_data = auth_handler.decode_token(token)
        
        # 결제 데이터 받기
        data = await request.json()
        
        # 주문번호 생성
        order_id = f"ORDER_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        headers = {
            "Authorization": f"KakaoAK {settings.kakao_admin_key}",
            "Content-Type": "application/x-www-form-urlencoded;charset=utf-8"
        }
        
        payload = {
            "cid": settings.kakao_pay_cid,
            "partner_order_id": order_id,
            "partner_user_id": str(user_data["id"]),
            "item_name": data["item_name"],
            "quantity": data["quantity"],
            "total_amount": data["total_amount"],
            "tax_free_amount": "0",
            "approval_url": f"{settings.base_url}/payment/success",
            "cancel_url": f"{settings.base_url}/payment/cancel",
            "fail_url": f"{settings.base_url}/payment/fail"
        }
        
        response = requests.post(
            "https://kapi.kakao.com/v1/payment/ready",
            headers=headers,
            data=payload
        )
        
        if response.status_code != 200:
            raise HTTPException(status_code=400, detail="카카오페이 결제 준비 요청 실패")
        
        payment_info = response.json()
        
        # 결제 정보를 암호화하여 쿠키에 저장
        payment_data = {
            "tid": payment_info["tid"],
            "order_id": order_id
        }
        payment_token = serializer.dumps(payment_data)
        
        response = JSONResponse(content=payment_info)
        response.set_cookie(
            key="payment_info",
            value=payment_token,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=1800  # 30분
        )
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/payment/success")
async def payment_success(request: Request):
    try:
        pg_token = request.query_params.get("pg_token")
        payment_token = request.cookies.get("payment_info")
        
        if not payment_token:
            raise HTTPException(status_code=400, detail="결제 정보가 없습니다")
            
        # 결제 정보 복호화
        payment_data = serializer.loads(payment_token)
        tid = payment_data["tid"]
        order_id = payment_data["order_id"]
        
        if not all([pg_token, tid, order_id]):
            raise HTTPException(status_code=400, detail="필요한 결제 정보가 없습니다")
        
        # 사용자 정보 가져오기
        auth_cookie = request.cookies.get("access_token")
        if not auth_cookie or not auth_cookie.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="로그인이 필요합니다")
        
        token = auth_cookie.split(" ")[1]
        user_data = auth_handler.decode_token(token)
        
        headers = {
            "Authorization": f"KakaoAK {settings.kakao_admin_key}",
            "Content-Type": "application/x-www-form-urlencoded;charset=utf-8"
        }
        
        payload = {
            "cid": settings.kakao_pay_cid,
            "tid": tid,
            "partner_order_id": order_id,
            "partner_user_id": str(user_data["id"]),
            "pg_token": pg_token
        }
        
        response = requests.post(
            "https://kapi.kakao.com/v1/payment/approve",
            headers=headers,
            data=payload
        )
        
        if response.status_code != 200:
            raise HTTPException(status_code=400, detail="카카오페이 결제 승인 요청 실패")
        
        # 결제 정보 쿠키 삭제
        response = RedirectResponse(url="/?payment=success")
        response.delete_cookie("payment_info")
        
        return response
        
    except Exception as e:
        return RedirectResponse(url="/?payment=fail")

@app.get("/payment/cancel")
async def payment_cancel(response: Response):
    response = RedirectResponse(url="/?payment=cancel")
    response.delete_cookie("payment_info")
    return response

@app.get("/payment/fail")
async def payment_fail(response: Response):
    response = RedirectResponse(url="/?payment=fail")
    response.delete_cookie("payment_info")
    return response 
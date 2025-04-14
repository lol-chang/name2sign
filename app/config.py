from pydantic_settings import BaseSettings
import secrets
from typing import Optional

class Settings(BaseSettings):
    # 기존 설정
    database_url: str
    secret_key: str
    jwt_secret_key: str
    
    # 카카오 로그인 설정
    kakao_client_id: str
    kakao_client_secret: str
    kakao_redirect_uri: str
    
    # 카카오페이 설정
    kakao_admin_key: str
    kakao_pay_cid: str = "TC0ONETIME"
    base_url: str = "http://127.0.0.1:8080"
    
    class Config:
        env_file = ".env"

settings = Settings() 
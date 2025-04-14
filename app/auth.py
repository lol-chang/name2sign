from datetime import datetime, timedelta
from typing import Optional
import jwt
from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from .config import settings

security = HTTPBearer()

class Auth:
    def __init__(self):
        """
        JWT 인증을 위한 클래스 초기화
        """
        self.secret = settings.jwt_secret_key
        self.algorithm = "HS256"

    def encode_token(self, user_data):
        """
        사용자 정보를 기반으로 JWT 토큰 생성
        """
        try:
            payload = {
                'exp': datetime.utcnow() + timedelta(hours=2),
                'iat': datetime.utcnow(),
                'user': user_data
            }
            return jwt.encode(
                payload,
                self.secret,
                algorithm=self.algorithm
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    def decode_token(self, token):
        """
        JWT 토큰 디코딩
        """
        try:
            payload = jwt.decode(token, self.secret, algorithms=[self.algorithm])
            if datetime.fromtimestamp(payload['exp']) < datetime.utcnow():
                raise HTTPException(status_code=401, detail='Token has expired')
            return payload['user']
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail='Token has expired')
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail='Invalid token')

    def auth_wrapper(self, auth: HTTPAuthorizationCredentials = Security(security)) -> dict:
        return self.decode_token(auth.credentials) 
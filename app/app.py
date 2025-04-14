from flask import Flask
from .auth import auth_bp
from .payment import payment_bp
import os
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-here')

app.register_blueprint(auth_bp)
app.register_blueprint(payment_bp)

if __name__ == '__main__':
    app.run(port=8080, debug=True) 
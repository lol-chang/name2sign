import os
import requests
from flask import Blueprint, request, jsonify, current_app, session
from datetime import datetime

payment_bp = Blueprint('payment', __name__)

KAKAO_ADMIN_KEY = os.environ.get('KAKAO_ADMIN_KEY')  # 카카오페이 어드민 키
KAKAO_PAY_HOST = 'https://kapi.kakao.com'
KAKAO_PAY_CID = os.environ.get('KAKAO_PAY_CID', 'TC0ONETIME')
BASE_URL = os.environ.get('BASE_URL', 'http://localhost:8080')

@payment_bp.route('/api/payment/prepare', methods=['POST'])
def prepare_payment():
    try:
        data = request.get_json()
        
        # 주문번호 생성
        order_id = f"ORDER_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        user_id = session.get('user_id', 'GUEST')
        
        headers = {
            'Authorization': f'KakaoAK {KAKAO_ADMIN_KEY}',
            'Content-Type': 'application/x-www-form-urlencoded;charset=utf-8'
        }
        
        payload = {
            'cid': KAKAO_PAY_CID,
            'partner_order_id': order_id,
            'partner_user_id': user_id,
            'item_name': data['item_name'],
            'quantity': data['quantity'],
            'total_amount': data['total_amount'],
            'tax_free_amount': '0',
            'approval_url': f'{BASE_URL}/payment/success',
            'cancel_url': f'{BASE_URL}/payment/cancel',
            'fail_url': f'{BASE_URL}/payment/fail'
        }
        
        response = requests.post(f'{KAKAO_PAY_HOST}/v1/payment/ready', headers=headers, data=payload)
        
        if response.status_code != 200:
            raise Exception('카카오페이 결제 준비 요청 실패')
        
        # 결제 정보를 세션에 저장
        payment_info = response.json()
        session['tid'] = payment_info['tid']
        session['order_id'] = order_id
        session['user_id'] = user_id
            
        return jsonify(payment_info)
        
    except Exception as e:
        current_app.logger.error(f'결제 준비 중 오류 발생: {str(e)}')
        return jsonify({'error': str(e)}), 500

@payment_bp.route('/payment/success')
def payment_success():
    try:
        pg_token = request.args.get('pg_token')
        tid = session.get('tid')
        order_id = session.get('order_id')
        user_id = session.get('user_id')

        if not all([pg_token, tid, order_id, user_id]):
            raise Exception('필요한 결제 정보가 없습니다.')

        headers = {
            'Authorization': f'KakaoAK {KAKAO_ADMIN_KEY}',
            'Content-Type': 'application/x-www-form-urlencoded;charset=utf-8'
        }

        payload = {
            'cid': KAKAO_PAY_CID,
            'tid': tid,
            'partner_order_id': order_id,
            'partner_user_id': user_id,
            'pg_token': pg_token
        }

        response = requests.post(f'{KAKAO_PAY_HOST}/v1/payment/approve', headers=headers, data=payload)

        if response.status_code != 200:
            raise Exception('카카오페이 결제 승인 요청 실패')

        # 결제 성공 후 처리
        # 여기에 프리미엄 기능 활성화 로직 추가
        session['is_premium'] = True
        
        # 결제 정보 세션에서 삭제
        session.pop('tid', None)
        session.pop('order_id', None)

        return '''
            <script>
                alert('결제가 성공적으로 완료되었습니다.');
                window.location.href = '/';
            </script>
        '''

    except Exception as e:
        current_app.logger.error(f'결제 승인 중 오류 발생: {str(e)}')
        return '''
            <script>
                alert('결제 승인 중 오류가 발생했습니다.');
                window.location.href = '/';
            </script>
        '''

@payment_bp.route('/payment/cancel')
def payment_cancel():
    return '''
        <script>
            alert('결제가 취소되었습니다.');
            window.location.href = '/';
        </script>
    '''

@payment_bp.route('/payment/fail')
def payment_fail():
    return '''
        <script>
            alert('결제에 실패했습니다.');
            window.location.href = '/';
        </script>
    ''' 
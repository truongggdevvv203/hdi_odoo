import json
import logging
from datetime import datetime, timedelta
from functools import wraps

import jwt
from odoo import http
from odoo.http import request, Response
from werkzeug.security import check_password_hash

_logger = logging.getLogger(__name__)

# Lấy secret key từ config hoặc sử dụng default
JWT_SECRET_KEY = http.request.env['ir.config_parameter'].sudo().get_param(
    'hdi_api.jwt_secret_key',
    'your-secret-key-change-in-production'
) if hasattr(http, 'request') else 'your-secret-key-change-in-production'


def _make_json_response(data, status_code=200):
    """Helper để tạo JSON response"""
    return Response(
        json.dumps(data),
        status=status_code,
        mimetype='application/json'
    )


def _verify_token(f):
    """Decorator để kiểm tra JWT token"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = None
        
        # Lấy token từ Authorization header
        auth_header = request.httprequest.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]  # Loại bỏ "Bearer " prefix
        
        if not token:
            return _make_json_response({
                'status': 'error',
                'message': 'Token không được cung cấp'
            }, 401)
        
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=['HS256'])
            request.jwt_payload = payload
        except jwt.ExpiredSignatureError:
            return _make_json_response({
                'status': 'error',
                'message': 'Token đã hết hạn'
            }, 401)
        except jwt.InvalidTokenError:
            return _make_json_response({
                'status': 'error',
                'message': 'Token không hợp lệ'
            }, 401)
        
        return f(*args, **kwargs)
    
    return decorated_function


class MobileAppAuthAPI(http.Controller):
    
    @http.route('/api/v1/auth/login', type='json', auth='none', methods=['POST'], csrf=False)
    def login(self):
        """
        Endpoint đăng nhập - trả về JWT token
        
        Request body:
        {
            "login": "email@example.com",
            "password": "password"
        }
        
        Response:
        {
            "status": "success",
            "token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
            "user": {
                "id": 1,
                "name": "John Doe",
                "email": "john@example.com"
            }
        }
        """
        try:
            data = request.jsonrequest
            login = data.get('login')
            password = data.get('password')
            
            if not login or not password:
                return _make_json_response({
                    'status': 'error',
                    'message': 'Email/Username và password là bắt buộc'
                }, 400)
            
            # Tìm user
            User = request.env['res.users'].sudo()
            users = User.search([
                '|',
                ('login', '=', login),
                ('email', '=', login)
            ], limit=1)
            
            if not users:
                return _make_json_response({
                    'status': 'error',
                    'message': 'Tài khoản hoặc mật khẩu không chính xác'
                }, 401)
            
            user = users[0]
            
            # Kiểm tra mật khẩu
            try:
                request.env.user = user
                request.env['res.users'].check_credentials(password)
            except Exception as e:
                _logger.warning(f"Failed login attempt for user {login}: {str(e)}")
                return _make_json_response({
                    'status': 'error',
                    'message': 'Tài khoản hoặc mật khẩu không chính xác'
                }, 401)
            
            # Tạo JWT token
            token_payload = {
                'user_id': user.id,
                'login': user.login,
                'name': user.name,
                'email': user.email,
                'iat': datetime.utcnow(),
                'exp': datetime.utcnow() + timedelta(days=30)  # Token hợp lệ trong 30 ngày
            }
            
            token = jwt.encode(token_payload, JWT_SECRET_KEY, algorithm='HS256')
            
            return _make_json_response({
                'status': 'success',
                'message': 'Đăng nhập thành công',
                'token': token,
                'user': {
                    'id': user.id,
                    'name': user.name,
                    'email': user.email,
                    'login': user.login,
                }
            }, 200)
        
        except Exception as e:
            _logger.error(f"Login error: {str(e)}")
            return _make_json_response({
                'status': 'error',
                'message': 'Lỗi server khi xử lý yêu cầu'
            }, 500)
    
    @http.route('/api/v1/auth/refresh-token', type='json', auth='none', methods=['POST'], csrf=False)
    @_verify_token
    def refresh_token(self):
        """
        Endpoint làm mới token
        
        Headers:
        Authorization: Bearer <token>
        
        Response:
        {
            "status": "success",
            "token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
        }
        """
        try:
            user_id = request.jwt_payload.get('user_id')
            user = request.env['res.users'].sudo().browse(user_id)
            
            if not user.exists():
                return _make_json_response({
                    'status': 'error',
                    'message': 'Người dùng không tồn tại'
                }, 404)
            
            # Tạo token mới
            token_payload = {
                'user_id': user.id,
                'login': user.login,
                'name': user.name,
                'email': user.email,
                'iat': datetime.utcnow(),
                'exp': datetime.utcnow() + timedelta(days=30)
            }
            
            token = jwt.encode(token_payload, JWT_SECRET_KEY, algorithm='HS256')
            
            return _make_json_response({
                'status': 'success',
                'message': 'Làm mới token thành công',
                'token': token
            }, 200)
        
        except Exception as e:
            _logger.error(f"Refresh token error: {str(e)}")
            return _make_json_response({
                'status': 'error',
                'message': 'Lỗi server khi xử lý yêu cầu'
            }, 500)
    
    @http.route('/api/v1/auth/verify-token', type='json', auth='none', methods=['POST'], csrf=False)
    @_verify_token
    def verify_token(self):
        """
        Endpoint kiểm tra token có hợp lệ không
        
        Headers:
        Authorization: Bearer <token>
        
        Response:
        {
            "status": "success",
            "valid": true,
            "user": {
                "id": 1,
                "name": "John Doe",
                "email": "john@example.com"
            }
        }
        """
        try:
            payload = request.jwt_payload
            return _make_json_response({
                'status': 'success',
                'valid': True,
                'user': {
                    'id': payload.get('user_id'),
                    'name': payload.get('name'),
                    'email': payload.get('email'),
                    'login': payload.get('login')
                }
            }, 200)
        
        except Exception as e:
            _logger.error(f"Verify token error: {str(e)}")
            return _make_json_response({
                'status': 'error',
                'message': 'Lỗi server khi xử lý yêu cầu'
            }, 500)
    
    @http.route('/api/v1/auth/logout', type='json', auth='none', methods=['POST'], csrf=False)
    @_verify_token
    def logout(self):
        """
        Endpoint đăng xuất (thường là vô nghĩa vì JWT không có trạng thái, 
        nhưng có thể dùng để xoá token ở phía client)
        
        Headers:
        Authorization: Bearer <token>
        
        Response:
        {
            "status": "success",
            "message": "Đã đăng xuất"
        }
        """
        return _make_json_response({
            'status': 'success',
            'message': 'Đã đăng xuất thành công'
        }, 200)
    
    @http.route('/api/v1/auth/me', type='json', auth='none', methods=['GET'], csrf=False)
    @_verify_token
    def get_current_user(self):
        """
        Endpoint lấy thông tin người dùng hiện tại
        
        Headers:
        Authorization: Bearer <token>
        
        Response:
        {
            "status": "success",
            "user": {
                "id": 1,
                "name": "John Doe",
                "email": "john@example.com",
                "login": "john@example.com"
            }
        }
        """
        try:
            user_id = request.jwt_payload.get('user_id')
            user = request.env['res.users'].sudo().browse(user_id)
            
            if not user.exists():
                return _make_json_response({
                    'status': 'error',
                    'message': 'Người dùng không tồn tại'
                }, 404)
            
            return _make_json_response({
                'status': 'success',
                'user': {
                    'id': user.id,
                    'name': user.name,
                    'email': user.email,
                    'login': user.login,
                }
            }, 200)
        
        except Exception as e:
            _logger.error(f"Get user error: {str(e)}")
            return _make_json_response({
                'status': 'error',
                'message': 'Lỗi server khi xử lý yêu cầu'
            }, 500)

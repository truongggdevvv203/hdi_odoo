import json
import logging
from datetime import datetime, timedelta
from functools import wraps

import jwt
from odoo import http
from odoo.http import request, Response
from ..utils.response_formatter import ResponseFormatter

_logger = logging.getLogger(__name__)

# Default secret key - sẽ được lấy từ config khi cần
DEFAULT_JWT_SECRET_KEY = 'your-secret-key-change-in-production'


def _get_jwt_secret_key():
    """Lấy JWT secret key từ config hoặc sử dụng default"""
    try:
        return request.env['ir.config_parameter'].sudo().get_param(
            'hdi_api.jwt_secret_key',
            DEFAULT_JWT_SECRET_KEY
        )
    except Exception:
        return DEFAULT_JWT_SECRET_KEY


def _is_token_blacklisted(token, db_name):
    """Kiểm tra token có trong blacklist không"""
    try:
        import odoo
        from odoo.modules.registry import Registry

        registry = Registry(db_name)
        with registry.cursor() as cr:
            env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
            blacklist = env['jwt.token.blacklist'].sudo().search([
                ('token_hash', '=', _hash_token(token))
            ], limit=1)
            return bool(blacklist)
    except Exception:
        return False


def _add_token_to_blacklist(token, user_id, db_name, exp_time):
    """Thêm token vào blacklist"""
    try:
        import odoo
        from odoo.modules.registry import Registry

        registry = Registry(db_name)
        with registry.cursor() as cr:
            env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
            env['jwt.token.blacklist'].sudo().create({
                'token_hash': _hash_token(token),
                'user_id': user_id,
                'exp_time': exp_time,
            })
            cr.commit()
    except Exception as e:
        _logger.warning(f"Failed to add token to blacklist: {str(e)}")


def _hash_token(token):
    """Băm token để lưu trữ an toàn"""
    import hashlib
    return hashlib.sha256(token.encode()).hexdigest()

def _get_json_data():
    """Helper để lấy JSON data từ request - tương thích Odoo 18"""
    try:
        # Odoo 18: Sử dụng get_json_data()
        if hasattr(request, 'get_json_data'):
            return request.get_json_data()
        # Fallback cho các phiên bản cũ hơn
        elif hasattr(request, 'jsonrequest'):
            return request.jsonrequest
        else:
            # Parse thủ công từ request body
            return json.loads(request.httprequest.data.decode('utf-8'))
    except Exception as e:
        _logger.error(f"Error parsing JSON data: {str(e)}")
        return {}


def _verify_token(f):
    """Decorator để kiểm tra JWT token - dùng cho HTTP routes"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = None

        # Lấy token từ Authorization header
        auth_header = request.httprequest.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]

        if not token:
            return ResponseFormatter.error_response('Token không được cung cấp', ResponseFormatter.HTTP_UNAUTHORIZED)

        try:
            secret_key = _get_jwt_secret_key()
            payload = jwt.decode(token, secret_key, algorithms=['HS256'])

            # Kiểm tra token có trong blacklist không
            if _is_token_blacklisted(token, payload.get('db')):
                return ResponseFormatter.error_response('Token đã bị vô hiệu hóa', ResponseFormatter.HTTP_UNAUTHORIZED)

            request.jwt_payload = payload
        except jwt.ExpiredSignatureError:
            return ResponseFormatter.error_response('Token đã hết hạn', ResponseFormatter.HTTP_UNAUTHORIZED)
        except jwt.InvalidTokenError:
            return ResponseFormatter.error_response('Token không hợp lệ', ResponseFormatter.HTTP_UNAUTHORIZED)

        return f(*args, **kwargs)

    return decorated_function


def _verify_token_json(f):
    """Decorator để kiểm tra JWT token - dùng cho JSON routes (type='json')
    Return dict để Odoo tự động wrap với JSON-RPC format"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = None

        # Lấy token từ Authorization header
        auth_header = request.httprequest.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]

        if not token:
            return ResponseFormatter.error('Token không được cung cấp', ResponseFormatter.HTTP_UNAUTHORIZED)

        try:
            secret_key = _get_jwt_secret_key()
            payload = jwt.decode(token, secret_key, algorithms=['HS256'])

            # Kiểm tra token có trong blacklist không
            if _is_token_blacklisted(token, payload.get('db')):
                return ResponseFormatter.error('Token đã bị vô hiệu hóa', ResponseFormatter.HTTP_UNAUTHORIZED)

            request.jwt_payload = payload
        except jwt.ExpiredSignatureError:
            return ResponseFormatter.error('Token đã hết hạn', ResponseFormatter.HTTP_UNAUTHORIZED)
        except jwt.InvalidTokenError:
            return ResponseFormatter.error('Token không hợp lệ', ResponseFormatter.HTTP_UNAUTHORIZED)

        return f(*args, **kwargs)

    return decorated_function


def _verify_token_http(f):
    """Decorator để kiểm tra JWT token - dùng cho HTTP routes (type='http')
    Return Response object"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = None

        # Lấy token từ Authorization header
        auth_header = request.httprequest.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]

        if not token:
            return ResponseFormatter.error_response('Token không được cung cấp', ResponseFormatter.HTTP_UNAUTHORIZED)

        try:
            secret_key = _get_jwt_secret_key()
            payload = jwt.decode(token, secret_key, algorithms=['HS256'])

            # Kiểm tra token có trong blacklist không
            if _is_token_blacklisted(token, payload.get('db')):
                return ResponseFormatter.error_response('Token đã bị vô hiệu hóa', ResponseFormatter.HTTP_UNAUTHORIZED)

            request.jwt_payload = payload
        except jwt.ExpiredSignatureError:
            return ResponseFormatter.error_response('Token đã hết hạn', ResponseFormatter.HTTP_UNAUTHORIZED)
        except jwt.InvalidTokenError:
            return ResponseFormatter.error_response('Token không hợp lệ', ResponseFormatter.HTTP_UNAUTHORIZED)

        return f(*args, **kwargs)

    return decorated_function


def _authenticate_user(db_name, login, password):
    try:
        import odoo
        from odoo.modules.registry import Registry

        registry = Registry(db_name)

        # Sử dụng method _login của res.users model
        # Trong Odoo 18, authenticate() yêu cầu credential dict
        credential = {
            'login': login,
            'password': password,
            'type': 'password'
        }

        with registry.cursor() as cr:
            env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})

            try:
                # Gọi _login thay vì authenticate
                auth_info = env.registry['res.users']._login(
                    db_name,
                    credential,
                    user_agent_env={}
                )

                # auth_info là dict chứa 'uid' và các thông tin khác
                if auth_info and isinstance(auth_info, dict):
                    return auth_info.get('uid')

            except Exception as e:
                _logger.debug(f"Login failed: {str(e)}")
                return None

        return None

    except Exception as e:
        _logger.error(f"Authentication error: {str(e)}", exc_info=True)
        return None


class MobileAppAuthAPI(http.Controller):

    @http.route('/api/v1/auth/login', type='http', auth='none', methods=['POST'], csrf=False)
    def login(self):
        try:
            # Sử dụng helper function để lấy JSON data
            data = _get_json_data()
            login = data.get('login')
            password = data.get('password')

            if not login or not password:
                return ResponseFormatter.error_response('Login và password là bắt buộc', ResponseFormatter.HTTP_BAD_REQUEST)

            db_name = request.env.cr.dbname

            if not db_name:
                return ResponseFormatter.error_response('Không xác định được database', ResponseFormatter.HTTP_BAD_REQUEST)

            # Xác thực user - Odoo 18 format
            try:
                credential = {
                    'login': login,
                    'password': password,
                    'type': 'password'
                }

                auth_info = request.env.registry['res.users'].authenticate(
                    db_name, credential, user_agent_env={}
                )

                # auth_info là dict chứa 'uid' và các thông tin khác
                if auth_info and isinstance(auth_info, dict):
                    uid = auth_info.get('uid')
                else:
                    uid = None

            except Exception as auth_error:
                _logger.debug(f"Authentication failed: {str(auth_error)}")
                uid = None

            if not uid:
                return ResponseFormatter.error_response('Tài khoản hoặc mật khẩu không chính xác', ResponseFormatter.HTTP_UNAUTHORIZED)

            user = request.env['res.users'].sudo().browse(uid)

            if not user.exists() or not user.active:
                return ResponseFormatter.error_response('Tài khoản không khả dụng', ResponseFormatter.HTTP_FORBIDDEN)

            # JWT
            secret_key = _get_jwt_secret_key()
            token_payload = {
                'user_id': uid,
                'login': user.login,
                'name': user.name,
                'email': user.email or '',
                'db': db_name,
                'iat': datetime.utcnow(),
                'exp': datetime.utcnow() + timedelta(minutes=30)
            }

            token = jwt.encode(token_payload, secret_key, algorithm='HS256')

            user_data = {
                'id': user.id,
                'name': user.name,
                'login': user.login,
                'email': user.email or '',
                'token': token,
                'expires_in': 1800
            }

            return ResponseFormatter.success_response('Đăng nhập thành công', user_data)

        except Exception as e:
            _logger.exception("Login error")
            return ResponseFormatter.error_response('Lỗi server', ResponseFormatter.HTTP_INTERNAL_ERROR)

    @http.route('/api/v1/auth/refresh-token', type='http', auth='none', methods=['POST'], csrf=False)
    @_verify_token
    def refresh_token(self):
        try:
            user_id = request.jwt_payload.get('user_id')
            db_name = request.jwt_payload.get('db')
            old_token_exp = request.jwt_payload.get('exp')

            import odoo
            from odoo.modules.registry import Registry

            registry = Registry(db_name)
            with registry.cursor() as cr:
                env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
                user = env['res.users'].browse(user_id)

                if not user.exists():
                    return ResponseFormatter.error_response('Người dùng không tồn tại', ResponseFormatter.HTTP_NOT_FOUND)

                if not user.active:
                    return ResponseFormatter.error_response('Tài khoản đã bị vô hiệu hóa', ResponseFormatter.HTTP_FORBIDDEN)

                user_info = {
                    'id': user.id,
                    'login': user.login,
                    'name': user.name,
                    'email': user.email or '',
                }

            # Blacklist token cũ
            old_token = request.httprequest.headers.get('Authorization', '').replace('Bearer ', '')
            if old_token and old_token_exp:
                old_exp_time = datetime.utcfromtimestamp(old_token_exp)
                _add_token_to_blacklist(old_token, user_id, db_name, old_exp_time)

            secret_key = _get_jwt_secret_key()
            token_payload = {
                'user_id': user_info['id'],
                'login': user_info['login'],
                'name': user_info['name'],
                'email': user_info['email'],
                'db': db_name,
                'iat': datetime.utcnow(),
                'exp': datetime.utcnow() + timedelta(minutes=30)
            }

            token = jwt.encode(token_payload, secret_key, algorithm='HS256')

            token_data = {
                'token': token,
                'expires_in': 1800
            }

            return ResponseFormatter.success_response('Làm mới token thành công', token_data)

        except Exception as e:
            _logger.error(f"Refresh token error: {str(e)}", exc_info=True)
            return ResponseFormatter.error_response('Lỗi server khi xử lý yêu cầu', ResponseFormatter.HTTP_INTERNAL_ERROR)

    @http.route('/api/v1/auth/verify-token', type='http', auth='none', methods=['POST'], csrf=False)
    @_verify_token
    def verify_token(self):
        try:
            payload = request.jwt_payload
            user_data = {
                'id': payload.get('user_id'),
                'name': payload.get('name'),
                'email': payload.get('email'),
                'login': payload.get('login'),
                'exp': payload.get('exp'),
                'valid': True
            }
            return ResponseFormatter.success_response('Token hợp lệ', user_data)

        except Exception as e:
            _logger.error(f"Verify token error: {str(e)}", exc_info=True)
            return ResponseFormatter.error_response('Lỗi server khi xử lý yêu cầu', ResponseFormatter.HTTP_INTERNAL_ERROR)

    @http.route('/api/v1/auth/logout', type='http', auth='none', methods=['POST'], csrf=False)
    @_verify_token
    def logout(self):
        try:
            # Lấy token từ header
            auth_header = request.httprequest.headers.get('Authorization', '')
            if auth_header.startswith('Bearer '):
                token = auth_header[7:]

                user_id = request.jwt_payload.get('user_id')
                db_name = request.jwt_payload.get('db')
                exp_time = datetime.utcfromtimestamp(request.jwt_payload.get('exp'))

                # Thêm token vào blacklist
                _add_token_to_blacklist(token, user_id, db_name, exp_time)

            return ResponseFormatter.success_response('Đã đăng xuất thành công')
        except Exception as e:
            _logger.error(f"Logout error: {str(e)}", exc_info=True)
            return ResponseFormatter.error_response('Lỗi server khi xử lý yêu cầu', ResponseFormatter.HTTP_INTERNAL_ERROR)

    @http.route('/api/v1/auth/me', type='http', auth='none', methods=['GET'], csrf=False)
    @_verify_token
    def get_current_user(self):
        try:
            user_id = request.jwt_payload.get('user_id')
            db_name = request.jwt_payload.get('db')

            # Lấy thông tin user
            import odoo
            from odoo.modules.registry import Registry

            registry = Registry(db_name)
            with registry.cursor() as cr:
                env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
                user = env['res.users'].browse(user_id)

                if not user.exists():
                    return ResponseFormatter.error_response('Người dùng không tồn tại', ResponseFormatter.HTTP_NOT_FOUND)

                if not user.active:
                    return ResponseFormatter.error_response('Tài khoản đã bị vô hiệu hóa', ResponseFormatter.HTTP_FORBIDDEN)

                user_info = {
                    'id': user.id,
                    'name': user.name,
                    'email': user.email or '',
                    'login': user.login,
                    'active': user.active
                }

            return ResponseFormatter.success_response('Lấy thông tin người dùng thành công', user_info)
        except Exception as e:
            _logger.error(f"Get user error: {str(e)}", exc_info=True)
            return ResponseFormatter.error_response('Lỗi server khi xử lý yêu cầu', ResponseFormatter.HTTP_INTERNAL_ERROR)

    @http.route('/api/v1/auth/change-password', type='http', auth='none', methods=['POST'], csrf=False)
    @_verify_token
    def change_password(self):
        try:
            # Sử dụng helper function để lấy JSON data
            data = _get_json_data()

            old_password = data.get('old_password')
            new_password = data.get('new_password')
            confirm_password = data.get('confirm_password')

            # Kiểm tra dữ liệu đầu vào
            if not old_password or not new_password or not confirm_password:
                return ResponseFormatter.error_response('Mật khẩu cũ, mật khẩu mới và xác nhận mật khẩu là bắt buộc', ResponseFormatter.HTTP_BAD_REQUEST)

            # Kiểm tra xác nhận mật khẩu
            if new_password != confirm_password:
                return ResponseFormatter.error_response('Mật khẩu mới và xác nhận mật khẩu không khớp', ResponseFormatter.HTTP_BAD_REQUEST)

            # Kiểm tra độ dài mật khẩu
            if len(new_password) < 8:
                return ResponseFormatter.error_response('Mật khẩu mới phải ít nhất 8 ký tự', ResponseFormatter.HTTP_BAD_REQUEST)

            # Kiểm tra mật khẩu cũ và mới không được giống nhau
            if old_password == new_password:
                return ResponseFormatter.error_response('Mật khẩu mới không được giống mật khẩu cũ', ResponseFormatter.HTTP_BAD_REQUEST)

            user_id = request.jwt_payload.get('user_id')
            db_name = request.jwt_payload.get('db')

            import odoo
            from odoo.modules.registry import Registry

            registry = Registry(db_name)
            with registry.cursor() as cr:
                env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
                user = env['res.users'].browse(user_id)

                if not user.exists():
                    return ResponseFormatter.error_response('Người dùng không tồn tại', ResponseFormatter.HTTP_NOT_FOUND)

                if not user.active:
                    return ResponseFormatter.error_response('Tài khoản đã bị vô hiệu hóa', ResponseFormatter.HTTP_FORBIDDEN)

                try:
                    # Xác thực mật khẩu cũ bằng cách gọi _authenticate_user
                    auth_uid = _authenticate_user(db_name, user.login, old_password)

                    if not auth_uid or auth_uid != user.id:
                        return ResponseFormatter.error_response('Mật khẩu cũ không chính xác', ResponseFormatter.HTTP_UNAUTHORIZED)

                    # Cập nhật mật khẩu mới (Odoo sẽ tự động hash)
                    user.write({'password': new_password})
                    cr.commit()

                    _logger.info(f"User {user.login} changed password successfully")

                    return ResponseFormatter.success_response('Đổi mật khẩu thành công')

                except Exception as pwd_error:
                    cr.rollback()
                    _logger.error(f"Password change failed for user {user.login}: {str(pwd_error)}", exc_info=True)
                    return ResponseFormatter.error_response('Lỗi khi đổi mật khẩu', ResponseFormatter.HTTP_INTERNAL_ERROR)

        except Exception as e:
            _logger.error(f"Change password error: {str(e)}", exc_info=True)
            return ResponseFormatter.error_response('Lỗi server khi xử lý yêu cầu', ResponseFormatter.HTTP_INTERNAL_ERROR)
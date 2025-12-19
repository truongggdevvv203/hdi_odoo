import json
import logging
from datetime import datetime, timedelta
from functools import wraps

import jwt
from odoo import http
from odoo.http import request, Response
from werkzeug.security import check_password_hash

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


def _is_token_blacklisted(token, db_name=None):
    """Kiểm tra token có trong blacklist không"""
    try:
        if not db_name:
            db_name = request.session.db or request.env.cr.dbname

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
    except Exception as e:
        _logger.warning(f"Failed to add token to blacklist: {str(e)}")


def _hash_token(token):
    """Băm token để lưu trữ an toàn"""
    import hashlib
    return hashlib.sha256(token.encode()).hexdigest()


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
            secret_key = _get_jwt_secret_key()
            payload = jwt.decode(token, secret_key, algorithms=['HS256'])

            # Kiểm tra token có trong blacklist không
            if _is_token_blacklisted(token, payload.get('db')):
                return _make_json_response({
                    'status': 'error',
                    'message': 'Token đã bị vô hiệu hóa'
                }, 401)

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
        try:
            try:
                data = request.jsonrequest or json.loads(request.httprequest.data.decode('utf-8'))
            except:
                data = json.loads(request.httprequest.data.decode('utf-8'))

            login = data.get('login')
            password = data.get('password')
            db_name = data.get('db')

            if not login or not password:
                return {
                    'status': 'error',
                    'message': 'Email/Username và password là bắt buộc'
                }

            if not db_name:
                db_name = request.session.db
            if not db_name:
                db_name = request.env.cr.dbname
            if not db_name:
                db_name = request.httprequest.environ.get('HTTP_X_OPENERP_DBNAME')

            if not db_name:
                return {
                    'status': 'error',
                    'message': 'Không xác định được database'
                }

            uid = None
            user_info = None

            try:
                import odoo
                from odoo.modules.registry import Registry
                from passlib.context import CryptContext

                registry = Registry(db_name)
                with registry.cursor() as cr:
                    env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
                    User = env['res.users'].sudo()
                    user = User.search([
                        '|',
                        ('login', '=', login),
                        ('email', '=', login)
                    ], limit=1)

                    if not user:
                        return {
                            'status': 'error',
                            'message': 'Tài khoản hoặc mật khẩu không chính xác'
                        }

                    try:
                        default_crypt_context = CryptContext(
                            schemes=['pbkdf2_sha512', 'plaintext'],
                            deprecated=['plaintext']
                        )

                        cr.execute(
                            "SELECT password FROM res_users WHERE id=%s",
                            (user.id,)
                        )
                        result = cr.fetchone()

                        if not result or not result[0]:
                            return {
                                'status': 'error',
                                'message': 'Tài khoản hoặc mật khẩu không chính xác'
                            }

                        stored_password = result[0]

                        valid, replacement = default_crypt_context.verify_and_update(
                            password, stored_password
                        )

                        if not valid:
                            return {
                                'status': 'error',
                                'message': 'Tài khoản hoặc mật khẩu không chính xác'
                            }

                        uid = user.id
                        user_info = {
                            'id': user.id,
                            'name': user.name,
                            'email': user.email or '',
                            'login': user.login,
                        }

                    except Exception as pwd_error:
                        _logger.warning(f"Password check failed for user {login}: {str(pwd_error)}")
                        return {
                            'status': 'error',
                            'message': 'Tài khoản hoặc mật khẩu không chính xác'
                        }

            except Exception as auth_error:
                _logger.error(f"Authentication error for user {login}: {str(auth_error)}", exc_info=True)
                return {
                    'status': 'error',
                    'message': 'Tài khoản hoặc mật khẩu không chính xác'
                }

            if not uid or not user_info:
                return {
                    'status': 'error',
                    'message': 'Tài khoản hoặc mật khẩu không chính xác'
                }

            secret_key = _get_jwt_secret_key()
            token_payload = {
                'user_id': uid,
                'login': user_info['login'],
                'name': user_info['name'],
                'email': user_info['email'],
                'db': db_name,
                'iat': datetime.utcnow(),
                'exp': datetime.utcnow() + timedelta(minutes=30)
            }

            token = jwt.encode(token_payload, secret_key, algorithm='HS256')

            return {
                'status': 'success',
                'message': 'Đăng nhập thành công',
                'token': token,
                'user': user_info
            }

        except Exception as e:
            _logger.error(f"Login error: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'message': 'Lỗi server khi xử lý yêu cầu'
            }

    @http.route('/api/v1/auth/refresh-token', type='json', auth='none', methods=['POST'], csrf=False)
    @_verify_token
    def refresh_token(self):
        try:
            user_id = request.jwt_payload.get('user_id')
            db_name = request.jwt_payload.get('db')

            if not db_name:
                return {
                    'status': 'error',
                    'message': 'Token không chứa thông tin database'
                }

            import odoo
            from odoo.modules.registry import Registry

            registry = Registry(db_name)
            with registry.cursor() as cr:
                env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
                user = env['res.users'].browse(user_id)

                if not user.exists():
                    return {
                        'status': 'error',
                        'message': 'Người dùng không tồn tại'
                    }

                user_info = {
                    'id': user.id,
                    'login': user.login,
                    'name': user.name,
                    'email': user.email or '',
                }

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

            return {
                'status': 'success',
                'message': 'Làm mới token thành công',
                'token': token
            }

        except Exception as e:
            _logger.error(f"Refresh token error: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'message': 'Lỗi server khi xử lý yêu cầu'
            }

    @http.route('/api/v1/auth/verify-token', type='json', auth='none', methods=['POST'], csrf=False)
    @_verify_token
    def verify_token(self):
        try:
            payload = request.jwt_payload
            return {
                'status': 'success',
                'valid': True,
                'user': {
                    'id': payload.get('user_id'),
                    'name': payload.get('name'),
                    'email': payload.get('email'),
                    'login': payload.get('login')
                }
            }

        except Exception as e:
            _logger.error(f"Verify token error: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'message': 'Lỗi server khi xử lý yêu cầu'
            }

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

            return _make_json_response({
                'status': 'success',
                'message': 'Đã đăng xuất thành công'
            }, 200)
        except Exception as e:
            _logger.error(f"Logout error: {str(e)}", exc_info=True)
            return _make_json_response({
                'status': 'error',
                'message': 'Lỗi server khi xử lý yêu cầu'
            }, 500)

    @http.route('/api/v1/auth/me', type='http', auth='none', methods=['GET'], csrf=False)
    @_verify_token
    def get_current_user(self):
        try:
            user_id = request.jwt_payload.get('user_id')
            db_name = request.jwt_payload.get('db')

            if not db_name:
                return _make_json_response({
                    'status': 'error',
                    'message': 'Token không chứa thông tin database'
                }, 400)

            # Lấy thông tin user
            import odoo
            from odoo.modules.registry import Registry

            registry = Registry(db_name)
            with registry.cursor() as cr:
                env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
                user = env['res.users'].browse(user_id)

                if not user.exists():
                    return _make_json_response({
                        'status': 'error',
                        'message': 'Người dùng không tồn tại'
                    }, 404)

                user_info = {
                    'id': user.id,
                    'name': user.name,
                    'email': user.email or '',
                    'login': user.login,
                }

            return _make_json_response({
                'status': 'success',
                'user': user_info
            }, 200)

        except Exception as e:
            _logger.error(f"Get user error: {str(e)}", exc_info=True)
            return _make_json_response({
                'status': 'error',
                'message': 'Lỗi server khi xử lý yêu cầu'
            }, 500)
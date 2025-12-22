import json
import logging
from datetime import datetime, timedelta
from functools import wraps

import jwt
from odoo import http
from odoo.http import request, Response

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
            cr.commit()
    except Exception as e:
        _logger.warning(f"Failed to add token to blacklist: {str(e)}")


def _hash_token(token):
    """Băm token để lưu trữ an toàn"""
    import hashlib
    return hashlib.sha256(token.encode()).hexdigest()


def _make_json_response(data, status_code=200):
    """Helper để tạo JSON response"""
    return Response(
        json.dumps(data, ensure_ascii=False),
        status=status_code,
        mimetype='application/json',
        headers={'Content-Type': 'application/json; charset=utf-8'}
    )


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


def _verify_token_json(f):
    """Decorator để kiểm tra JWT token - dùng cho JSON routes"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = None

        # Lấy token từ Authorization header
        auth_header = request.httprequest.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header[7:]

        if not token:
            return {
                'status': 'error',
                'message': 'Token không được cung cấp'
            }

        try:
            secret_key = _get_jwt_secret_key()
            payload = jwt.decode(token, secret_key, algorithms=['HS256'])

            # Kiểm tra token có trong blacklist không
            if _is_token_blacklisted(token, payload.get('db')):
                return {
                    'status': 'error',
                    'message': 'Token đã bị vô hiệu hóa'
                }

            request.jwt_payload = payload
        except jwt.ExpiredSignatureError:
            return {
                'status': 'error',
                'message': 'Token đã hết hạn'
            }
        except jwt.InvalidTokenError:
            return {
                'status': 'error',
                'message': 'Token không hợp lệ'
            }

        return f(*args, **kwargs)

    return decorated_function


def _authenticate_user(db_name, login, password):
    """
    Xác thực user với database - tương thích với Odoo 18
    Returns: user_id nếu thành công, None nếu thất bại
    """
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

    @http.route('/api/v1/auth/login', type='json', auth='none', methods=['POST'], csrf=False)
    def login(self):
        try:
            # Sử dụng helper function để lấy JSON data
            data = _get_json_data()
            login = data.get('login')
            password = data.get('password')

            if not login or not password:
                return {
                    'status': 'error',
                    'message': 'Login và password là bắt buộc'
                }

            db_name = request.env.cr.dbname

            if not db_name:
                return {
                    'status': 'error',
                    'message': 'Không xác định được database'
                }

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
                return {
                    'status': 'error',
                    'message': 'Tài khoản hoặc mật khẩu không chính xác'
                }

            user = request.env['res.users'].sudo().browse(uid)

            if not user.exists() or not user.active:
                return {
                    'status': 'error',
                    'message': 'Tài khoản không khả dụng'
                }

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

            return {
                'status': 'success',
                'message': 'Đăng nhập thành công',
                'token': token,
                'user': {
                    'id': user.id,
                    'name': user.name,
                    'login': user.login,
                    'email': user.email or ''
                },
                'expires_in': 1800
            }

        except Exception as e:
            _logger.exception("Login error")
            return {
                'status': 'error',
                'message': 'Lỗi server'
            }

    @http.route('/api/v1/auth/refresh-token', type='json', auth='none', methods=['POST'], csrf=False)
    @_verify_token_json
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

                if not user.active:
                    return {
                        'status': 'error',
                        'message': 'Tài khoản đã bị vô hiệu hóa'
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
                'exp': datetime.utcnow() + timedelta(hours=24)
            }

            token = jwt.encode(token_payload, secret_key, algorithm='HS256')

            return {
                'status': 'success',
                'message': 'Làm mới token thành công',
                'token': token,
                'expires_in': 1800
            }

        except Exception as e:
            _logger.error(f"Refresh token error: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'message': 'Lỗi server khi xử lý yêu cầu'
            }

    @http.route('/api/v1/auth/verify-token', type='json', auth='none', methods=['POST'], csrf=False)
    @_verify_token_json
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
                },
                'exp': payload.get('exp')
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

                if not user.active:
                    return _make_json_response({
                        'status': 'error',
                        'message': 'Tài khoản đã bị vô hiệu hóa'
                    }, 403)

                user_info = {
                    'id': user.id,
                    'name': user.name,
                    'email': user.email or '',
                    'login': user.login,
                    'active': user.active
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

    @http.route('/api/v1/auth/change-password', type='json', auth='none', methods=['POST'], csrf=False)
    @_verify_token_json
    def change_password(self):
        try:
            # Sử dụng helper function để lấy JSON data
            data = _get_json_data()

            old_password = data.get('old_password')
            new_password = data.get('new_password')
            confirm_password = data.get('confirm_password')

            # Kiểm tra dữ liệu đầu vào
            if not old_password or not new_password or not confirm_password:
                return {
                    'status': 'error',
                    'message': 'Mật khẩu cũ, mật khẩu mới và xác nhận mật khẩu là bắt buộc'
                }

            # Kiểm tra xác nhận mật khẩu
            if new_password != confirm_password:
                return {
                    'status': 'error',
                    'message': 'Mật khẩu mới và xác nhận mật khẩu không khớp'
                }

            # Kiểm tra độ dài mật khẩu
            if len(new_password) < 8:
                return {
                    'status': 'error',
                    'message': 'Mật khẩu mới phải ít nhất 8 ký tự'
                }

            # Kiểm tra mật khẩu cũ và mới không được giống nhau
            if old_password == new_password:
                return {
                    'status': 'error',
                    'message': 'Mật khẩu mới không được giống mật khẩu cũ'
                }

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

                if not user.active:
                    return {
                        'status': 'error',
                        'message': 'Tài khoản đã bị vô hiệu hóa'
                    }

                try:
                    # Xác thực mật khẩu cũ bằng cách gọi _authenticate_user
                    auth_uid = _authenticate_user(db_name, user.login, old_password)

                    if not auth_uid or auth_uid != user.id:
                        return {
                            'status': 'error',
                            'message': 'Mật khẩu cũ không chính xác'
                        }

                    # Cập nhật mật khẩu mới (Odoo sẽ tự động hash)
                    user.write({'password': new_password})
                    cr.commit()

                    _logger.info(f"User {user.login} changed password successfully")

                    return {
                        'status': 'success',
                        'message': 'Đổi mật khẩu thành công'
                    }

                except Exception as pwd_error:
                    cr.rollback()
                    _logger.error(f"Password change failed for user {user.login}: {str(pwd_error)}", exc_info=True)
                    return {
                        'status': 'error',
                        'message': 'Lỗi khi đổi mật khẩu'
                    }

        except Exception as e:
            _logger.error(f"Change password error: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'message': 'Lỗi server khi xử lý yêu cầu'
            }
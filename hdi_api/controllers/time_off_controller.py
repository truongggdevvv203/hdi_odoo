import json
import logging
from datetime import datetime
from odoo import http
from odoo.http import request
from .auth_controller import _verify_token_http, _get_json_data
from ..utils.response_formatter import ResponseFormatter

_logger = logging.getLogger(__name__)


class TimeOffController(http.Controller):

    @http.route('/api/time-off/types', type='http', auth='none', methods=['GET'], csrf=False)
    @_verify_token_http
    def get_leave_types(self):
        """Lấy danh sách các loại nghỉ"""
        try:
            jwt_payload = getattr(request, 'jwt_payload', {})
            db_name = jwt_payload.get('db')

            if not db_name:
                return ResponseFormatter.error_response('Token không chứa thông tin database', ResponseFormatter.HTTP_BAD_REQUEST)

            import odoo
            from odoo.modules.registry import Registry

            registry = Registry(db_name)
            with registry.cursor() as cr:
                env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})

                try:
                    # Sử dụng model method
                    types_data = env['hr.leave'].sudo().api_get_leave_types()
                    cr.commit()
                    
                    return ResponseFormatter.success_response('Lấy danh sách loại nghỉ thành công', types_data)
                
                except Exception as e:
                    cr.rollback()
                    _logger.error(f"Error in model api_get_leave_types: {str(e)}", exc_info=True)
                    return ResponseFormatter.error_response(f'Lỗi: {str(e)}', ResponseFormatter.HTTP_INTERNAL_ERROR)

        except Exception as e:
            _logger.error(f"Error in get_leave_types: {str(e)}", exc_info=True)
            return ResponseFormatter.error_response('Có lỗi xảy ra khi lấy danh sách loại nghỉ', ResponseFormatter.HTTP_INTERNAL_ERROR)

    @http.route('/api/time-off/remaining-days', type='http', auth='none', methods=['GET'], csrf=False)
    @_verify_token_http
    def get_remaining_days(self):
        """Lấy số ngày phép còn lại của user đang đăng nhập"""
        try:
            jwt_payload = getattr(request, 'jwt_payload', {})
            user_id = jwt_payload.get('user_id')
            db_name = jwt_payload.get('db')

            if not db_name:
                return ResponseFormatter.error_response('Token không chứa thông tin database', ResponseFormatter.HTTP_BAD_REQUEST)

            import odoo
            from odoo.modules.registry import Registry

            registry = Registry(db_name)
            with registry.cursor() as cr:
                env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})

                try:
                    # Sử dụng model method
                    result = env['hr.leave'].sudo().api_get_remaining_days(user_id)
                    cr.commit()
                    
                    return ResponseFormatter.success_response('Lấy số ngày phép còn lại thành công', result)
                
                except Exception as e:
                    cr.rollback()
                    _logger.error(f"Error in model api_get_remaining_days: {str(e)}", exc_info=True)
                    return ResponseFormatter.error_response(f'Lỗi: {str(e)}', ResponseFormatter.HTTP_INTERNAL_ERROR)

        except Exception as e:
            _logger.error(f"Error in get_remaining_days: {str(e)}", exc_info=True)
            return ResponseFormatter.error_response('Có lỗi xảy ra khi lấy số ngày phép', ResponseFormatter.HTTP_INTERNAL_ERROR)

    @http.route('/api/time-off/list', type='http', auth='none', methods=['GET'], csrf=False)
    @_verify_token_http
    def get_leave_list(self):
        """Lấy danh sách đơn xin nghỉ"""
        try:
            jwt_payload = getattr(request, 'jwt_payload', {})
            user_id = jwt_payload.get('user_id')
            db_name = jwt_payload.get('db')

            if not db_name:
                return ResponseFormatter.error_response('Token không chứa thông tin database', ResponseFormatter.HTTP_BAD_REQUEST)

            # Lấy params từ query string
            limit = int(request.httprequest.args.get('limit', 10))
            offset = int(request.httprequest.args.get('offset', 0))
            state = request.httprequest.args.get('state')  # draft, confirm, refuse, validate

            import odoo
            from odoo.modules.registry import Registry

            registry = Registry(db_name)
            with registry.cursor() as cr:
                env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})

                try:
                    # Sử dụng model method
                    result = env['hr.leave'].sudo().api_get_leave_list(
                        user_id, limit=limit, offset=offset, state=state)
                    cr.commit()
                    
                    return ResponseFormatter.success_response('Lấy danh sách đơn xin nghỉ thành công', result)
                
                except Exception as e:
                    cr.rollback()
                    _logger.error(f"Error in model api_get_leave_list: {str(e)}", exc_info=True)
                    return ResponseFormatter.error_response(f'Lỗi: {str(e)}', ResponseFormatter.HTTP_INTERNAL_ERROR)

        except Exception as e:
            _logger.error(f"Error in get_leave_list: {str(e)}", exc_info=True)
            return ResponseFormatter.error_response('Có lỗi xảy ra khi lấy danh sách đơn xin nghỉ', ResponseFormatter.HTTP_INTERNAL_ERROR)

    @http.route('/api/time-off/detail', type='http', auth='none', methods=['POST'], csrf=False)
    @_verify_token_http
    def get_leave_detail(self):
        """Lấy thông tin chi tiết của một đơn xin nghỉ (leave_id trong body)"""
        try:
            data = _get_json_data()
            leave_id = data.get('leave_id')
            if not leave_id:
                return ResponseFormatter.error_response('leave_id là bắt buộc', ResponseFormatter.HTTP_BAD_REQUEST)

            jwt_payload = getattr(request, 'jwt_payload', {})
            user_id = jwt_payload.get('user_id')
            db_name = jwt_payload.get('db')

            if not db_name:
                return ResponseFormatter.error_response('Token không chứa thông tin database', ResponseFormatter.HTTP_BAD_REQUEST)

            import odoo
            from odoo.modules.registry import Registry

            registry = Registry(db_name)
            with registry.cursor() as cr:
                env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})

                try:
                    # Sử dụng model method
                    leave_data = env['hr.leave'].sudo().api_get_leave_detail(leave_id, user_id)
                    cr.commit()
                    
                    return ResponseFormatter.success_response('Lấy thông tin chi tiết đơn xin nghỉ thành công', leave_data)
                
                except Exception as e:
                    cr.rollback()
                    _logger.error(f"Error in model api_get_leave_detail: {str(e)}", exc_info=True)
                    return ResponseFormatter.error_response(f'Lỗi: {str(e)}', ResponseFormatter.HTTP_INTERNAL_ERROR)

        except Exception as e:
            _logger.error(f"Error in get_leave_detail: {str(e)}", exc_info=True)
            return ResponseFormatter.error_response('Có lỗi xảy ra khi lấy chi tiết đơn xin nghỉ', ResponseFormatter.HTTP_INTERNAL_ERROR)

    @http.route('/api/time-off/create', type='http', auth='none', methods=['POST'], csrf=False)
    @_verify_token_http
    def create_leave(self):
        """Tạo bản ghi đăng ký xin nghỉ"""
        try:
            data = _get_json_data()

            jwt_payload = getattr(request, 'jwt_payload', {})
            user_id = jwt_payload.get('user_id')
            db_name = jwt_payload.get('db')

            if not db_name:
                return ResponseFormatter.error_response('Token không chứa thông tin database', ResponseFormatter.HTTP_BAD_REQUEST)

            import odoo
            from odoo.modules.registry import Registry

            registry = Registry(db_name)
            with registry.cursor() as cr:
                env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})

                try:
                    # Sử dụng model method
                    result = env['hr.leave'].sudo().api_create_leave(data, user_id)
                    cr.commit()
                    
                    return ResponseFormatter.success_response('Tạo đơn xin nghỉ thành công', result)

                except Exception as e:
                    cr.rollback()
                    _logger.error(f"Error creating leave: {str(e)}", exc_info=True)
                    return ResponseFormatter.error_response(f'Lỗi: {str(e)}', ResponseFormatter.HTTP_INTERNAL_ERROR)

        except Exception as e:
            _logger.error(f"Error in create_leave: {str(e)}", exc_info=True)
            return ResponseFormatter.error_response('Có lỗi xảy ra khi tạo đơn xin nghỉ', ResponseFormatter.HTTP_INTERNAL_ERROR)

    @http.route('/api/time-off/update/<int:leave_id>', type='http', auth='none', methods=['PUT'], csrf=False)
    @_verify_token_http
    def update_leave(self, leave_id):
        """Sửa bản ghi đăng ký xin nghỉ"""
        try:
            data = _get_json_data()

            jwt_payload = getattr(request, 'jwt_payload', {})
            user_id = jwt_payload.get('user_id')
            db_name = jwt_payload.get('db')

            if not db_name:
                return ResponseFormatter.error_response('Token không chứa thông tin database', ResponseFormatter.HTTP_BAD_REQUEST)

            import odoo
            from odoo.modules.registry import Registry

            registry = Registry(db_name)
            with registry.cursor() as cr:
                env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})

                try:
                    # Lấy leave và sử dụng model method
                    leave = env['hr.leave'].sudo().browse(leave_id)
                    if not leave.exists():
                        return ResponseFormatter.error_response('Không tìm thấy đơn xin nghỉ', ResponseFormatter.HTTP_NOT_FOUND)
                    
                    result = leave.api_update_leave(data, user_id)
                    cr.commit()
                    
                    return ResponseFormatter.success_response('Cập nhật đơn xin nghỉ thành công', result)

                except Exception as e:
                    cr.rollback()
                    _logger.error(f"Error updating leave: {str(e)}", exc_info=True)
                    return ResponseFormatter.error_response(f'Lỗi: {str(e)}', ResponseFormatter.HTTP_INTERNAL_ERROR)

        except Exception as e:
            _logger.error(f"Error in update_leave: {str(e)}", exc_info=True)
            return ResponseFormatter.error_response('Có lỗi xảy ra khi cập nhật đơn xin nghỉ', ResponseFormatter.HTTP_INTERNAL_ERROR)

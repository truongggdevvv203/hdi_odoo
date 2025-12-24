"""
API Controller for Time Off
Xử lý các endpoint API cho quản lý nghỉ phép
"""
import logging
from odoo import http
from odoo.http import request

from .auth_controller import _verify_token_http, _get_json_data
from ..utils.response_formatter import ResponseFormatter

_logger = logging.getLogger(__name__)


class TimeOffController(http.Controller):
    """API endpoints cho quản lý time off/nghỉ phép"""

    def _get_env(self):
        """Lấy environment từ token"""
        db_name = request.jwt_payload.get('db')
        import odoo
        from odoo.modules.registry import Registry

        registry = Registry(db_name)
        cr = registry.cursor()
        return odoo.api.Environment(cr, odoo.SUPERUSER_ID, {}), cr

    # ========== GET LEAVE TYPES ==========
    @http.route('/api/time-off/types', type='http', auth='none', methods=['GET'], csrf=False)
    @_verify_token_http
    def get_leave_types(self):
        """Lấy danh sách các loại nghỉ"""
        try:
            env, cr = self._get_env()
            
            try:
                types_data = env['hr.leave'].sudo().api_get_leave_types()
                cr.commit()
                
                return ResponseFormatter.success_response('Lấy danh sách loại nghỉ thành công', types_data)
            except Exception as e:
                cr.rollback()
                raise

        except Exception as e:
            _logger.error(f"Get leave types error: {str(e)}", exc_info=True)
            return ResponseFormatter.error_response(f'Lỗi: {str(e)}', ResponseFormatter.HTTP_INTERNAL_ERROR)

    # ========== GET REMAINING DAYS ==========
    @http.route('/api/time-off/remaining-days', type='http', auth='none', methods=['GET'], csrf=False)
    @_verify_token_http
    def get_remaining_days(self):
        """Lấy số ngày phép còn lại"""
        try:
            user_id = request.jwt_payload.get('user_id')
            env, cr = self._get_env()
            
            try:
                result = env['hr.leave'].sudo().api_get_remaining_days(user_id)
                cr.commit()
                
                return ResponseFormatter.success_response('Lấy số ngày phép còn lại thành công', result)
            except Exception as e:
                cr.rollback()
                raise

        except Exception as e:
            _logger.error(f"Get remaining days error: {str(e)}", exc_info=True)
            return ResponseFormatter.error_response(f'Lỗi: {str(e)}', ResponseFormatter.HTTP_INTERNAL_ERROR)

    # ========== GET LEAVE LIST ==========
    @http.route('/api/time-off/list', type='http', auth='none', methods=['GET'], csrf=False)
    @_verify_token_http
    def get_leave_list(self):
        """Lấy danh sách đơn xin nghỉ"""
        try:
            user_id = request.jwt_payload.get('user_id')
            limit = int(request.httprequest.args.get('limit', 10))
            offset = int(request.httprequest.args.get('offset', 0))
            state = request.httprequest.args.get('state')
            
            env, cr = self._get_env()
            
            try:
                result = env['hr.leave'].sudo().api_get_leave_list(user_id, limit=limit, offset=offset, state=state)
                cr.commit()
                
                return ResponseFormatter.success_response('Lấy danh sách đơn xin nghỉ thành công', result)
            except Exception as e:
                cr.rollback()
                raise

        except Exception as e:
            _logger.error(f"Get leave list error: {str(e)}", exc_info=True)
            return ResponseFormatter.error_response(f'Lỗi: {str(e)}', ResponseFormatter.HTTP_INTERNAL_ERROR)

    # ========== GET LEAVE DETAIL ==========
    @http.route('/api/time-off/detail', type='http', auth='none', methods=['POST'], csrf=False)
    @_verify_token_http
    def get_leave_detail(self):
        """Lấy chi tiết đơn xin nghỉ"""
        try:
            data = _get_json_data()
            leave_id = data.get('leave_id')
            user_id = request.jwt_payload.get('user_id')
            env, cr = self._get_env()
            
            try:
                leave_data = env['hr.leave'].sudo().api_get_leave_detail(leave_id, user_id)
                cr.commit()
                
                return ResponseFormatter.success_response('Lấy chi tiết đơn xin nghỉ thành công', leave_data)
            except Exception as e:
                cr.rollback()
                raise

        except Exception as e:
            _logger.error(f"Get leave detail error: {str(e)}", exc_info=True)
            return ResponseFormatter.error_response(f'Lỗi: {str(e)}', ResponseFormatter.HTTP_INTERNAL_ERROR)

    # ========== CREATE LEAVE ==========
    @http.route('/api/time-off/create', type='http', auth='none', methods=['POST'], csrf=False)
    @_verify_token_http
    def create_leave(self):
        """Tạo đơn xin nghỉ"""
        try:
            data = _get_json_data()
            user_id = request.jwt_payload.get('user_id')
            env, cr = self._get_env()
            
            try:
                result = env['hr.leave'].sudo().api_create_leave(data, user_id)
                cr.commit()
                
                return ResponseFormatter.success_response('Tạo đơn xin nghỉ thành công', result)
            except Exception as e:
                cr.rollback()
                raise

        except Exception as e:
            _logger.error(f"Create leave error: {str(e)}", exc_info=True)
            return ResponseFormatter.error_response(f'Lỗi: {str(e)}', ResponseFormatter.HTTP_INTERNAL_ERROR)

    # ========== UPDATE LEAVE ==========
    @http.route('/api/time-off/update/<int:leave_id>', type='http', auth='none', methods=['PUT'], csrf=False)
    @_verify_token_http
    def update_leave(self, leave_id):
        """Cập nhật đơn xin nghỉ"""
        try:
            data = _get_json_data()
            user_id = request.jwt_payload.get('user_id')
            env, cr = self._get_env()
            
            try:
                leave = env['hr.leave'].sudo().browse(leave_id)
                result = leave.api_update_leave(data, user_id)
                cr.commit()
                
                return ResponseFormatter.success_response('Cập nhật đơn xin nghỉ thành công', result)
            except Exception as e:
                cr.rollback()
                raise

        except Exception as e:
            _logger.error(f"Update leave error: {str(e)}", exc_info=True)
            return ResponseFormatter.error_response(f'Lỗi: {str(e)}', ResponseFormatter.HTTP_INTERNAL_ERROR)

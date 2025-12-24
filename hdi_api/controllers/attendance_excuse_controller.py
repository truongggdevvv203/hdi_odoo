"""
API Controller for Attendance Excuse
Xử lý các endpoint API cho giải trình chấm công
"""
import logging
from odoo import http
from odoo.http import request

from .auth_controller import _verify_token_http, _get_json_data
from ..utils.response_formatter import ResponseFormatter

_logger = logging.getLogger(__name__)


class MobileAppAttendanceExcuseAPI(http.Controller):
    """API endpoints cho quản lý giải trình chấm công"""

    def _call_model_method(self, method_name, *args, **kwargs):
        """Helper để gọi model method với xử lý database"""
        jwt_payload = getattr(request, 'jwt_payload', {})
        db_name = jwt_payload.get('db')
        
        import odoo
        from odoo.modules.registry import Registry

        registry = Registry(db_name)
        with registry.cursor() as cr:
            env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
            
            try:
                excuse_model = env['attendance.excuse'].sudo()
                method = getattr(excuse_model, method_name)
                result = method(*args, **kwargs)
                cr.commit()
                return result
            except Exception as e:
                cr.rollback()
                _logger.error(f"Error in {method_name}: {str(e)}", exc_info=True)
                raise

    # ========== CREATE ==========
    @http.route('/api/v1/attendance-excuse/create', type='http', auth='none', methods=['POST'], csrf=False)
    @_verify_token_http
    def create_excuse(self):
        """Tạo giải trình chấm công mới"""
        try:
            data = _get_json_data()
            jwt_payload = getattr(request, 'jwt_payload', {})
            user_id = jwt_payload.get('user_id')

            result = self._call_model_method('api_create_excuse', data, user_id)
            return ResponseFormatter.success_response('Tạo giải trình thành công', result)
        
        except Exception as e:
            _logger.error(f"Error in create_excuse: {str(e)}", exc_info=True)
            return ResponseFormatter.error_response(f'Lỗi: {str(e)}', ResponseFormatter.HTTP_INTERNAL_ERROR)

    # ========== GET DETAIL ==========
    @http.route('/api/v1/attendance-excuse/get', type='http', auth='none', methods=['POST'], csrf=False)
    @_verify_token_http
    def get_excuse(self):
        """Lấy chi tiết giải trình chấm công"""
        try:
            data = _get_json_data()
            excuse_id = data.get('excuse_id')
            jwt_payload = getattr(request, 'jwt_payload', {})
            user_id = jwt_payload.get('user_id')

            db_name = jwt_payload.get('db')
            import odoo
            from odoo.modules.registry import Registry

            registry = Registry(db_name)
            with registry.cursor() as cr:
                env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
                
                try:
                    excuse = env['attendance.excuse'].sudo().browse(excuse_id)
                    result = excuse.api_get_excuse_detail(user_id)
                    cr.commit()
                    
                    return ResponseFormatter.success_response('Lấy chi tiết giải trình thành công', result)
                
                except Exception as e:
                    cr.rollback()
                    _logger.error(f"Error in api_get_excuse_detail: {str(e)}", exc_info=True)
                    raise

        except Exception as e:
            _logger.error(f"Error in get_excuse: {str(e)}", exc_info=True)
            return ResponseFormatter.error_response(f'Lỗi: {str(e)}', ResponseFormatter.HTTP_INTERNAL_ERROR)

    # ========== LIST ==========
    @http.route('/api/v1/attendance-excuse/list', type='http', auth='none', methods=['POST'], csrf=False)
    @_verify_token_http
    def get_excuse_list(self):
        """Lấy danh sách giải trình chấm công"""
        try:
            data = _get_json_data()
            jwt_payload = getattr(request, 'jwt_payload', {})
            user_id = jwt_payload.get('user_id')

            limit = data.get('limit', 10)
            offset = data.get('offset', 0)
            state = data.get('state')

            result = self._call_model_method('api_get_my_excuse_list', user_id, 
                                            limit=limit, offset=offset, state=state)
            return ResponseFormatter.success_response('Lấy danh sách giải trình thành công', result)
        
        except Exception as e:
            _logger.error(f"Error in get_excuse_list: {str(e)}", exc_info=True)
            return ResponseFormatter.error_response(f'Lỗi: {str(e)}', ResponseFormatter.HTTP_INTERNAL_ERROR)

    # ========== SUBMIT ==========
    @http.route('/api/v1/attendance-excuse/submit', type='http', auth='none', methods=['POST'], csrf=False)
    @_verify_token_http
    def submit_excuse(self):
        """Submit giải trình để duyệt"""
        try:
            data = _get_json_data()
            excuse_id = data.get('excuse_id')
            jwt_payload = getattr(request, 'jwt_payload', {})
            user_id = jwt_payload.get('user_id')

            db_name = jwt_payload.get('db')
            import odoo
            from odoo.modules.registry import Registry

            registry = Registry(db_name)
            with registry.cursor() as cr:
                env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
                
                try:
                    excuse = env['attendance.excuse'].sudo().browse(excuse_id)
                    result = excuse.api_submit_excuse(user_id)
                    cr.commit()
                    
                    return ResponseFormatter.success_response('Submit giải trình thành công', result)
                
                except Exception as e:
                    cr.rollback()
                    _logger.error(f"Error in api_submit_excuse: {str(e)}", exc_info=True)
                    raise

        except Exception as e:
            _logger.error(f"Error in submit_excuse: {str(e)}", exc_info=True)
            return ResponseFormatter.error_response(f'Lỗi: {str(e)}', ResponseFormatter.HTTP_INTERNAL_ERROR)

    # ========== UPDATE ==========
    @http.route('/api/v1/attendance-excuse/update', type='http', auth='none', methods=['POST'], csrf=False)
    @_verify_token_http
    def update_excuse(self):
        """Cập nhật giải trình (chỉ khi draft)"""
        try:
            data = _get_json_data()
            excuse_id = data.get('excuse_id')
            jwt_payload = getattr(request, 'jwt_payload', {})
            user_id = jwt_payload.get('user_id')

            db_name = jwt_payload.get('db')
            import odoo
            from odoo.modules.registry import Registry

            registry = Registry(db_name)
            with registry.cursor() as cr:
                env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
                
                try:
                    excuse = env['attendance.excuse'].sudo().browse(excuse_id)
                    
                    # Kiểm tra quyền và state từ model write override
                    update_data = {}
                    if 'reason' in data:
                        update_data['reason'] = data['reason']
                    if 'requested_checkin' in data:
                        update_data['requested_checkin'] = data['requested_checkin']
                    if 'requested_checkout' in data:
                        update_data['requested_checkout'] = data['requested_checkout']

                    if update_data:
                        excuse.write(update_data)

                    result = excuse.api_get_excuse_detail(user_id)
                    cr.commit()
                    
                    return ResponseFormatter.success_response('Cập nhật giải trình thành công', result)
                
                except Exception as e:
                    cr.rollback()
                    _logger.error(f"Error updating excuse: {str(e)}", exc_info=True)
                    raise

        except Exception as e:
            _logger.error(f"Error in update_excuse: {str(e)}", exc_info=True)
            return ResponseFormatter.error_response(f'Lỗi: {str(e)}', ResponseFormatter.HTTP_INTERNAL_ERROR)

    # ========== DELETE ==========
    @http.route('/api/v1/attendance-excuse/delete', type='http', auth='none', methods=['POST'], csrf=False)
    @_verify_token_http
    def delete_excuse(self):
        """Xóa giải trình (chỉ khi draft)"""
        try:
            data = _get_json_data()
            excuse_id = data.get('excuse_id')

            db_name = getattr(request, 'jwt_payload', {}).get('db')
            import odoo
            from odoo.modules.registry import Registry

            registry = Registry(db_name)
            with registry.cursor() as cr:
                env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
                
                try:
                    excuse = env['attendance.excuse'].sudo().browse(excuse_id)
                    excuse.unlink()
                    cr.commit()
                    
                    return ResponseFormatter.success_response('Xóa giải trình thành công', {'deleted': True})
                
                except Exception as e:
                    cr.rollback()
                    _logger.error(f"Error deleting excuse: {str(e)}", exc_info=True)
                    raise

        except Exception as e:
            _logger.error(f"Error in delete_excuse: {str(e)}", exc_info=True)
            return ResponseFormatter.error_response(f'Lỗi: {str(e)}', ResponseFormatter.HTTP_INTERNAL_ERROR)

    # ========== APPROVE ==========
    @http.route('/api/v1/attendance-excuse/approve', type='http', auth='none', methods=['POST'], csrf=False)
    @_verify_token_http
    def approve_excuse(self):
        """Phê duyệt giải trình"""
        try:
            data = _get_json_data()
            excuse_id = data.get('excuse_id')
            jwt_payload = getattr(request, 'jwt_payload', {})
            user_id = jwt_payload.get('user_id')

            if not excuse_id:
                return ResponseFormatter.error_response('excuse_id là bắt buộc', ResponseFormatter.HTTP_BAD_REQUEST)

            db_name = jwt_payload.get('db')
            import odoo
            from odoo.modules.registry import Registry

            registry = Registry(db_name)
            with registry.cursor() as cr:
                env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
                
                try:
                    excuse = env['attendance.excuse'].sudo().browse(excuse_id)
                    
                    # Call action_approve từ model
                    excuse.api_approve_excuse(user_id, data.get('corrected_checkin'), data.get('corrected_checkout'))
                    cr.commit()
                    
                    result = excuse.api_get_excuse_detail(user_id)
                    return ResponseFormatter.success_response('Phê duyệt giải trình thành công', result)
                
                except Exception as e:
                    cr.rollback()
                    _logger.error(f"Error approving excuse: {str(e)}", exc_info=True)
                    raise

        except Exception as e:
            _logger.error(f"Error in approve_excuse: {str(e)}", exc_info=True)
            return ResponseFormatter.error_response(f'Lỗi: {str(e)}', ResponseFormatter.HTTP_INTERNAL_ERROR)

    # ========== REJECT ==========
    @http.route('/api/v1/attendance-excuse/reject', type='http', auth='none', methods=['POST'], csrf=False)
    @_verify_token_http
    def reject_excuse(self):
        """Từ chối giải trình"""
        try:
            data = _get_json_data()
            excuse_id = data.get('excuse_id')
            rejection_reason = data.get('rejection_reason', '')
            jwt_payload = getattr(request, 'jwt_payload', {})
            user_id = jwt_payload.get('user_id')

            if not excuse_id:
                return ResponseFormatter.error_response('excuse_id là bắt buộc', ResponseFormatter.HTTP_BAD_REQUEST)

            db_name = jwt_payload.get('db')
            import odoo
            from odoo.modules.registry import Registry

            registry = Registry(db_name)
            with registry.cursor() as cr:
                env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
                
                try:
                    excuse = env['attendance.excuse'].sudo().browse(excuse_id)
                    
                    # Call api_reject_excuse từ model
                    excuse.api_reject_excuse(user_id, rejection_reason)
                    cr.commit()
                    
                    result = excuse.api_get_excuse_detail(user_id)
                    return ResponseFormatter.success_response('Từ chối giải trình thành công', result)
                
                except Exception as e:
                    cr.rollback()
                    _logger.error(f"Error rejecting excuse: {str(e)}", exc_info=True)
                    raise

        except Exception as e:
            _logger.error(f"Error in reject_excuse: {str(e)}", exc_info=True)
            return ResponseFormatter.error_response(f'Lỗi: {str(e)}', ResponseFormatter.HTTP_INTERNAL_ERROR)

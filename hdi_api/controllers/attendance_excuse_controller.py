import json
import logging
from datetime import datetime, timedelta

from odoo import http
from odoo.http import request
from odoo.exceptions import UserError, ValidationError

from .auth_controller import _verify_token_http, _get_json_data
from ..utils.response_formatter import ResponseFormatter

_logger = logging.getLogger(__name__)


class MobileAppAttendanceExcuseAPI(http.Controller):

    @http.route('/api/v1/attendance-excuse/create', type='http', auth='none', methods=['POST'], csrf=False)
    @_verify_token_http
    def create_excuse(self):
        """
        Tạo giải trình chấm công mới
        """
        try:
            data = _get_json_data()
            
            # Lấy thông tin người dùng từ token
            jwt_payload = getattr(request, 'jwt_payload', {})
            user_id = jwt_payload.get('user_id')
            db_name = jwt_payload.get('db')

            if not db_name:
                return ResponseFormatter.error_response(
                    'Token không chứa thông tin database',
                    ResponseFormatter.HTTP_BAD_REQUEST
                )

            import odoo
            from odoo.modules.registry import Registry

            registry = Registry(db_name)
            with registry.cursor() as cr:
                env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
                
                try:
                    # Sử dụng model method
                    result = env['attendance.excuse'].sudo().api_create_excuse(data, user_id)
                    cr.commit()
                    
                    return ResponseFormatter.success_response('Tạo giải trình thành công', result)
                
                except Exception as e:
                    cr.rollback()
                    _logger.error(f"Error in model api_create_excuse: {str(e)}", exc_info=True)
                    return ResponseFormatter.error_response(f'Lỗi: {str(e)}', ResponseFormatter.HTTP_INTERNAL_ERROR)

        except Exception as e:
            _logger.error(f"Error in create_excuse: {str(e)}", exc_info=True)
            return ResponseFormatter.error_response(
                'Có lỗi xảy ra khi tạo giải trình chấm công',
                ResponseFormatter.HTTP_INTERNAL_ERROR
            )

    @http.route('/api/v1/attendance-excuse/get', type='http', auth='none', methods=['POST'], csrf=False)
    @_verify_token_http
    def get_excuse(self):
        """
        Lấy chi tiết giải trình chấm công
        """
        try:
            data = _get_json_data()
            excuse_id = data.get('excuse_id')
            
            if not excuse_id:
                return ResponseFormatter.error_response(
                    'excuse_id là bắt buộc',
                    ResponseFormatter.HTTP_BAD_REQUEST
                )

            jwt_payload = getattr(request, 'jwt_payload', {})
            user_id = jwt_payload.get('user_id')
            db_name = jwt_payload.get('db')

            if not db_name:
                return ResponseFormatter.error_response(
                    'Token không chứa thông tin database',
                    ResponseFormatter.HTTP_BAD_REQUEST
                )

            import odoo
            from odoo.modules.registry import Registry

            registry = Registry(db_name)
            with registry.cursor() as cr:
                env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
                
                try:
                    # Lấy excuse và sử dụng model method
                    excuse = env['attendance.excuse'].sudo().browse(excuse_id)
                    if not excuse.exists():
                        return ResponseFormatter.error_response('Không tìm thấy giải trình', ResponseFormatter.HTTP_NOT_FOUND)
                    
                    result = excuse.api_get_excuse_detail(user_id)
                    cr.commit()
                    
                    return ResponseFormatter.success_response('Lấy chi tiết giải trình thành công', result)
                
                except Exception as e:
                    cr.rollback()
                    _logger.error(f"Error in model api_get_excuse_detail: {str(e)}", exc_info=True)
                    return ResponseFormatter.error_response(f'Lỗi: {str(e)}', ResponseFormatter.HTTP_INTERNAL_ERROR)

        except Exception as e:
            _logger.error(f"Error in get_excuse: {str(e)}", exc_info=True)
            return ResponseFormatter.error_response(
                'Có lỗi xảy ra khi lấy chi tiết giải trình',
                ResponseFormatter.HTTP_INTERNAL_ERROR
            )

    @http.route('/api/v1/attendance-excuse/list', type='http', auth='none', methods=['POST'], csrf=False)
    @_verify_token_http
    def get_excuse_list(self):
        """
        Lấy danh sách giải trình chấm công
        """
        try:
            data = _get_json_data()
            
            # Lấy params
            limit = data.get('limit', 10)
            offset = data.get('offset', 0)
            state = data.get('state')  # draft, submitted, approved, rejected

            jwt_payload = getattr(request, 'jwt_payload', {})
            user_id = jwt_payload.get('user_id')
            db_name = jwt_payload.get('db')

            if not db_name:
                return ResponseFormatter.error_response(
                    'Token không chứa thông tin database',
                    ResponseFormatter.HTTP_BAD_REQUEST
                )

            import odoo
            from odoo.modules.registry import Registry

            registry = Registry(db_name)
            with registry.cursor() as cr:
                env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
                
                try:
                    # Sử dụng model method
                    result = env['attendance.excuse'].sudo().api_get_my_excuse_list(
                        user_id, limit=limit, offset=offset, state=state)
                    cr.commit()
                    
                    return ResponseFormatter.success_response('Lấy danh sách giải trình thành công', result)
                
                except Exception as e:
                    cr.rollback()
                    _logger.error(f"Error in model api_get_my_excuse_list: {str(e)}", exc_info=True)
                    return ResponseFormatter.error_response(f'Lỗi: {str(e)}', ResponseFormatter.HTTP_INTERNAL_ERROR)

        except Exception as e:
            _logger.error(f"Error in get_excuse_list: {str(e)}", exc_info=True)
            return ResponseFormatter.error_response(
                'Có lỗi xảy ra khi lấy danh sách giải trình',
                ResponseFormatter.HTTP_INTERNAL_ERROR
            )

    @http.route('/api/v1/attendance-excuse/submit', type='http', auth='none', methods=['POST'], csrf=False)
    @_verify_token_http
    def submit_excuse(self):
        """
        Submit giải trình chấm công để duyệt
        """
        try:
            data = _get_json_data()
            excuse_id = data.get('excuse_id')
            
            if not excuse_id:
                return ResponseFormatter.error_response(
                    'excuse_id là bắt buộc',
                    ResponseFormatter.HTTP_BAD_REQUEST
                )

            jwt_payload = getattr(request, 'jwt_payload', {})
            user_id = jwt_payload.get('user_id')
            db_name = jwt_payload.get('db')

            if not db_name:
                return ResponseFormatter.error_response(
                    'Token không chứa thông tin database',
                    ResponseFormatter.HTTP_BAD_REQUEST
                )

            import odoo
            from odoo.modules.registry import Registry

            registry = Registry(db_name)
            with registry.cursor() as cr:
                env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
                
                try:
                    # Lấy excuse và sử dụng model method
                    excuse = env['attendance.excuse'].sudo().browse(excuse_id)
                    if not excuse.exists():
                        return ResponseFormatter.error_response('Không tìm thấy giải trình', ResponseFormatter.HTTP_NOT_FOUND)
                    
                    result = excuse.api_submit_excuse(user_id)
                    cr.commit()
                    
                    return ResponseFormatter.success_response('Submit giải trình thành công', result)
                
                except Exception as e:
                    cr.rollback()
                    _logger.error(f"Error in model api_submit_excuse: {str(e)}", exc_info=True)
                    return ResponseFormatter.error_response(f'Lỗi: {str(e)}', ResponseFormatter.HTTP_INTERNAL_ERROR)

        except Exception as e:
            _logger.error(f"Error in submit_excuse: {str(e)}", exc_info=True)
            return ResponseFormatter.error_response(
                'Có lỗi xảy ra khi submit giải trình',
                ResponseFormatter.HTTP_INTERNAL_ERROR
            )

    @http.route('/api/v1/attendance-excuse/update', type='http', auth='none', methods=['POST'], csrf=False)
    @_verify_token_http
    def update_excuse(self):
        """
        Cập nhật giải trình chấm công (chỉ khi ở trạng thái draft)
        """
        try:
            data = _get_json_data()
            excuse_id = data.get('excuse_id')
            
            if not excuse_id:
                return ResponseFormatter.error_response(
                    'excuse_id là bắt buộc',
                    ResponseFormatter.HTTP_BAD_REQUEST
                )

            jwt_payload = getattr(request, 'jwt_payload', {})
            user_id = jwt_payload.get('user_id')
            db_name = jwt_payload.get('db')

            if not db_name:
                return ResponseFormatter.error_response(
                    'Token không chứa thông tin database',
                    ResponseFormatter.HTTP_BAD_REQUEST
                )

            import odoo
            from odoo.modules.registry import Registry

            registry = Registry(db_name)
            with registry.cursor() as cr:
                env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
                
                try:
                    # Lấy excuse
                    excuse = env['attendance.excuse'].sudo().browse(excuse_id)
                    if not excuse.exists():
                        return ResponseFormatter.error_response('Không tìm thấy giải trình', ResponseFormatter.HTTP_NOT_FOUND)

                    # Kiểm tra permission trước khi update
                    current_user = env['res.users'].browse(user_id)
                    if not current_user.exists():
                        raise UserError('User không tồn tại')

                    current_employee = current_user.employee_id
                    can_edit = (current_user.has_group('base.group_system') or
                               current_user.has_group('hr.group_hr_manager') or
                               (current_employee and current_employee.id == excuse.employee_id.id))

                    if not can_edit:
                        raise UserError('Không có quyền sửa giải trình này')

                    if excuse.state != 'draft':
                        raise UserError('Chỉ có thể sửa giải trình ở trạng thái draft')

                    # Chuẩn bị dữ liệu update
                    update_data = {}
                    if 'reason' in data:
                        update_data['reason'] = data['reason']
                    if 'requested_checkin' in data:
                        update_data['requested_checkin'] = data['requested_checkin']
                    if 'requested_checkout' in data:
                        update_data['requested_checkout'] = data['requested_checkout']

                    if update_data:
                        excuse.write(update_data)

                    # Format response
                    result = excuse.api_get_excuse_detail(user_id)
                    cr.commit()
                    
                    return ResponseFormatter.success_response('Cập nhật giải trình thành công', result)
                
                except Exception as e:
                    cr.rollback()
                    _logger.error(f"Error updating excuse: {str(e)}", exc_info=True)
                    return ResponseFormatter.error_response(f'Lỗi: {str(e)}', ResponseFormatter.HTTP_INTERNAL_ERROR)

        except Exception as e:
            _logger.error(f"Error in update_excuse: {str(e)}", exc_info=True)
            return ResponseFormatter.error_response(
                'Có lỗi xảy ra khi cập nhật giải trình',
                ResponseFormatter.HTTP_INTERNAL_ERROR
            )

    @http.route('/api/v1/attendance-excuse/delete', type='http', auth='none', methods=['POST'], csrf=False)
    @_verify_token_http
    def delete_excuse(self):
        """
        Xóa giải trình chấm công (chỉ khi ở trạng thái draft)
        """
        try:
            data = _get_json_data()
            excuse_id = data.get('excuse_id')
            
            if not excuse_id:
                return ResponseFormatter.error_response(
                    'excuse_id là bắt buộc',
                    ResponseFormatter.HTTP_BAD_REQUEST
                )

            jwt_payload = getattr(request, 'jwt_payload', {})
            user_id = jwt_payload.get('user_id')
            db_name = jwt_payload.get('db')

            if not db_name:
                return ResponseFormatter.error_response(
                    'Token không chứa thông tin database',
                    ResponseFormatter.HTTP_BAD_REQUEST
                )

            import odoo
            from odoo.modules.registry import Registry

            registry = Registry(db_name)
            with registry.cursor() as cr:
                env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
                
                try:
                    # Lấy excuse
                    excuse = env['attendance.excuse'].sudo().browse(excuse_id)
                    if not excuse.exists():
                        return ResponseFormatter.error_response('Không tìm thấy giải trình', ResponseFormatter.HTTP_NOT_FOUND)

                    # Kiểm tra permission
                    current_user = env['res.users'].browse(user_id)
                    if not current_user.exists():
                        raise UserError('User không tồn tại')

                    current_employee = current_user.employee_id
                    can_delete = (current_user.has_group('base.group_system') or
                                 current_user.has_group('hr.group_hr_manager') or
                                 (current_employee and current_employee.id == excuse.employee_id.id))

                    if not can_delete:
                        raise UserError('Không có quyền xóa giải trình này')

                    if excuse.state != 'draft':
                        raise UserError('Chỉ có thể xóa giải trình ở trạng thái draft')

                    # Xóa excuse
                    excuse.unlink()
                    cr.commit()
                    
                    return ResponseFormatter.success_response('Xóa giải trình thành công', {'deleted': True})
                
                except Exception as e:
                    cr.rollback()
                    _logger.error(f"Error deleting excuse: {str(e)}", exc_info=True)
                    return ResponseFormatter.error_response(f'Lỗi: {str(e)}', ResponseFormatter.HTTP_INTERNAL_ERROR)

        except Exception as e:
            _logger.error(f"Error in delete_excuse: {str(e)}", exc_info=True)
            return ResponseFormatter.error_response(
                'Có lỗi xảy ra khi xóa giải trình',
                ResponseFormatter.HTTP_INTERNAL_ERROR
            )

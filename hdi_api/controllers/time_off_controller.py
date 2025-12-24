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

                # Lấy danh sách loại nghỉ
                leave_types = env['hr.leave.type'].sudo().search([
                    ('active', '=', True)
                ], order='name')

                types_data = []
                for leave_type in leave_types:
                    types_data.append({
                        'id': leave_type.id,
                        'name': leave_type.name,
                    })

                return ResponseFormatter.success_response('Lấy danh sách loại nghỉ thành công', types_data)

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

                current_user = env['res.users'].sudo().search([('id', '=', user_id)], limit=1)
                if not current_user:
                    return ResponseFormatter.error_response('User không tồn tại', ResponseFormatter.HTTP_UNAUTHORIZED)

                employee = current_user.employee_id
                if not employee:
                    return ResponseFormatter.error_response('User không phải là nhân viên', ResponseFormatter.HTTP_FORBIDDEN)

                leave_types = env['hr.leave.type'].sudo().search([('active', '=', True)])
                remaining_days = []

                for leave_type in leave_types:
                    allocation = env['hr.leave.allocation'].sudo().search([
                        ('employee_id', '=', employee.id),
                        ('holiday_status_id', '=', leave_type.id),
                        ('state', '=', 'validate'),
                    ], order='date_from desc', limit=1)

                    if allocation:
                        used_leaves = env['hr.leave'].sudo().search_count([
                            ('employee_id', '=', employee.id),
                            ('holiday_status_id', '=', leave_type.id),
                            ('state', '=', 'validate'),
                            ('date_from', '>=', allocation.date_from),
                        ])
                        remaining = allocation.number_of_days - used_leaves
                    else:
                        remaining = 0

                    remaining_days.append({
                        'leave_type_id': leave_type.id,
                        'leave_type_name': leave_type.name,
                        'remaining_days': remaining,
                    })

                return ResponseFormatter.success_response('Lấy số ngày phép còn lại thành công', {
                    'employee_id': employee.id,
                    'employee_name': employee.name,
                    'remaining_days': remaining_days
                })

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

                # Lấy thông tin user hiện tại
                current_user = env['res.users'].sudo().search([('id', '=', user_id)], limit=1)
                if not current_user:
                    return ResponseFormatter.error_response('User không tồn tại', ResponseFormatter.HTTP_UNAUTHORIZED)

                current_employee = current_user.employee_id

                # Build domain
                domain = []

                # Nếu không phải HR/Admin, chỉ xem được đơn của chính mình
                if not (current_user.has_group('base.group_system') or current_user.has_group('hr.group_hr_manager')):
                    if current_employee:
                        domain.append(('employee_id', '=', current_employee.id))
                    else:
                        return ResponseFormatter.error_response('User không phải là nhân viên', ResponseFormatter.HTTP_FORBIDDEN)

                if state:
                    domain.append(('state', '=', state))

                # Lấy danh sách leave
                leaves = env['hr.leave'].sudo().search(domain, limit=limit, offset=offset, order='date_from desc')
                total_count = env['hr.leave'].sudo().search_count(domain)

                leaves_data = []
                for leave in leaves:
                    leaves_data.append({
                        'id': leave.id,
                        'employee_id': leave.employee_id.id,
                        'employee_name': leave.employee_id.name,
                        'leave_type': leave.holiday_status_id.name,
                        'date_from': leave.date_from.isoformat() if leave.date_from else None,
                        'date_to': leave.date_to.isoformat() if leave.date_to else None,
                        'number_of_days': leave.number_of_days,
                        'state': leave.state,
                    })

                return ResponseFormatter.success_response('Lấy danh sách đơn xin nghỉ thành công', {
                    'leaves': leaves_data,
                    'total_count': total_count,
                    'limit': limit,
                    'offset': offset,
                })

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

                # Lấy thông tin user hiện tại
                current_user = env['res.users'].sudo().search([('id', '=', user_id)], limit=1)
                if not current_user:
                    return ResponseFormatter.error_response('User không tồn tại', ResponseFormatter.HTTP_UNAUTHORIZED)

                # Lấy leave
                leave = env['hr.leave'].sudo().search([('id', '=', leave_id)], limit=1)
                if not leave:
                    return ResponseFormatter.error_response('Không tìm thấy đơn xin nghỉ', ResponseFormatter.HTTP_NOT_FOUND)

                # Kiểm tra quyền - chỉ xem được của chính mình hoặc nếu là HR/Admin
                current_employee = current_user.employee_id
                can_view = (current_user.has_group('base.group_system') or
                           current_user.has_group('hr.group_hr_manager') or
                           (current_employee and current_employee.id == leave.employee_id.id))

                if not can_view:
                    return ResponseFormatter.error_response('Không có quyền xem thông tin này', ResponseFormatter.HTTP_FORBIDDEN)

                # Format dữ liệu
                leave_data = {
                    'id': leave.id,
                    'employee_id': leave.employee_id.id,
                    'employee_name': leave.employee_id.name,
                    'leave_type': leave.holiday_status_id.name,
                    'date_from': leave.date_from.isoformat() if leave.date_from else None,
                    'date_to': leave.date_to.isoformat() if leave.date_to else None,
                    'number_of_days': leave.number_of_days,
                    'state': leave.state,
                    'name': leave.name or '',
                }

                return ResponseFormatter.success_response('Lấy thông tin chi tiết đơn xin nghỉ thành công', leave_data)

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

            # Kiểm tra dữ liệu bắt buộc
            required_fields = ['holiday_status_id', 'date_from', 'date_to']
            for field in required_fields:
                if field not in data or not data[field]:
                    return ResponseFormatter.error_response(f'{field} là bắt buộc', ResponseFormatter.HTTP_BAD_REQUEST)

            import odoo
            from odoo.modules.registry import Registry

            registry = Registry(db_name)
            with registry.cursor() as cr:
                env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})

                # Lấy thông tin user hiện tại
                current_user = env['res.users'].sudo().search([('id', '=', user_id)], limit=1)
                if not current_user:
                    return ResponseFormatter.error_response('User không tồn tại', ResponseFormatter.HTTP_UNAUTHORIZED)

                current_employee = current_user.employee_id
                if not current_employee:
                    return ResponseFormatter.error_response('User không phải là nhân viên', ResponseFormatter.HTTP_FORBIDDEN)

                # Kiểm tra employee_id - cho phép tạo cho chính mình hoặc nếu là HR/Admin
                employee_id = data.get('employee_id', current_employee.id)
                if employee_id != current_employee.id:
                    if not (current_user.has_group('base.group_system') or current_user.has_group('hr.group_hr_manager')):
                        return ResponseFormatter.error_response('Không có quyền tạo đơn cho nhân viên khác', ResponseFormatter.HTTP_FORBIDDEN)

                # Validate employee
                employee = env['hr.employee'].sudo().search([('id', '=', employee_id)], limit=1)
                if not employee:
                    return ResponseFormatter.error_response('Không tìm thấy nhân viên', ResponseFormatter.HTTP_NOT_FOUND)

                # Validate leave type
                leave_type = env['hr.leave.type'].sudo().search([('id', '=', data['holiday_status_id'])], limit=1)
                if not leave_type:
                    return ResponseFormatter.error_response('Không tìm thấy loại nghỉ', ResponseFormatter.HTTP_NOT_FOUND)

                # Tạo leave
                try:
                    leave = env['hr.leave'].sudo().create({
                        'employee_id': employee_id,
                        'holiday_status_id': data['holiday_status_id'],
                        'date_from': data['date_from'],
                        'date_to': data['date_to'],
                        'name': data.get('name', ''),
                    })
                    cr.commit()

                    return ResponseFormatter.success_response('Tạo đơn xin nghỉ thành công', {
                        'id': leave.id,
                        'employee_id': leave.employee_id.id,
                        'leave_type': leave.holiday_status_id.name,
                        'date_from': leave.date_from.isoformat() if leave.date_from else None,
                        'date_to': leave.date_to.isoformat() if leave.date_to else None,
                        'state': leave.state,
                    })

                except Exception as e:
                    cr.rollback()
                    _logger.error(f"Error creating leave: {str(e)}", exc_info=True)
                    return ResponseFormatter.error_response(f'Lỗi khi tạo đơn xin nghỉ: {str(e)}', ResponseFormatter.HTTP_INTERNAL_ERROR)

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

                # Lấy thông tin user hiện tại
                current_user = env['res.users'].sudo().search([('id', '=', user_id)], limit=1)
                if not current_user:
                    return ResponseFormatter.error_response('User không tồn tại', ResponseFormatter.HTTP_UNAUTHORIZED)

                current_employee = current_user.employee_id

                # Lấy leave
                leave = env['hr.leave'].sudo().search([('id', '=', leave_id)], limit=1)
                if not leave:
                    return ResponseFormatter.error_response('Không tìm thấy đơn xin nghỉ', ResponseFormatter.HTTP_NOT_FOUND)

                # Kiểm tra quyền - chỉ sửa được của chính mình hoặc nếu là HR/Admin
                can_edit = (current_user.has_group('base.group_system') or
                           current_user.has_group('hr.group_hr_manager') or
                           (current_employee and current_employee.id == leave.employee_id.id))

                if not can_edit:
                    return ResponseFormatter.error_response('Không có quyền sửa đơn này', ResponseFormatter.HTTP_FORBIDDEN)

                # Chỉ cho sửa khi trạng thái là draft
                if leave.state != 'draft':
                    return ResponseFormatter.error_response('Chỉ có thể sửa đơn ở trạng thái nháp', ResponseFormatter.HTTP_BAD_REQUEST)

                # Chuẩn bị dữ liệu update
                update_data = {}
                if 'date_from' in data:
                    update_data['date_from'] = data['date_from']
                if 'date_to' in data:
                    update_data['date_to'] = data['date_to']
                if 'holiday_status_id' in data:
                    update_data['holiday_status_id'] = data['holiday_status_id']
                if 'name' in data:
                    update_data['name'] = data['name']

                if not update_data:
                    return ResponseFormatter.error_response('Không có dữ liệu để sửa', ResponseFormatter.HTTP_BAD_REQUEST)

                # Cập nhật leave
                try:
                    leave.sudo().write(update_data)
                    cr.commit()

                    return ResponseFormatter.success_response('Cập nhật đơn xin nghỉ thành công', {
                        'id': leave.id,
                        'employee_id': leave.employee_id.id,
                        'leave_type': leave.holiday_status_id.name,
                        'date_from': leave.date_from.isoformat() if leave.date_from else None,
                        'date_to': leave.date_to.isoformat() if leave.date_to else None,
                        'state': leave.state,
                    })

                except Exception as e:
                    cr.rollback()
                    _logger.error(f"Error updating leave: {str(e)}", exc_info=True)
                    return ResponseFormatter.error_response(f'Lỗi khi cập nhật đơn xin nghỉ: {str(e)}', ResponseFormatter.HTTP_INTERNAL_ERROR)

        except Exception as e:
            _logger.error(f"Error in update_leave: {str(e)}", exc_info=True)
            return ResponseFormatter.error_response('Có lỗi xảy ra khi cập nhật đơn xin nghỉ', ResponseFormatter.HTTP_INTERNAL_ERROR)

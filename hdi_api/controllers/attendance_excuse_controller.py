import json
import logging
from datetime import datetime, timedelta

from odoo import http
from odoo.http import request
from odoo.exceptions import UserError, ValidationError

from .auth_controller import _verify_token_http
from ..utils.response_formatter import ResponseFormatter

_logger = logging.getLogger(__name__)


class MobileAppAttendanceExcuseAPI(http.Controller):

    @http.route('/api/v1/attendance-excuse/create', type='http', auth='none', methods=['POST'], csrf=False)
    @_verify_token_http
    def create_excuse(self):
        """
        Tạo giải trình chấm công mới
        
        Request body:
        {
            "attendance_id": int,          # ID bản ghi chấm công (bắt buộc)
            "excuse_type": str,            # "late_or_early" hoặc "missing_checkin_out" (bắt buộc)
            "reason": str,                 # Lý do giải trình (không bắt buộc)
            "requested_checkin": datetime, # Giờ check-in yêu cầu sửa (không bắt buộc)
            "requested_checkout": datetime # Giờ check-out yêu cầu sửa (không bắt buộc)
        }
        """
        try:
            # Lấy dữ liệu từ request
            try:
                data = json.loads(request.httprequest.data.decode('utf-8'))
            except Exception:
                data = request.POST.to_dict()

            attendance_id = data.get('attendance_id')
            excuse_type = data.get('excuse_type')
            reason = data.get('reason', '')
            requested_checkin = data.get('requested_checkin')
            requested_checkout = data.get('requested_checkout')

            # Kiểm tra dữ liệu bắt buộc
            if not attendance_id:
                return ResponseFormatter.error_response(
                    'attendance_id là bắt buộc',
                    ResponseFormatter.HTTP_BAD_REQUEST
                )

            if not excuse_type or excuse_type not in ['late_or_early', 'missing_checkin_out']:
                return ResponseFormatter.error_response(
                    'excuse_type phải là "late_or_early" hoặc "missing_checkin_out"',
                    ResponseFormatter.HTTP_BAD_REQUEST
                )

            # Lấy thông tin người dùng từ token
            user_id = request.jwt_payload.get('user_id')
            db_name = request.jwt_payload.get('db')

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
                
                # Lấy user và employee
                user = env['res.users'].browse(user_id)
                if not user.exists():
                    return ResponseFormatter.error_response(
                        'Người dùng không tồn tại',
                        ResponseFormatter.HTTP_NOT_FOUND
                    )

                # Lấy employee từ user
                employee = env['hr.employee'].search([
                    ('user_id', '=', user.id)
                ], limit=1)

                if not employee:
                    return ResponseFormatter.error_response(
                        'Không tìm thấy thông tin nhân viên',
                        ResponseFormatter.HTTP_NOT_FOUND
                    )

                # Kiểm tra attendance_id có tồn tại và thuộc về nhân viên này không
                attendance = env['hr.attendance'].browse(int(attendance_id))
                if not attendance.exists():
                    return ResponseFormatter.error_response(
                        'Bản ghi chấm công không tồn tại',
                        ResponseFormatter.HTTP_NOT_FOUND
                    )

                if attendance.employee_id.id != employee.id:
                    return ResponseFormatter.error_response(
                        'Bản ghi chấm công không thuộc về nhân viên này',
                        ResponseFormatter.HTTP_FORBIDDEN
                    )

                # Kiểm tra giải trình đã tồn tại chưa
                existing_excuse = env['attendance.excuse'].search([
                    ('attendance_id', '=', attendance.id),
                    ('excuse_type', '=', excuse_type),
                    ('state', 'in', ['draft', 'submitted', 'approved'])
                ], limit=1)

                if existing_excuse:
                    return ResponseFormatter.error_response(
                        f'Giải trình {excuse_type} cho bản ghi này đã tồn tại',
                        ResponseFormatter.HTTP_BAD_REQUEST
                    )

                try:
                    # Tạo giải trình mới
                    excuse_values = {
                        'attendance_id': attendance.id,
                        'excuse_type': excuse_type,
                        'reason': reason,
                        'state': 'draft',
                    }

                    # Nếu có requested_checkin/checkout, thêm vào
                    if requested_checkin:
                        try:
                            if isinstance(requested_checkin, str):
                                requested_checkin = datetime.fromisoformat(requested_checkin.replace('Z', '+00:00'))
                            excuse_values['requested_checkin'] = requested_checkin
                        except Exception as e:
                            _logger.warning(f"Invalid requested_checkin format: {str(e)}")

                    if requested_checkout:
                        try:
                            if isinstance(requested_checkout, str):
                                requested_checkout = datetime.fromisoformat(requested_checkout.replace('Z', '+00:00'))
                            excuse_values['requested_checkout'] = requested_checkout
                        except Exception as e:
                            _logger.warning(f"Invalid requested_checkout format: {str(e)}")

                    excuse = env['attendance.excuse'].create(excuse_values)
                    cr.commit()

                    excuse_data = {
                        'id': excuse.id,
                        'attendance_id': excuse.attendance_id.id,
                        'employee_id': excuse.employee_id.id,
                        'employee_name': excuse.employee_id.name,
                        'date': excuse.date.isoformat() if excuse.date else None,
                        'excuse_type': excuse.excuse_type,
                        'reason': excuse.reason,
                        'state': excuse.state,
                        'created_at': excuse.create_date.isoformat() if excuse.create_date else None,
                    }

                    return ResponseFormatter.success_response(
                        'Tạo giải trình thành công',
                        excuse_data
                    )

                except ValidationError as ve:
                    cr.rollback()
                    return ResponseFormatter.error_response(
                        str(ve),
                        ResponseFormatter.HTTP_BAD_REQUEST
                    )
                except Exception as e:
                    cr.rollback()
                    _logger.error(f"Error creating excuse: {str(e)}", exc_info=True)
                    return ResponseFormatter.error_response(
                        'Lỗi khi tạo giải trình',
                        ResponseFormatter.HTTP_INTERNAL_ERROR
                    )

        except Exception as e:
            _logger.error(f"Create excuse error: {str(e)}", exc_info=True)
            return ResponseFormatter.error_response(
                'Lỗi server khi xử lý yêu cầu',
                ResponseFormatter.HTTP_INTERNAL_ERROR
            )

    @http.route('/api/v1/attendance-excuse/get', type='http', auth='none', methods=['POST'], csrf=False)
    @_verify_token_http
    def get_excuse(self):
        """
        Lấy chi tiết giải trình chấm công
        Request body:
        {
            "excuse_id": int
        }
        """
        try:
            # Lấy dữ liệu từ request body
            try:
                data = json.loads(request.httprequest.data.decode('utf-8'))
            except Exception:
                data = {}

            excuse_id = data.get('excuse_id')
            if not excuse_id:
                return ResponseFormatter.error_response(
                    'excuse_id là bắt buộc',
                    ResponseFormatter.HTTP_BAD_REQUEST
                )

            user_id = request.jwt_payload.get('user_id')
            db_name = request.jwt_payload.get('db')

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

                # Lấy user và employee
                user = env['res.users'].browse(user_id)
                if not user.exists():
                    return ResponseFormatter.error_response(
                        'Người dùng không tồn tại',
                        ResponseFormatter.HTTP_NOT_FOUND
                    )

                employee = env['hr.employee'].search([
                    ('user_id', '=', user.id)
                ], limit=1)

                # Lấy giải trình
                excuse = env['attendance.excuse'].browse(excuse_id)
                if not excuse.exists():
                    return ResponseFormatter.error_response(
                        'Giải trình không tồn tại',
                        ResponseFormatter.HTTP_NOT_FOUND
                    )

                # Kiểm tra quyền: user chỉ xem được giải trình của mình hoặc HR Manager
                if employee and excuse.employee_id.id != employee.id:
                    if not user.has_group('hr.group_hr_manager'):
                        return ResponseFormatter.error_response(
                            'Bạn không có quyền xem giải trình này',
                            ResponseFormatter.HTTP_FORBIDDEN
                        )

                # Chuẩn bị dữ liệu trả về
                excuse_data = {
                    'id': excuse.id,
                    'attendance_id': excuse.attendance_id.id,
                    'employee_id': excuse.employee_id.id,
                    'employee_name': excuse.employee_id.name,
                    'date': excuse.date.isoformat() if excuse.date else None,
                    'excuse_type': excuse.excuse_type,
                    'reason': excuse.reason,
                    'state': excuse.state,
                    'original_checkin': excuse.original_checkin.isoformat() if excuse.original_checkin else None,
                    'original_checkout': excuse.original_checkout.isoformat() if excuse.original_checkout else None,
                    'requested_checkin': excuse.requested_checkin.isoformat() if excuse.requested_checkin else None,
                    'requested_checkout': excuse.requested_checkout.isoformat() if excuse.requested_checkout else None,
                    'corrected_checkin': excuse.corrected_checkin.isoformat() if excuse.corrected_checkin else None,
                    'corrected_checkout': excuse.corrected_checkout.isoformat() if excuse.corrected_checkout else None,
                    'late_minutes': excuse.late_minutes,
                    'early_minutes': excuse.early_minutes,
                    'approver_id': excuse.approver_id.id if excuse.approver_id else None,
                    'approver_name': excuse.approver_id.name if excuse.approver_id else None,
                    'approval_date': excuse.approval_date.isoformat() if excuse.approval_date else None,
                    'rejection_reason': excuse.rejection_reason,
                    'notes': excuse.notes,
                    'created_at': excuse.create_date.isoformat() if excuse.create_date else None,
                    'updated_at': excuse.write_date.isoformat() if excuse.write_date else None,
                    'can_approve': excuse.can_approve,
                    'can_reject': excuse.can_reject,
                    'is_approver': excuse.is_approver,
                }

                return ResponseFormatter.success_response(
                    'Lấy thông tin giải trình thành công',
                    excuse_data
                )

        except Exception as e:
            _logger.error(f"Get excuse error: {str(e)}", exc_info=True)
            return ResponseFormatter.error_response(
                'Lỗi server khi xử lý yêu cầu',
                ResponseFormatter.HTTP_INTERNAL_ERROR
            )

    @http.route('/api/v1/attendance-excuse/list', type='http', auth='none', methods=['POST'], csrf=False)
    @_verify_token_http
    def list_excuses(self):
        """
        Lấy danh sách giải trình chấm công của user
        
        Request body:
        {
            "state": "draft",      # draft, submitted, approved, rejected (không bắt buộc)
            "limit": 50,           # số lượng bản ghi (mặc định: 50)
            "offset": 0            # số lượng bỏ qua (mặc định: 0)
        }
        """
        try:
            user_id = request.jwt_payload.get('user_id')
            db_name = request.jwt_payload.get('db')

            if not db_name:
                return ResponseFormatter.error_response(
                    'Token không chứa thông tin database',
                    ResponseFormatter.HTTP_BAD_REQUEST
                )

            # Lấy dữ liệu từ request body
            try:
                data = json.loads(request.httprequest.data.decode('utf-8'))
            except Exception:
                data = {}

            state_filter = data.get('state', '')
            limit = int(data.get('limit', 50))
            offset = int(data.get('offset', 0))

            import odoo
            from odoo.modules.registry import Registry

            registry = Registry(db_name)
            with registry.cursor() as cr:
                env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})

                # Lấy user và employee
                user = env['res.users'].browse(user_id)
                if not user.exists():
                    return ResponseFormatter.error_response(
                        'Người dùng không tồn tại',
                        ResponseFormatter.HTTP_NOT_FOUND
                    )

                employee = env['hr.employee'].search([
                    ('user_id', '=', user.id)
                ], limit=1)

                if not employee:
                    return ResponseFormatter.error_response(
                        'Không tìm thấy thông tin nhân viên',
                        ResponseFormatter.HTTP_NOT_FOUND
                    )

                # Xây dựng domain search
                domain = [('employee_id', '=', employee.id)]

                # Lọc theo state nếu được chỉ định
                if state_filter and state_filter in ['draft', 'submitted', 'approved', 'rejected']:
                    domain.append(('state', '=', state_filter))

                # Tìm giải trình
                excuses = env['attendance.excuse'].search(
                    domain,
                    order='date desc',
                    limit=limit,
                    offset=offset
                )

                # Tính tổng số bản ghi
                total_count = env['attendance.excuse'].search_count(domain)

                # Chuẩn bị dữ liệu trả về
                excuses_data = []
                for excuse in excuses:
                    excuse_data = {
                        'id': excuse.id,
                        'attendance_id': excuse.attendance_id.id,
                        'employee_id': excuse.employee_id.id,
                        'employee_name': excuse.employee_id.name,
                        'date': excuse.date.isoformat() if excuse.date else None,
                        'excuse_type': excuse.excuse_type,
                        'reason': excuse.reason,
                        'state': excuse.state,
                        'original_checkin': excuse.original_checkin.isoformat() if excuse.original_checkin else None,
                        'original_checkout': excuse.original_checkout.isoformat() if excuse.original_checkout else None,
                        'requested_checkin': excuse.requested_checkin.isoformat() if excuse.requested_checkin else None,
                        'requested_checkout': excuse.requested_checkout.isoformat() if excuse.requested_checkout else None,
                        'late_minutes': excuse.late_minutes,
                        'early_minutes': excuse.early_minutes,
                        'approver_id': excuse.approver_id.id if excuse.approver_id else None,
                        'approver_name': excuse.approver_id.name if excuse.approver_id else None,
                        'approval_date': excuse.approval_date.isoformat() if excuse.approval_date else None,
                        'created_at': excuse.create_date.isoformat() if excuse.create_date else None,
                        'updated_at': excuse.write_date.isoformat() if excuse.write_date else None,
                    }
                    excuses_data.append(excuse_data)

                response_data = {
                    'total_count': total_count,
                    'limit': limit,
                    'offset': offset,
                    'data': excuses_data
                }

                return ResponseFormatter.success_response(
                    'Lấy danh sách giải trình thành công',
                    response_data
                )

        except Exception as e:
            _logger.error(f"List excuses error: {str(e)}", exc_info=True)
            return ResponseFormatter.error_response(
                'Lỗi server khi xử lý yêu cầu',
                ResponseFormatter.HTTP_INTERNAL_ERROR
            )

    @http.route('/api/v1/attendance-excuse/submit', type='http', auth='none', methods=['POST'], csrf=False)
    @_verify_token_http
    def submit_excuse(self):
        """
        Gửi giải trình chấm công (từ trạng thái draft -> submitted)
        Request body:
        {
            "excuse_id": int
        }
        """
        try:
            # Lấy dữ liệu từ request body
            try:
                data = json.loads(request.httprequest.data.decode('utf-8'))
            except Exception:
                data = {}

            excuse_id = data.get('excuse_id')
            if not excuse_id:
                return ResponseFormatter.error_response(
                    'excuse_id là bắt buộc',
                    ResponseFormatter.HTTP_BAD_REQUEST
                )

            user_id = request.jwt_payload.get('user_id')
            db_name = request.jwt_payload.get('db')

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

                # Lấy user và employee
                user = env['res.users'].browse(user_id)
                if not user.exists():
                    return ResponseFormatter.error_response(
                        'Người dùng không tồn tại',
                        ResponseFormatter.HTTP_NOT_FOUND
                    )

                employee = env['hr.employee'].search([
                    ('user_id', '=', user.id)
                ], limit=1)

                # Lấy giải trình
                excuse = env['attendance.excuse'].browse(excuse_id)
                if not excuse.exists():
                    return ResponseFormatter.error_response(
                        'Giải trình không tồn tại',
                        ResponseFormatter.HTTP_NOT_FOUND
                    )

                # Kiểm tra quyền
                if employee and excuse.employee_id.id != employee.id:
                    return ResponseFormatter.error_response(
                        'Bạn không có quyền cập nhật giải trình này',
                        ResponseFormatter.HTTP_FORBIDDEN
                    )

                # Kiểm tra trạng thái
                if excuse.state != 'draft':
                    return ResponseFormatter.error_response(
                        f'Giải trình phải ở trạng thái draft, hiện tại là {excuse.state}',
                        ResponseFormatter.HTTP_BAD_REQUEST
                    )

                try:
                    # Gửi giải trình
                    excuse.action_submit()
                    cr.commit()

                    excuse_data = {
                        'id': excuse.id,
                        'state': excuse.state,
                        'approver_id': excuse.approver_id.id if excuse.approver_id else None,
                        'approver_name': excuse.approver_id.name if excuse.approver_id else None,
                    }

                    return ResponseFormatter.success_response(
                        'Gửi giải trình thành công',
                        excuse_data
                    )

                except ValidationError as ve:
                    cr.rollback()
                    return ResponseFormatter.error_response(
                        str(ve),
                        ResponseFormatter.HTTP_BAD_REQUEST
                    )
                except Exception as e:
                    cr.rollback()
                    _logger.error(f"Error submitting excuse: {str(e)}", exc_info=True)
                    return ResponseFormatter.error_response(
                        'Lỗi khi gửi giải trình',
                        ResponseFormatter.HTTP_INTERNAL_ERROR
                    )

        except Exception as e:
            _logger.error(f"Submit excuse error: {str(e)}", exc_info=True)
            return ResponseFormatter.error_response(
                'Lỗi server khi xử lý yêu cầu',
                ResponseFormatter.HTTP_INTERNAL_ERROR
            )

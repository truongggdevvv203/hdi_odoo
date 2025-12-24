import logging
from datetime import datetime, timedelta

from odoo import http
from odoo.http import request
from odoo.exceptions import UserError

from .auth_controller import _verify_token
from ..utils.response_formatter import ResponseFormatter

_logger = logging.getLogger(__name__)


class AttendanceAPI(http.Controller):
    """API endpoints cho chức năng chấm công"""

    def _get_employee_from_user(self, env, user_id):
        """Lấy employee từ user_id trong environment"""
        employee = env['hr.employee'].search([
            ('user_id', '=', user_id)
        ], limit=1)

        if not employee:
            raise UserError('Không tìm thấy nhân viên liên kết với tài khoản này')
        
        return employee

    @http.route('/api/v1/attendance/check-in', type='http', auth='none', methods=['POST'], csrf=False)
    @_verify_token
    def check_in(self):
        """Chấm công vào"""
        try:
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

                try:
                    # Lấy employee và thực hiện check-in (logic trong model)
                    employee = self._get_employee_from_user(env, user_id)
                    result = env['hr.attendance'].api_check_in(employee.id)
                    
                    cr.commit()
                    
                    return ResponseFormatter.success_response(
                        'Chấm công vào thành công',
                        result,
                        ResponseFormatter.HTTP_OK
                    )

                except UserError as ue:
                    cr.rollback()
                    return ResponseFormatter.error_response(
                        str(ue),
                        ResponseFormatter.HTTP_BAD_REQUEST
                    )
                except Exception as e:
                    cr.rollback()
                    _logger.error(f"Check-in error: {str(e)}", exc_info=True)
                    return ResponseFormatter.error_response(
                        f'Lỗi khi chấm công vào: {str(e)}',
                        ResponseFormatter.HTTP_INTERNAL_ERROR
                    )

        except Exception as e:
            _logger.error(f"Check-in error: {str(e)}", exc_info=True)
            return ResponseFormatter.error_response(
                f'Lỗi khi chấm công vào: {str(e)}',
                ResponseFormatter.HTTP_INTERNAL_ERROR
            )

    @http.route('/api/v1/attendance/check-out', type='http', auth='none', methods=['POST'], csrf=False)
    @_verify_token
    def check_out(self):
        """Chấm công ra"""
        try:
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

                try:
                    # Lấy employee và thực hiện check-out (logic trong model)
                    employee = self._get_employee_from_user(env, user_id)
                    result = env['hr.attendance'].api_check_out(employee.id)
                    
                    cr.commit()
                    
                    return ResponseFormatter.success_response(
                        'Chấm công ra thành công',
                        result,
                        ResponseFormatter.HTTP_OK
                    )

                except UserError as ue:
                    cr.rollback()
                    return ResponseFormatter.error_response(
                        str(ue),
                        ResponseFormatter.HTTP_BAD_REQUEST
                    )
                except Exception as e:
                    cr.rollback()
                    _logger.error(f"Check-out error: {str(e)}", exc_info=True)
                    return ResponseFormatter.error_response(
                        f'Lỗi khi chấm công ra: {str(e)}',
                        ResponseFormatter.HTTP_INTERNAL_ERROR
                    )

        except Exception as e:
            _logger.error(f"Check-out error: {str(e)}", exc_info=True)
            return ResponseFormatter.error_response(
                f'Lỗi khi chấm công ra: {str(e)}',
                ResponseFormatter.HTTP_INTERNAL_ERROR
            )

    @http.route('/api/v1/attendance/status', type='http', auth='none', methods=['GET'], csrf=False)
    @_verify_token
    def get_status(self):
        """Lấy trạng thái chấm công hiện tại"""
        try:
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

                # Lấy employee
                employee = env['hr.employee'].sudo().search([
                    ('user_id', '=', user_id)
                ], limit=1)

                if not employee:
                    return ResponseFormatter.error_response(
                        'Không tìm thấy nhân viên liên kết với tài khoản này',
                        ResponseFormatter.HTTP_NOT_FOUND
                    )

                # Kiểm tra có đang check-in không
                current_attendance = env['hr.attendance'].sudo().search([
                    ('employee_id', '=', employee.id),
                    ('check_out', '=', False)
                ], limit=1)

                if current_attendance:
                    return ResponseFormatter.success_response(
                        'Trạng thái chấm công',
                        {
                            'is_checked_in': True,
                            'attendance_id': current_attendance.id,
                            'check_in': current_attendance.check_in.isoformat() if current_attendance.check_in else None,
                            'employee_name': employee.name,
                        },
                        ResponseFormatter.HTTP_OK
                    )
                else:
                    return ResponseFormatter.success_response(
                        'Trạng thái chấm công',
                        {
                            'is_checked_in': False,
                            'employee_name': employee.name,
                        },
                        ResponseFormatter.HTTP_OK
                    )

        except Exception as e:
            _logger.error(f"Get status error: {str(e)}", exc_info=True)
            return ResponseFormatter.error_response(
                f'Lỗi khi lấy trạng thái: {str(e)}',
                ResponseFormatter.HTTP_INTERNAL_ERROR
            )

    @http.route('/api/v1/attendance/history', type='http', auth='none', methods=['GET'], csrf=False)
    @_verify_token
    def get_history(self):
        """Lấy lịch sử chấm công"""
        try:
            user_id = request.jwt_payload.get('user_id')
            db_name = request.jwt_payload.get('db')

            # Lấy params từ query string
            limit = int(request.httprequest.args.get('limit', 30))
            offset = int(request.httprequest.args.get('offset', 0))
            from_date = request.httprequest.args.get('from_date')  # Format: YYYY-MM-DD
            to_date = request.httprequest.args.get('to_date')  # Format: YYYY-MM-DD

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

                # Lấy employee
                employee = env['hr.employee'].sudo().search([
                    ('user_id', '=', user_id)
                ], limit=1)

                if not employee:
                    return ResponseFormatter.error_response(
                        'Không tìm thấy nhân viên liên kết với tài khoản này',
                        ResponseFormatter.HTTP_NOT_FOUND
                    )

                # Build domain
                domain = [('employee_id', '=', employee.id)]

                if from_date:
                    try:
                        from_datetime = datetime.strptime(from_date, '%Y-%m-%d')
                        domain.append(('check_in', '>=', from_datetime))
                    except ValueError:
                        return ResponseFormatter.error_response(
                            'Định dạng from_date không hợp lệ. Sử dụng YYYY-MM-DD',
                            ResponseFormatter.HTTP_BAD_REQUEST
                        )

                if to_date:
                    try:
                        to_datetime = datetime.strptime(to_date, '%Y-%m-%d') + timedelta(days=1)
                        domain.append(('check_in', '<', to_datetime))
                    except ValueError:
                        return ResponseFormatter.error_response(
                            'Định dạng to_date không hợp lệ. Sử dụng YYYY-MM-DD',
                            ResponseFormatter.HTTP_BAD_REQUEST
                        )

                # Lấy danh sách chấm công
                attendances = env['hr.attendance'].sudo().search(
                    domain,
                    limit=limit,
                    offset=offset,
                    order='check_in desc'
                )

                # Đếm tổng số bản ghi
                total_count = env['hr.attendance'].sudo().search_count(domain)

                # Format data
                attendance_list = []
                for att in attendances:
                    worked_hours = att.worked_hours if hasattr(att, 'worked_hours') else 0
                    attendance_list.append({
                        'id': att.id,
                        'check_in': att.check_in.isoformat() if att.check_in else None,
                        'check_out': att.check_out.isoformat() if att.check_out else None,
                        'worked_hours': worked_hours,
                    })

                return ResponseFormatter.success_response(
                    'Lịch sử chấm công',
                    {
                        'employee_name': employee.name,
                        'attendances': attendance_list,
                        'total_count': total_count,
                        'limit': limit,
                        'offset': offset,
                    },
                    ResponseFormatter.HTTP_OK
                )

        except Exception as e:
            _logger.error(f"Get history error: {str(e)}", exc_info=True)
            return ResponseFormatter.error_response(
                f'Lỗi khi lấy lịch sử: {str(e)}',
                ResponseFormatter.HTTP_INTERNAL_ERROR
            )

    @http.route('/api/v1/attendance/summary', type='http', auth='none', methods=['GET'], csrf=False)
    @_verify_token
    def get_summary(self):
        """Lấy tổng hợp chấm công theo tháng"""
        try:
            user_id = request.jwt_payload.get('user_id')
            db_name = request.jwt_payload.get('db')

            # Lấy params từ query string (YYYY-MM)
            month = request.httprequest.args.get('month')

            if not month:
                # Mặc định là tháng hiện tại
                month = datetime.now().strftime('%Y-%m')

            if not db_name:
                return ResponseFormatter.error_response(
                    'Token không chứa thông tin database',
                    ResponseFormatter.HTTP_BAD_REQUEST
                )

            try:
                year, month_num = map(int, month.split('-'))
                from_date = datetime(year, month_num, 1)

                # Tính ngày cuối tháng
                if month_num == 12:
                    to_date = datetime(year + 1, 1, 1)
                else:
                    to_date = datetime(year, month_num + 1, 1)
            except (ValueError, AttributeError):
                return ResponseFormatter.error_response(
                    'Định dạng month không hợp lệ. Sử dụng YYYY-MM',
                    ResponseFormatter.HTTP_BAD_REQUEST
                )

            import odoo
            from odoo.modules.registry import Registry

            registry = Registry(db_name)
            with registry.cursor() as cr:
                env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})

                # Lấy employee
                employee = env['hr.employee'].sudo().search([
                    ('user_id', '=', user_id)
                ], limit=1)

                if not employee:
                    return ResponseFormatter.error_response(
                        'Không tìm thấy nhân viên liên kết với tài khoản này',
                        ResponseFormatter.HTTP_NOT_FOUND
                    )

                # Lấy tất cả attendance trong tháng
                attendances = env['hr.attendance'].sudo().search([
                    ('employee_id', '=', employee.id),
                    ('check_in', '>=', from_date),
                    ('check_in', '<', to_date),
                ])

                # Tính toán
                total_days = 0
                total_hours = 0
                incomplete_days = 0

                for att in attendances:
                    if att.check_in:
                        total_days += 1
                        if att.check_out:
                            worked_hours = att.worked_hours if hasattr(att, 'worked_hours') else 0
                            total_hours += worked_hours
                        else:
                            incomplete_days += 1

                return ResponseFormatter.success_response(
                    'Tổng hợp chấm công',
                    {
                        'employee_name': employee.name,
                        'month': month,
                        'total_days': total_days,
                        'total_hours': round(total_hours, 2),
                        'incomplete_days': incomplete_days,
                        'average_hours_per_day': round(total_hours / total_days, 2) if total_days > 0 else 0,
                    },
                    ResponseFormatter.HTTP_OK
                )

        except Exception as e:
            _logger.error(f"Get summary error: {str(e)}", exc_info=True)
            return ResponseFormatter.error_response(
                f'Lỗi khi lấy tổng hợp: {str(e)}',
                ResponseFormatter.HTTP_INTERNAL_ERROR
            )

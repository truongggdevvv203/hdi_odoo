import json
import logging
from datetime import datetime, timedelta

from odoo import http
from odoo.http import request

from .auth_controller import _verify_token, _make_json_response

_logger = logging.getLogger(__name__)


class AttendanceAPI(http.Controller):
    """API endpoints cho chức năng chấm công"""

    def _get_employee_from_user(self, user_id, db_name):
        """Lấy employee từ user_id"""
        try:
            import odoo
            from odoo.modules.registry import Registry

            registry = Registry(db_name)
            with registry.cursor() as cr:
                env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
                employee = env['hr.employee'].sudo().search([
                    ('user_id', '=', user_id)
                ], limit=1)
                return employee
        except Exception as e:
            _logger.error(f"Error getting employee: {str(e)}", exc_info=True)
            return None

    @http.route('/api/v1/attendance/check-in', type='http', auth='none', methods=['POST'], csrf=False)
    @_verify_token
    def check_in(self):
        """Chấm công vào"""
        try:
            user_id = request.jwt_payload.get('user_id')
            db_name = request.jwt_payload.get('db')

            if not db_name:
                return _make_json_response({
                    'status': 'error',
                    'message': 'Token không chứa thông tin database'
                }, 400)

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
                    return _make_json_response({
                        'status': 'error',
                        'message': 'Không tìm thấy nhân viên liên kết với tài khoản này'
                    }, 404)

                # Kiểm tra xem đã check-in chưa
                last_attendance = env['hr.attendance'].sudo().search([
                    ('employee_id', '=', employee.id),
                    ('check_out', '=', False)
                ], limit=1)

                if last_attendance:
                    return _make_json_response({
                        'status': 'error',
                        'message': 'Bạn đã chấm công vào rồi. Vui lòng chấm công ra trước khi chấm công vào lại.',
                        'data': {
                            'check_in': last_attendance.check_in.isoformat() if last_attendance.check_in else None
                        }
                    }, 400)

                # Tạo bản ghi chấm công
                attendance = env['hr.attendance'].sudo().create({
                    'employee_id': employee.id,
                    'check_in': datetime.now(),
                })

                cr.commit()

                return _make_json_response({
                    'status': 'success',
                    'message': 'Chấm công vào thành công',
                    'data': {
                        'id': attendance.id,
                        'employee_id': employee.id,
                        'employee_name': employee.name,
                        'check_in': attendance.check_in.isoformat() if attendance.check_in else None,
                    }
                }, 200)

        except Exception as e:
            _logger.error(f"Check-in error: {str(e)}", exc_info=True)
            return _make_json_response({
                'status': 'error',
                'message': f'Lỗi khi chấm công vào: {str(e)}'
            }, 500)

    @http.route('/api/v1/attendance/check-out', type='http', auth='none', methods=['POST'], csrf=False)
    @_verify_token
    def check_out(self):
        """Chấm công ra"""
        try:
            user_id = request.jwt_payload.get('user_id')
            db_name = request.jwt_payload.get('db')

            if not db_name:
                return _make_json_response({
                    'status': 'error',
                    'message': 'Token không chứa thông tin database'
                }, 400)

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
                    return _make_json_response({
                        'status': 'error',
                        'message': 'Không tìm thấy nhân viên liên kết với tài khoản này'
                    }, 404)

                # Tìm bản ghi chấm công chưa check-out
                attendance = env['hr.attendance'].sudo().search([
                    ('employee_id', '=', employee.id),
                    ('check_out', '=', False)
                ], limit=1, order='check_in desc')

                if not attendance:
                    return _make_json_response({
                        'status': 'error',
                        'message': 'Không tìm thấy bản ghi chấm công vào. Vui lòng chấm công vào trước.'
                    }, 400)

                try:
                    # Kiểm tra và xóa overtime record cũ nếu tồn tại
                    attendance_date = attendance.check_in.date() if attendance.check_in else datetime.now().date()
                    old_overtime = env['hr.attendance.overtime'].sudo().search([
                        ('employee_id', '=', employee.id),
                        ('date', '=', str(attendance_date))
                    ])
                    if old_overtime:
                        old_overtime.sudo().unlink()

                    # Cập nhật check-out
                    attendance.sudo().write({
                        'check_out': datetime.now(),
                    })
                    cr.commit()
                except Exception as write_error:
                    _logger.warning(f"Check-out update warning: {str(write_error)}")
                    cr.rollback()

                    # Fallback: cập nhật trực tiếp database
                    try:
                        cr.execute(
                            "UPDATE hr_attendance SET check_out = %s WHERE id = %s",
                            (datetime.now(), attendance.id)
                        )
                        cr.commit()
                        _logger.info(f"Check-out successful via direct SQL for employee {employee.name}")
                    except Exception as e:
                        _logger.error(f"Check-out failed: {str(e)}", exc_info=True)
                        cr.rollback()
                        raise e

                # Tính thời gian làm việc
                worked_hours = attendance.worked_hours if hasattr(attendance, 'worked_hours') else 0

                return _make_json_response({
                    'status': 'success',
                    'message': 'Chấm công ra thành công',
                    'data': {
                        'id': attendance.id,
                        'employee_id': employee.id,
                        'employee_name': employee.name,
                        'check_in': attendance.check_in.isoformat() if attendance.check_in else None,
                        'check_out': attendance.check_out.isoformat() if attendance.check_out else None,
                        'worked_hours': worked_hours,
                    }
                }, 200)

        except Exception as e:
            _logger.error(f"Check-out error: {str(e)}", exc_info=True)
            return _make_json_response({
                'status': 'error',
                'message': f'Lỗi khi chấm công ra: {str(e)}'
            }, 500)

    @http.route('/api/v1/attendance/status', type='http', auth='none', methods=['GET'], csrf=False)
    @_verify_token
    def get_status(self):
        """Lấy trạng thái chấm công hiện tại"""
        try:
            user_id = request.jwt_payload.get('user_id')
            db_name = request.jwt_payload.get('db')

            if not db_name:
                return _make_json_response({
                    'status': 'error',
                    'message': 'Token không chứa thông tin database'
                }, 400)

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
                    return _make_json_response({
                        'status': 'error',
                        'message': 'Không tìm thấy nhân viên liên kết với tài khoản này'
                    }, 404)

                # Kiểm tra có đang check-in không
                current_attendance = env['hr.attendance'].sudo().search([
                    ('employee_id', '=', employee.id),
                    ('check_out', '=', False)
                ], limit=1)

                if current_attendance:
                    return _make_json_response({
                        'status': 'success',
                        'data': {
                            'is_checked_in': True,
                            'attendance_id': current_attendance.id,
                            'check_in': current_attendance.check_in.isoformat() if current_attendance.check_in else None,
                            'employee_name': employee.name,
                        }
                    }, 200)
                else:
                    return _make_json_response({
                        'status': 'success',
                        'data': {
                            'is_checked_in': False,
                            'employee_name': employee.name,
                        }
                    }, 200)

        except Exception as e:
            _logger.error(f"Get status error: {str(e)}", exc_info=True)
            return _make_json_response({
                'status': 'error',
                'message': f'Lỗi khi lấy trạng thái: {str(e)}'
            }, 500)

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
                return _make_json_response({
                    'status': 'error',
                    'message': 'Token không chứa thông tin database'
                }, 400)

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
                    return _make_json_response({
                        'status': 'error',
                        'message': 'Không tìm thấy nhân viên liên kết với tài khoản này'
                    }, 404)

                # Build domain
                domain = [('employee_id', '=', employee.id)]

                if from_date:
                    try:
                        from_datetime = datetime.strptime(from_date, '%Y-%m-%d')
                        domain.append(('check_in', '>=', from_datetime))
                    except ValueError:
                        return _make_json_response({
                            'status': 'error',
                            'message': 'Định dạng from_date không hợp lệ. Sử dụng YYYY-MM-DD'
                        }, 400)

                if to_date:
                    try:
                        to_datetime = datetime.strptime(to_date, '%Y-%m-%d') + timedelta(days=1)
                        domain.append(('check_in', '<', to_datetime))
                    except ValueError:
                        return _make_json_response({
                            'status': 'error',
                            'message': 'Định dạng to_date không hợp lệ. Sử dụng YYYY-MM-DD'
                        }, 400)

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

                return _make_json_response({
                    'status': 'success',
                    'data': {
                        'employee_name': employee.name,
                        'attendances': attendance_list,
                        'total_count': total_count,
                        'limit': limit,
                        'offset': offset,
                    }
                }, 200)

        except Exception as e:
            _logger.error(f"Get history error: {str(e)}", exc_info=True)
            return _make_json_response({
                'status': 'error',
                'message': f'Lỗi khi lấy lịch sử: {str(e)}'
            }, 500)

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
                return _make_json_response({
                    'status': 'error',
                    'message': 'Token không chứa thông tin database'
                }, 400)

            try:
                year, month_num = map(int, month.split('-'))
                from_date = datetime(year, month_num, 1)

                # Tính ngày cuối tháng
                if month_num == 12:
                    to_date = datetime(year + 1, 1, 1)
                else:
                    to_date = datetime(year, month_num + 1, 1)
            except (ValueError, AttributeError):
                return _make_json_response({
                    'status': 'error',
                    'message': 'Định dạng month không hợp lệ. Sử dụng YYYY-MM'
                }, 400)

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
                    return _make_json_response({
                        'status': 'error',
                        'message': 'Không tìm thấy nhân viên liên kết với tài khoản này'
                    }, 404)

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

                return _make_json_response({
                    'status': 'success',
                    'data': {
                        'employee_name': employee.name,
                        'month': month,
                        'total_days': total_days,
                        'total_hours': round(total_hours, 2),
                        'incomplete_days': incomplete_days,
                        'average_hours_per_day': round(total_hours / total_days, 2) if total_days > 0 else 0,
                    }
                }, 200)

        except Exception as e:
            _logger.error(f"Get summary error: {str(e)}", exc_info=True)
            return _make_json_response({
                'status': 'error',
                'message': f'Lỗi khi lấy tổng hợp: {str(e)}'
            }, 500)

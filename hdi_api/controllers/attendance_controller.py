"""
API Controller for Attendance
Xử lý các endpoint API cho chức năng chấm công
"""
import logging
from datetime import datetime, timedelta
from odoo import http
from odoo.http import request

from .auth_controller import _verify_token
from ..utils.response_formatter import ResponseFormatter

_logger = logging.getLogger(__name__)


class AttendanceAPI(http.Controller):
    """API endpoints cho chấm công"""

    def _get_env(self):
        """Lấy environment từ token"""
        db_name = request.jwt_payload.get('db')
        import odoo
        from odoo.modules.registry import Registry

        registry = Registry(db_name)
        cr = registry.cursor()
        return odoo.api.Environment(cr, odoo.SUPERUSER_ID, {}), cr

    # ========== CHECK-IN ==========
    @http.route('/api/v1/attendance/check-in', type='http', auth='none', methods=['POST'], csrf=False)
    @_verify_token
    def check_in(self):
        """Chấm công vào"""
        try:
            user_id = request.jwt_payload.get('user_id')
            env, cr = self._get_env()
            
            try:
                # Lấy GPS coordinates từ request
                in_latitude = request.httprequest.form.get('in_latitude')
                in_longitude = request.httprequest.form.get('in_longitude')
                
                employee = env['hr.employee'].search([('user_id', '=', user_id)], limit=1)
                result = env['hr.attendance'].api_check_in(employee.id, in_latitude, in_longitude)
                cr.commit()
                
                return ResponseFormatter.success_response('Chấm công vào thành công', result, ResponseFormatter.HTTP_OK)
            except Exception as e:
                cr.rollback()
                raise
        
        except Exception as e:
            _logger.error(f"Check-in error: {str(e)}", exc_info=True)
            return ResponseFormatter.error_response(f'Lỗi: {str(e)}', ResponseFormatter.HTTP_INTERNAL_ERROR)

    # ========== CHECK-OUT ==========
    @http.route('/api/v1/attendance/check-out', type='http', auth='none', methods=['POST'], csrf=False)
    @_verify_token
    def check_out(self):
        """Chấm công ra"""
        try:
            user_id = request.jwt_payload.get('user_id')
            env, cr = self._get_env()
            
            try:
                # Lấy GPS coordinates từ request
                out_latitude = request.httprequest.form.get('out_latitude')
                out_longitude = request.httprequest.form.get('out_longitude')
                
                employee = env['hr.employee'].search([('user_id', '=', user_id)], limit=1)
                result = env['hr.attendance'].api_check_out(employee.id, out_latitude, out_longitude)
                cr.commit()
                
                return ResponseFormatter.success_response('Chấm công ra thành công', result, ResponseFormatter.HTTP_OK)
            except Exception as e:
                cr.rollback()
                raise
        
        except Exception as e:
            _logger.error(f"Check-out error: {str(e)}", exc_info=True)
            return ResponseFormatter.error_response(f'Lỗi: {str(e)}', ResponseFormatter.HTTP_INTERNAL_ERROR)

    # ========== STATUS ==========
    @http.route('/api/v1/attendance/status', type='http', auth='none', methods=['GET'], csrf=False)
    @_verify_token
    def get_status(self):
        """Lấy trạng thái chấm công hiện tại"""
        try:
            user_id = request.jwt_payload.get('user_id')
            env, cr = self._get_env()
            
            try:
                employee = env['hr.employee'].search([('user_id', '=', user_id)], limit=1)
                
                # Kiểm tra có đang check-in không
                current_attendance = env['hr.attendance'].search([
                    ('employee_id', '=', employee.id),
                    ('check_out', '=', False)
                ], limit=1)

                if current_attendance:
                    result = {
                        'is_checked_in': True,
                        'attendance_id': current_attendance.id,
                        'check_in': current_attendance.check_in.isoformat() if current_attendance.check_in else None,
                        'in_latitude': current_attendance.in_latitude,
                        'in_longitude': current_attendance.in_longitude,
                        'employee_name': employee.name,
                    }
                else:
                    result = {
                        'is_checked_in': False,
                        'employee_name': employee.name,
                    }
                
                cr.commit()
                return ResponseFormatter.success_response('Trạng thái chấm công', result, ResponseFormatter.HTTP_OK)
            except Exception as e:
                cr.rollback()
                raise

        except Exception as e:
            _logger.error(f"Get status error: {str(e)}", exc_info=True)
            return ResponseFormatter.error_response(f'Lỗi: {str(e)}', ResponseFormatter.HTTP_INTERNAL_ERROR)

    # ========== HISTORY ==========
    @http.route('/api/v1/attendance/history', type='http', auth='none', methods=['GET'], csrf=False)
    @_verify_token
    def get_history(self):
        """Lấy lịch sử chấm công"""
        try:
            user_id = request.jwt_payload.get('user_id')
            env, cr = self._get_env()
            
            try:
                # Lấy params
                limit = int(request.httprequest.args.get('limit', 30))
                offset = int(request.httprequest.args.get('offset', 0))
                from_date = request.httprequest.args.get('from_date')
                to_date = request.httprequest.args.get('to_date')

                employee = env['hr.employee'].search([('user_id', '=', user_id)], limit=1)
                
                # Build domain
                domain = [('employee_id', '=', employee.id)]

                if from_date:
                    from_datetime = datetime.strptime(from_date, '%Y-%m-%d')
                    domain.append(('check_in', '>=', from_datetime))

                if to_date:
                    to_datetime = datetime.strptime(to_date, '%Y-%m-%d') + timedelta(days=1)
                    domain.append(('check_in', '<', to_datetime))

                # Lấy danh sách chấm công
                attendances = env['hr.attendance'].search(domain, limit=limit, offset=offset, order='check_in desc')
                total_count = env['hr.attendance'].search_count(domain)

                # Format data
                attendance_list = []
                for att in attendances:
                    worked_hours = att.worked_hours if hasattr(att, 'worked_hours') else 0
                    attendance_list.append({
                        'id': att.id,
                        'check_in': att.check_in.isoformat() if att.check_in else None,
                        'check_out': att.check_out.isoformat() if att.check_out else None,
                        'in_latitude': att.in_latitude,
                        'in_longitude': att.in_longitude,
                        'out_latitude': att.out_latitude,
                        'out_longitude': att.out_longitude,
                        'worked_hours': worked_hours,
                    })

                result = {
                    'employee_name': employee.name,
                    'attendances': attendance_list,
                    'total_count': total_count,
                    'limit': limit,
                    'offset': offset,
                }
                
                cr.commit()
                return ResponseFormatter.success_response('Lịch sử chấm công', result, ResponseFormatter.HTTP_OK)
            except Exception as e:
                cr.rollback()
                raise

        except Exception as e:
            _logger.error(f"Get history error: {str(e)}", exc_info=True)
            return ResponseFormatter.error_response(f'Lỗi: {str(e)}', ResponseFormatter.HTTP_INTERNAL_ERROR)

    # ========== SUMMARY ==========
    @http.route('/api/v1/attendance/summary', type='http', auth='none', methods=['GET'], csrf=False)
    @_verify_token
    def get_summary(self):
        """Lấy tổng hợp chấm công theo tháng"""
        try:
            user_id = request.jwt_payload.get('user_id')
            env, cr = self._get_env()
            
            try:
                # Lấy month param (YYYY-MM), mặc định là tháng hiện tại
                month = request.httprequest.args.get('month', datetime.now().strftime('%Y-%m'))

                year, month_num = map(int, month.split('-'))
                from_date = datetime(year, month_num, 1)

                # Tính ngày cuối tháng
                if month_num == 12:
                    to_date = datetime(year + 1, 1, 1)
                else:
                    to_date = datetime(year, month_num + 1, 1)

                employee = env['hr.employee'].search([('user_id', '=', user_id)], limit=1)

                # Lấy tất cả attendance trong tháng
                attendances = env['hr.attendance'].search([
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

                result = {
                    'employee_name': employee.name,
                    'month': month,
                    'total_days': total_days,
                    'total_hours': round(total_hours, 2),
                    'incomplete_days': incomplete_days,
                    'average_hours_per_day': round(total_hours / total_days, 2) if total_days > 0 else 0,
                }
                
                cr.commit()
                return ResponseFormatter.success_response('Tổng hợp chấm công', result, ResponseFormatter.HTTP_OK)
            except Exception as e:
                cr.rollback()
                raise

        except Exception as e:
            _logger.error(f"Get summary error: {str(e)}", exc_info=True)
            return ResponseFormatter.error_response(f'Lỗi: {str(e)}', ResponseFormatter.HTTP_INTERNAL_ERROR)

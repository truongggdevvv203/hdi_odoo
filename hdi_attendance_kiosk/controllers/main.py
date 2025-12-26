# -*- coding: utf-8 -*-
from datetime import datetime
from odoo.http import request, route, Controller
from odoo import http, fields
import json
import logging

_logger = logging.getLogger(__name__)


class AttendanceKioskController(Controller):
    """Kiosk UI cho chấm công - sử dụng API từ hdi_api"""
    
    @route('/attendance/kiosk', auth='public', type='http', website=True)
    def attendance_kiosk(self):
        """Màn hình chấm công chính"""
        return request.render('hdi_attendance_kiosk.attendance_kiosk_template')
    
    @route('/kiosk/api/check-in', auth='user', type='json', methods=['POST'])
    def kiosk_check_in(self):
        """Wrapper cho API check-in - gọi hàm api_check_in từ model"""
        try:
            employee = request.env.user.employee_id
            if not employee:
                return {
                    'success': False,
                    'message': 'Bạn không phải nhân viên',
                    'code': 'NO_EMPLOYEE'
                }
            
            # Lấy dữ liệu từ request
            data = json.loads(request.httprequest.get_data(as_text=True)) if request.httprequest.get_data(as_text=True) else {}
            in_latitude = data.get('in_latitude')
            in_longitude = data.get('in_longitude')
            
            # Gọi api_check_in từ model
            result = request.env['hr.attendance'].api_check_in(
                employee.id, 
                in_latitude=in_latitude, 
                in_longitude=in_longitude
            )
            
            return {
                'success': True,
                'message': 'Check-in thành công',
                'data': result
            }
        except Exception as e:
            _logger.error(f"Kiosk check-in error: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': str(e),
                'code': 'ERROR'
            }
    
    @route('/kiosk/api/check-out', auth='user', type='json', methods=['POST'])
    def kiosk_check_out(self):
        """Wrapper cho API check-out - gọi hàm api_check_out từ model"""
        try:
            employee = request.env.user.employee_id
            if not employee:
                return {
                    'success': False,
                    'message': 'Bạn không phải nhân viên',
                    'code': 'NO_EMPLOYEE'
                }
            
            # Lấy dữ liệu từ request
            data = json.loads(request.httprequest.get_data(as_text=True)) if request.httprequest.get_data(as_text=True) else {}
            out_latitude = data.get('out_latitude')
            out_longitude = data.get('out_longitude')
            
            # Gọi api_check_out từ model
            result = request.env['hr.attendance'].api_check_out(
                employee.id, 
                out_latitude=out_latitude, 
                out_longitude=out_longitude
            )
            
            return {
                'success': True,
                'message': 'Check-out thành công',
                'data': result
            }
        except Exception as e:
            _logger.error(f"Kiosk check-out error: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': str(e),
                'code': 'ERROR'
            }
    
    @route('/kiosk/api/status', auth='user', type='json', methods=['GET'])
    def kiosk_status(self):
        """Lấy trạng thái check-in/out hôm nay"""
        try:
            employee = request.env.user.employee_id
            if not employee:
                return {
                    'success': False,
                    'message': 'Bạn không phải nhân viên',
                    'code': 'NO_EMPLOYEE'
                }
            
            # Tìm attendance hôm nay (chưa check-out)
            today_start = fields.Date.context_today(request.env).replace(hour=0, minute=0, second=0)
            today_attendance = request.env['hr.attendance'].search([
                ('employee_id', '=', employee.id),
                ('check_in', '>=', today_start),
            ], order='check_in desc', limit=1)
            
            if not today_attendance:
                return {
                    'success': True,
                    'status': 'not_checked_in',
                    'employee_name': employee.name,
                    'message': 'Bạn chưa check-in hôm nay'
                }
            
            if today_attendance.check_out:
                return {
                    'success': True,
                    'status': 'checked_out',
                    'employee_name': employee.name,
                    'check_in_time': today_attendance.check_in.isoformat(),
                    'check_out_time': today_attendance.check_out.isoformat(),
                    'worked_hours': round(today_attendance.worked_hours, 2),
                    'message': f'Giờ làm việc: {today_attendance.worked_hours:.1f} giờ'
                }
            else:
                # Tính giờ làm việc tạm thời
                now = datetime.now()
                current_worked_hours = (now - today_attendance.check_in).total_seconds() / 3600
                
                return {
                    'success': True,
                    'status': 'checked_in',
                    'employee_name': employee.name,
                    'check_in_time': today_attendance.check_in.isoformat(),
                    'current_worked_hours': round(current_worked_hours, 2),
                    'message': f'Đã check-in: {today_attendance.check_in.strftime("%H:%M:%S")}'
                }
        except Exception as e:
            _logger.error(f"Kiosk status error: {str(e)}", exc_info=True)
            return {
                'success': False,
                'message': str(e),
                'code': 'ERROR'
            }
    
    @route('/kiosk/api/today-worked-hours', auth='user', type='json', methods=['GET'])
    def kiosk_today_worked_hours(self):
        """Lấy tổng giờ làm việc hôm nay"""
        try:
            employee = request.env.user.employee_id
            if not employee:
                return {
                    'success': False,
                    'total_worked_hours': 0,
                    'message': 'Bạn không phải nhân viên'
                }
            
            # Tìm tất cả attendance hôm nay
            today_start = fields.Date.context_today(request.env).replace(hour=0, minute=0, second=0)
            today_attendances = request.env['hr.attendance'].search([
                ('employee_id', '=', employee.id),
                ('check_in', '>=', today_start)
            ])
            
            total_hours = 0
            for att in today_attendances:
                if att.check_out:
                    total_hours += att.worked_hours
                else:
                    # Tính giờ từ check-in đến bây giờ
                    current_hours = (datetime.now() - att.check_in).total_seconds() / 3600
                    total_hours += current_hours
            
            return {
                'success': True,
                'total_worked_hours': round(total_hours, 2),
                'employee_name': employee.name
            }
        except Exception as e:
            _logger.error(f"Kiosk today worked hours error: {str(e)}", exc_info=True)
            return {
                'success': False,
                'total_worked_hours': 0,
                'message': str(e)
            }

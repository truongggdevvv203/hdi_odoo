import json
import logging
from odoo import http
from odoo.http import request, Response
from .auth_controller import _verify_token_json

_logger = logging.getLogger(__name__)


class EmployeeController(http.Controller):

    @http.route('/api/employee/detail', type='json', auth='none', methods=['POST'], csrf=False)
    @_verify_token_json
    def get_employee_detail(self, **kwargs):
        """
        API lấy thông tin chi tiết nhân viên theo phân quyền phòng ban
        Body Request: {"employee_id": int}
        """
        try:
            # Lấy dữ liệu từ request
            data = request.jsonrequest
            employee_id = data.get('employee_id')
            
            if not employee_id:
                return {
                    'status': 'error',
                    'code': 400,
                    'message': 'employee_id là bắt buộc',
                    'data': None
                }

            # Lấy user hiện tại từ JWT payload
            jwt_payload = getattr(request, 'jwt_payload', {})
            user_id = jwt_payload.get('uid')
            
            if not user_id:
                return {
                    'status': 'error',
                    'code': 401,
                    'message': 'Token không hợp lệ',
                    'data': None
                }

            current_user = request.env['res.users'].sudo().browse(user_id)
            current_employee = current_user.employee_id
            
            if not current_employee:
                return {
                    'status': 'error', 
                    'code': 403,
                    'message': 'User hiện tại không phải là nhân viên',
                    'data': None
                }

            # Tìm nhân viên được yêu cầu
            target_employee = request.env['hr.employee'].sudo().search([('id', '=', employee_id)], limit=1)
            
            if not target_employee:
                return {
                    'status': 'error',
                    'code': 404,
                    'message': 'Không tìm thấy nhân viên',
                    'data': None
                }

            # Kiểm tra phân quyền phòng ban
            has_access = self._check_department_access(current_user, current_employee, target_employee)
            
            if not has_access:
                return {
                    'status': 'error',
                    'code': 403,
                    'message': 'Không có quyền truy cập thông tin nhân viên này',
                    'data': None
                }

            # Lấy thông tin chi tiết nhân viên
            employee_data = self._get_employee_detail_data(target_employee)

            return {
                'status': 'success',
                'code': 200,
                'message': 'Lấy thông tin nhân viên thành công',
                'data': employee_data
            }

        except Exception as e:
            _logger.error(f"Error in get_employee_detail: {str(e)}")
            return {
                'status': 'error',
                'code': 500,
                'message': 'Có lỗi xảy ra khi lấy thông tin nhân viên',
                'data': None
            }

    def _check_department_access(self, current_user, current_employee, target_employee):
        """
        Kiểm tra quyền truy cập thông tin nhân viên theo phòng ban
        Rules:
        1. Admin có thể xem tất cả
        2. Trưởng phòng có thể xem nhân viên trong phòng ban của mình
        3. Nhân viên chỉ có thể xem thông tin của chính mình
        4. HR có thể xem tất cả nhân viên
        """        
        # Rule 1: Admin có thể xem tất cả
        if current_user.has_group('base.group_system'):
            return True
            
        # Rule 4: HR có thể xem tất cả
        if current_user.has_group('hr.group_hr_manager') or current_user.has_group('hr.group_hr_user'):
            return True
        
        # Rule 3: Nhân viên có thể xem thông tin của chính mình
        if current_employee and current_employee.id == target_employee.id:
            return True
            
        # Rule 2: Trưởng phòng có thể xem nhân viên trong phòng ban
        if current_employee and current_employee.department_id:
            # Kiểm tra xem current_employee có phải là trưởng phòng không
            is_department_head = request.env['hr.department'].sudo().search([
                ('head_id', '=', current_employee.id)
            ])
            
            if is_department_head:
                # Kiểm tra target_employee có trong các phòng ban mà current_employee là trưởng phòng không
                target_in_managed_departments = target_employee.department_id.id in is_department_head.ids
                if target_in_managed_departments:
                    return True
        
        return False

    def _get_employee_detail_data(self, employee):
        """Lấy thông tin chi tiết của nhân viên"""
        return {
            'id': employee.id,
            'name': employee.name,
            'employee_code': employee.barcode or '',
            'work_email': employee.work_email or '',
            'work_phone': employee.work_phone or '',
            'mobile_phone': employee.mobile_phone or '',
            'job_title': employee.job_title or '',
            'department': {
                'id': employee.department_id.id if employee.department_id else None,
                'name': employee.department_id.name if employee.department_id else '',
                'code': employee.department_id.department_code if employee.department_id else ''
            },
            'manager': {
                'id': employee.parent_id.id if employee.parent_id else None,
                'name': employee.parent_id.name if employee.parent_id else ''
            },
            'work_location': employee.work_location_id.name if employee.work_location_id else '',
            'start_work_date': employee.start_work_date.isoformat() if employee.start_work_date else None,
            'seniority_text': employee.seniority_text or '',
            'birthday': employee.birthday.isoformat() if employee.birthday else None,
            'gender': employee.gender or '',
            'marital': employee.marital or '',
            'address_home': employee.address_home_id.name if employee.address_home_id else '',
            'bank_account_id': employee.bank_account_id.acc_number if employee.bank_account_id else '',
            'identification_id': employee.identification_id or '',
            'passport_id': employee.passport_id or '',
            'visa_no': employee.visa_no or '',
            'visa_expire': employee.visa_expire.isoformat() if employee.visa_expire else None,
            'work_permit_no': employee.work_permit_no or '',
            'work_permit_expiry_date': employee.work_permit_expiry_date.isoformat() if employee.work_permit_expiry_date else None,
            'active': employee.active,
            'company': {
                'id': employee.company_id.id if employee.company_id else None,
                'name': employee.company_id.name if employee.company_id else ''
            }
        }
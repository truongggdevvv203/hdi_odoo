import json
import logging
from odoo import http
from odoo.http import request, Response
from .auth_controller import _verify_token_json, _get_json_data, _format_success_response, _format_error_response

_logger = logging.getLogger(__name__)


class EmployeeController(http.Controller):

    @http.route('/api/employee/detail', type='json', auth='none', methods=['POST'], csrf=False)
    @_verify_token_json
    def get_employee_detail(self, **kwargs):
        try:
            # Lấy dữ liệu từ request
            data = _get_json_data()
            employee_id = data.get('employee_id')

            if not employee_id:
                return _format_error_response('employee_id là bắt buộc', code=400)

            # Lấy user hiện tại từ JWT payload
            jwt_payload = getattr(request, 'jwt_payload', {})
            user_id = jwt_payload.get('user_id')
            db_name = jwt_payload.get('db')

            if not user_id or not db_name:
                return _format_error_response('Token không hợp lệ', code=401)

            # Tạo environment mới với user_id từ token
            # Điều này rất quan trọng để tránh lỗi singleton khi auth='none'
            import odoo
            from odoo.modules.registry import Registry

            registry = Registry(db_name)
            with registry.cursor() as cr:
                # Tạo environment với user_id cụ thể thay vì SUPERUSER_ID
                env = odoo.api.Environment(cr, user_id, {})

                # Lấy user hiện tại
                current_user = env['res.users'].browse(user_id)

                if not current_user.exists():
                    return _format_error_response('User không tồn tại', code=401)

                # Lấy employee của user hiện tại
                current_employee = current_user.employee_id

                if not current_employee:
                    return _format_error_response('User hiện tại không phải là nhân viên', code=403)

                # Tìm nhân viên được yêu cầu
                target_employee = env['hr.employee'].sudo().browse(employee_id)

                if not target_employee.exists():
                    return _format_error_response('Không tìm thấy nhân viên', code=404)

                # Kiểm tra phân quyền phòng ban
                has_access = self._check_department_access(env, current_user, current_employee, target_employee)

                if not has_access:
                    return _format_error_response('Không có quyền truy cập thông tin nhân viên này', code=403)

                # Lấy thông tin chi tiết nhân viên
                employee_data = self._get_employee_detail_data(target_employee)

                return _format_success_response('Lấy thông tin nhân viên thành công', data=employee_data, code=200)

        except Exception as e:
            _logger.error(f"Error in get_employee_detail: {str(e)}", exc_info=True)
            return _format_error_response('Có lỗi xảy ra khi lấy thông tin nhân viên', code=500)

    def _check_department_access(self, env, current_user, current_employee, target_employee):
        """Kiểm tra quyền truy cập thông tin nhân viên"""
        try:
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
                # Trong Odoo 18, field có thể là manager_id hoặc parent_id
                managed_departments = env['hr.department'].sudo().search([
                    '|',
                    ('manager_id', '=', current_employee.id),
                    ('parent_id', '=', current_employee.id)
                ])

                if managed_departments:
                    # Kiểm tra target_employee có trong các phòng ban mà current_employee là trưởng phòng không
                    if target_employee.department_id and target_employee.department_id.id in managed_departments.ids:
                        return True

                    # Kiểm tra cả các phòng ban con
                    all_child_departments = self._get_all_child_departments(env, managed_departments)
                    if target_employee.department_id and target_employee.department_id.id in all_child_departments.ids:
                        return True

            return False

        except Exception as e:
            _logger.error(f"Error in _check_department_access: {str(e)}", exc_info=True)
            return False

    def _get_all_child_departments(self, env, departments):
        """Lấy tất cả các phòng ban con (đệ quy)"""
        all_departments = departments
        for dept in departments:
            child_depts = env['hr.department'].sudo().search([
                ('parent_id', '=', dept.id)
            ])
            if child_depts:
                all_departments |= self._get_all_child_departments(env, child_depts)
        return all_departments

    def _get_employee_detail_data(self, employee):
        """Lấy thông tin chi tiết của nhân viên"""
        try:
            # Sử dụng sudo() để đảm bảo có quyền đọc tất cả các field
            emp = employee.sudo()

            return {
                'id': emp.id,
                'name': emp.name or '',
                'employee_code': emp.barcode or '',
                'work_email': emp.work_email or '',
                'work_phone': emp.work_phone or '',
                'mobile_phone': emp.mobile_phone or '',
                'job_title': emp.job_title or '',
                'department': {
                    'id': emp.department_id.id if emp.department_id else None,
                    'name': emp.department_id.name if emp.department_id else '',
                    'code': getattr(emp.department_id, 'department_code', '') if emp.department_id else ''
                },
                'manager': {
                    'id': emp.parent_id.id if emp.parent_id else None,
                    'name': emp.parent_id.name if emp.parent_id else ''
                },
                'work_location': emp.work_location_id.name if emp.work_location_id else '',
                'start_work_date': emp.start_work_date.isoformat() if emp.start_work_date else None,
                'seniority_text': getattr(emp, 'seniority_text', '') or '',
                'birthday': emp.birthday.isoformat() if emp.birthday else None,
                'gender': emp.gender or '',
                'marital': emp.marital or '',
                'address_home': emp.address_home_id.name if emp.address_home_id else '',
                'bank_account_id': emp.bank_account_id.acc_number if emp.bank_account_id else '',
                'identification_id': emp.identification_id or '',
                'passport_id': emp.passport_id or '',
                'visa_no': getattr(emp, 'visa_no', '') or '',
                'visa_expire': emp.visa_expire.isoformat() if hasattr(emp, 'visa_expire') and emp.visa_expire else None,
                'work_permit_no': getattr(emp, 'work_permit_no', '') or '',
                'work_permit_expiry_date': emp.work_permit_expiry_date.isoformat() if hasattr(emp,
                                                                                              'work_permit_expiry_date') and emp.work_permit_expiry_date else None,
                'active': emp.active,
                'company': {
                    'id': emp.company_id.id if emp.company_id else None,
                    'name': emp.company_id.name if emp.company_id else ''
                }
            }
        except Exception as e:
            _logger.error(f"Error in _get_employee_detail_data: {str(e)}", exc_info=True)
            raise
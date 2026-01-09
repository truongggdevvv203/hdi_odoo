"""
API Controller for Employee
Xử lý các endpoint API cho thông tin nhân viên
"""
import logging
from odoo import http
from odoo.http import request

from .auth_controller import _verify_token_http, _get_json_data
from ..utils.response_formatter import ResponseFormatter

_logger = logging.getLogger(__name__)


class EmployeeController(http.Controller):
    """API endpoints cho nhân viên"""

    def _get_env(self):
        """Lấy environment từ token"""
        db_name = request.jwt_payload.get('db')
        import odoo
        from odoo.modules.registry import Registry

        registry = Registry(db_name)
        cr = registry.cursor()
        return odoo.api.Environment(cr, odoo.SUPERUSER_ID, {}), cr

    # ========== GET LIST ==========
    @http.route('/api/v1/employee/list', type='http', auth='none', methods=['POST'], csrf=False)
    @_verify_token_http
    def get_employee_list(self):
        """Lấy danh sách nhân viên với tìm kiếm và lọc"""
        try:
            data = _get_json_data()
            user_id = request.jwt_payload.get('user_id')
            env, cr = self._get_env()

            # Lấy tham số từ request
            search_text = data.get('search', '')
            department_id = data.get('department_id', False)
            job_id = data.get('job_id', False)
            active = data.get('active', True)
            limit = data.get('limit', 50)
            offset = data.get('offset', 0)

            try:
                # Xây dựng domain tìm kiếm
                domain = []

                if active is not None:
                    domain.append(('active', '=', active))

                if search_text:
                    domain.append('|')
                    domain.append('|')
                    domain.append(('name', 'ilike', search_text))
                    domain.append(('work_email', 'ilike', search_text))
                    domain.append(('mobile_phone', 'ilike', search_text))

                if department_id:
                    domain.append(('department_id', '=', department_id))

                if job_id:
                    domain.append(('job_id', '=', job_id))

                # Tìm kiếm nhân viên
                employees = env['hr.employee'].sudo().search(
                    domain,
                    limit=limit,
                    offset=offset,
                    order='name asc'
                )

                # Đếm tổng số bản ghi
                total_count = env['hr.employee'].sudo().search_count(domain)

                # Chuẩn bị dữ liệu trả về
                employee_list = []
                for emp in employees:
                    employee_list.append({
                        'id': emp.id,
                        'name': emp.name,
                        'work_email': emp.work_email or '',
                        'mobile_phone': emp.mobile_phone or '',
                        'work_phone': emp.work_phone or '',
                        'department_id': emp.department_id.id if emp.department_id else False,
                        'department_name': emp.department_id.name if emp.department_id else '',
                        'job_id': emp.job_id.id if emp.job_id else False,
                        'job_title': emp.job_id.name if emp.job_id else '',
                        'parent_id': emp.parent_id.id if emp.parent_id else False,
                        'parent_name': emp.parent_id.name if emp.parent_id else '',
                        'company_id': emp.company_id.id if emp.company_id else False,
                        'company_name': emp.company_id.name if emp.company_id else '',
                        'active': emp.active,
                        'image_128': emp.image_128.decode('utf-8') if emp.image_128 else False,
                    })

                result = {
                    'employees': employee_list,
                    'total_count': total_count,
                    'limit': limit,
                    'offset': offset,
                }

                cr.commit()
                return ResponseFormatter.success_response('Lấy danh sách nhân viên thành công', result, ResponseFormatter.HTTP_OK)

            except Exception as e:
                cr.rollback()
                raise

        except Exception as e:
            _logger.error(f"Get employee list error: {str(e)}", exc_info=True)
            return ResponseFormatter.error_response(f'Lỗi: {str(e)}', ResponseFormatter.HTTP_INTERNAL_ERROR)

    # ========== GET DETAIL ==========
    @http.route('/api/employee/detail', type='http', auth='none', methods=['POST'], csrf=False)
    @_verify_token_http
    def get_employee_detail(self):
        """Lấy thông tin chi tiết nhân viên"""
        try:
            data = _get_json_data()
            employee_id = data.get('employee_id')
            user_id = request.jwt_payload.get('user_id')
            env, cr = self._get_env()

            try:
                employee_data = env['hr.employee'].api_get_employee_detail(employee_id, user_id)
                cr.commit()

                return ResponseFormatter.success_response('Lấy thông tin nhân viên thành công', employee_data, ResponseFormatter.HTTP_OK)
            except Exception as e:
                cr.rollback()
                raise

        except Exception as e:
            _logger.error(f"Get employee detail error: {str(e)}", exc_info=True)
            return ResponseFormatter.error_response(f'Lỗi: {str(e)}', ResponseFormatter.HTTP_INTERNAL_ERROR)

    # ========== GET DEPARTMENTS ==========
    @http.route('/api/v1/employee/departments', type='http', auth='none', methods=['GET'], csrf=False)
    @_verify_token_http
    def get_departments(self):
        """Lấy danh sách phòng ban"""
        try:
            env, cr = self._get_env()

            try:
                departments = env['hr.department'].sudo().search([
                    ('active', '=', True)
                ], order='name asc')

                department_list = []
                for dept in departments:
                    department_list.append({
                        'id': dept.id,
                        'name': dept.name,
                        'parent_id': dept.parent_id.id if dept.parent_id else False,
                        'parent_name': dept.parent_id.name if dept.parent_id else '',
                        'manager_id': dept.manager_id.id if dept.manager_id else False,
                        'manager_name': dept.manager_id.name if dept.manager_id else '',
                        'total_employee': dept.total_employee or 0,
                    })

                cr.commit()
                return ResponseFormatter.success_response('Lấy danh sách phòng ban thành công', department_list, ResponseFormatter.HTTP_OK)

            except Exception as e:
                cr.rollback()
                raise

        except Exception as e:
            _logger.error(f"Get departments error: {str(e)}", exc_info=True)
            return ResponseFormatter.error_response(f'Lỗi: {str(e)}', ResponseFormatter.HTTP_INTERNAL_ERROR)

    # ========== GET JOBS ==========
    @http.route('/api/v1/employee/jobs', type='http', auth='none', methods=['GET'], csrf=False)
    @_verify_token_http
    def get_jobs(self):
        """Lấy danh sách chức vụ"""
        try:
            env, cr = self._get_env()

            try:
                jobs = env['hr.job'].sudo().search([
                    ('active', '=', True)
                ], order='name asc')

                job_list = []
                for job in jobs:
                    job_list.append({
                        'id': job.id,
                        'name': job.name,
                        'department_id': job.department_id.id if job.department_id else False,
                        'department_name': job.department_id.name if job.department_id else '',
                        'no_of_employee': job.no_of_employee or 0,
                    })

                cr.commit()
                return ResponseFormatter.success_response('Lấy danh sách chức vụ thành công', job_list, ResponseFormatter.HTTP_OK)

            except Exception as e:
                cr.rollback()
                raise

        except Exception as e:
            _logger.error(f"Get jobs error: {str(e)}", exc_info=True)
            return ResponseFormatter.error_response(f'Lỗi: {str(e)}', ResponseFormatter.HTTP_INTERNAL_ERROR)

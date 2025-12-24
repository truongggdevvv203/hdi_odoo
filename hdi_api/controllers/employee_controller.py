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

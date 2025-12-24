import json
import logging
from odoo import http
from odoo.http import request, Response
from odoo.exceptions import UserError
from .auth_controller import _verify_token_http, _get_json_data
from ..utils.response_formatter import ResponseFormatter

_logger = logging.getLogger(__name__)


class EmployeeController(http.Controller):

    @http.route('/api/employee/detail', type='http', auth='none', methods=['POST'], csrf=False)
    @_verify_token_http
    def get_employee_detail(self, **kwargs):
        try:
            # Lấy dữ liệu từ request
            data = _get_json_data()
            employee_id = data.get('employee_id')

            if not employee_id:
                return ResponseFormatter.error_response('employee_id là bắt buộc', ResponseFormatter.HTTP_BAD_REQUEST)

            # Lấy user hiện tại từ JWT payload
            jwt_payload = getattr(request, 'jwt_payload', {})
            user_id = jwt_payload.get('user_id')
            db_name = jwt_payload.get('db')

            if not user_id:
                return ResponseFormatter.error_response('Token không hợp lệ', ResponseFormatter.HTTP_UNAUTHORIZED)

            if not db_name:
                return ResponseFormatter.error_response('Token không chứa thông tin database', ResponseFormatter.HTTP_BAD_REQUEST)

            # Sử dụng registry như AttendanceAPI để tránh lỗi singleton
            import odoo
            from odoo.modules.registry import Registry

            registry = Registry(db_name)
            with registry.cursor() as cr:
                env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})

                try:
                    # Gọi API method từ model (logic tập trung ở model)
                    employee_data = env['hr.employee'].api_get_employee_detail(employee_id, user_id)
                    
                    return ResponseFormatter.success_response('Lấy thông tin nhân viên thành công', employee_data, ResponseFormatter.HTTP_OK)

                except UserError as ue:
                    return ResponseFormatter.error_response(str(ue), ResponseFormatter.HTTP_FORBIDDEN)
                except Exception as e:
                    _logger.error(f"Error in get_employee_detail: {str(e)}", exc_info=True)
                    return ResponseFormatter.error_response('Có lỗi xảy ra khi lấy thông tin nhân viên', ResponseFormatter.HTTP_INTERNAL_ERROR)

        except Exception as e:
            _logger.error(f"Error in get_employee_detail: {str(e)}", exc_info=True)
            return ResponseFormatter.error_response('Có lỗi xảy ra khi lấy thông tin nhân viên', ResponseFormatter.HTTP_INTERNAL_ERROR)
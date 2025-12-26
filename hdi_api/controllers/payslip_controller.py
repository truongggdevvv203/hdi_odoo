"""
API Controller for Payslip
Xử lý các endpoint API cho bảng lương
"""
import logging
from datetime import datetime
from odoo import http
from odoo.http import request

from .auth_controller import _verify_token
from ..utils.response_formatter import ResponseFormatter

_logger = logging.getLogger(__name__)


class PayslipController(http.Controller):
    """API endpoints cho bảng lương"""

    def _get_env(self):
        """Lấy environment từ token"""
        db_name = request.jwt_payload.get('db')
        import odoo
        from odoo.modules.registry import Registry

        registry = Registry(db_name)
        cr = registry.cursor()
        return odoo.api.Environment(cr, odoo.SUPERUSER_ID, {}), cr

    # ========== GET PAYSLIP LIST ==========
    @http.route('/api/v1/payslip/list', type='http', auth='none', methods=['POST'], csrf=False)
    @_verify_token
    def get_payslip_list(self):
        """Lấy danh sách bảng lương của user"""
        try:
            user_id = request.jwt_payload.get('user_id')
            env, cr = self._get_env()

            try:
                # Tìm employee từ user_id
                employee = env['hr.employee'].search([('user_id', '=', user_id)], limit=1)
                
                if not employee:
                    return ResponseFormatter.error_response(
                        'Không tìm thấy thông tin nhân viên',
                        ResponseFormatter.HTTP_NOT_FOUND
                    )
                
                # Lấy danh sách payslip
                payslips = env['hr.payslip'].search(
                    [('employee_id', '=', employee.id)],
                    order='date_from desc',
                    limit=100
                )
                
                result = []
                for payslip in payslips:
                    result.append({
                        'id': payslip.id,
                        'name': payslip.name,
                        'number': payslip.number,
                        'date_from': payslip.date_from.isoformat() if payslip.date_from else None,
                        'date_to': payslip.date_to.isoformat() if payslip.date_to else None,
                        'state': payslip.state,
                        'basic_wage': payslip.basic_wage,
                        'gross_wage': payslip.gross_wage,
                        'net_wage': payslip.net_wage,
                        'created_date': payslip.create_date.isoformat() if payslip.create_date else None,
                    })
                
                cr.commit()
                return ResponseFormatter.success_response(
                    'Lấy danh sách bảng lương thành công',
                    {'payslips': result, 'total': len(result)},
                    ResponseFormatter.HTTP_OK
                )
            except Exception as e:
                cr.rollback()
                raise

        except Exception as e:
            _logger.error(f"Get payslip list error: {str(e)}", exc_info=True)
            return ResponseFormatter.error_response(
                f'Lỗi: {str(e)}',
                ResponseFormatter.HTTP_INTERNAL_ERROR
            )

    # ========== GET PAYSLIP DETAIL ==========
    @http.route('/api/v1/payslip/detail', type='http', auth='none', methods=['POST'], csrf=False)
    @_verify_token
    def get_payslip_detail(self):
        """Lấy chi tiết bảng lương"""
        try:
            user_id = request.jwt_payload.get('user_id')
            env, cr = self._get_env()

            try:
                # Lấy payslip_id từ request
                import json
                data = json.loads(request.httprequest.data.decode('utf-8'))
                payslip_id = data.get('payslip_id')
                
                if not payslip_id:
                    return ResponseFormatter.error_response(
                        'Vui lòng cung cấp payslip_id',
                        ResponseFormatter.HTTP_BAD_REQUEST
                    )
                
                # Tìm employee từ user_id
                employee = env['hr.employee'].search([('user_id', '=', user_id)], limit=1)
                
                if not employee:
                    return ResponseFormatter.error_response(
                        'Không tìm thấy thông tin nhân viên',
                        ResponseFormatter.HTTP_NOT_FOUND
                    )
                
                # Lấy payslip và kiểm tra quyền
                payslip = env['hr.payslip'].search([
                    ('id', '=', payslip_id),
                    ('employee_id', '=', employee.id)
                ], limit=1)
                
                if not payslip:
                    return ResponseFormatter.error_response(
                        'Không tìm thấy bảng lương hoặc bạn không có quyền truy cập',
                        ResponseFormatter.HTTP_FORBIDDEN
                    )
                
                # Xây dựng dữ liệu chi tiết
                result = {
                    'id': payslip.id,
                    'name': payslip.name,
                    'number': payslip.number,
                    'employee_name': payslip.employee_id.name,
                    'date_from': payslip.date_from.isoformat() if payslip.date_from else None,
                    'date_to': payslip.date_to.isoformat() if payslip.date_to else None,
                    'state': payslip.state,
                    'basic_wage': payslip.basic_wage,
                    'gross_wage': payslip.gross_wage,
                    'net_wage': payslip.net_wage,
                    'standard_days': payslip.standard_days,
                    'worked_days': payslip.worked_days_line_ids.__len__(),
                    'lines': []
                }
                
                # Thêm chi tiết các dòng lương
                for line in payslip.line_ids:
                    result['lines'].append({
                        'id': line.id,
                        'name': line.name,
                        'code': line.code,
                        'amount': line.amount,
                        'sequence': line.sequence,
                    })
                
                # Thêm thông tin ngày công
                worked_days = []
                for wd in payslip.worked_days_line_ids:
                    worked_days.append({
                        'id': wd.id,
                        'name': wd.name,
                        'code': wd.code,
                        'number_of_days': wd.number_of_days,
                        'number_of_hours': wd.number_of_hours,
                    })
                result['worked_days'] = worked_days
                
                # Thêm thông tin nhập thêm (thưởng, phạt, ...)
                input_lines = []
                for inp in payslip.input_line_ids:
                    input_lines.append({
                        'id': inp.id,
                        'name': inp.name,
                        'code': inp.code,
                        'amount': inp.amount,
                    })
                result['input_lines'] = input_lines
                
                cr.commit()
                return ResponseFormatter.success_response(
                    'Lấy chi tiết bảng lương thành công',
                    result,
                    ResponseFormatter.HTTP_OK
                )
            except Exception as e:
                cr.rollback()
                raise

        except Exception as e:
            _logger.error(f"Get payslip detail error: {str(e)}", exc_info=True)
            return ResponseFormatter.error_response(
                f'Lỗi: {str(e)}',
                ResponseFormatter.HTTP_INTERNAL_ERROR
            )

    # ========== GET CURRENT MONTH PAYSLIP ==========
    @http.route('/api/v1/payslip/current-month', type='http', auth='none', methods=['GET'], csrf=False)
    @_verify_token
    def get_current_month_payslip(self):
        """Lấy bảng lương tháng hiện tại"""
        try:
            user_id = request.jwt_payload.get('user_id')
            env, cr = self._get_env()

            try:
                from datetime import datetime
                from dateutil.relativedelta import relativedelta
                
                # Tìm employee từ user_id
                employee = env['hr.employee'].search([('user_id', '=', user_id)], limit=1)
                
                if not employee:
                    return ResponseFormatter.error_response(
                        'Không tìm thấy thông tin nhân viên',
                        ResponseFormatter.HTTP_NOT_FOUND
                    )
                
                # Tính ngày đầu tháng và cuối tháng
                today = datetime.today().date()
                first_day = today.replace(day=1)
                last_day = (first_day + relativedelta(months=1, days=-1))
                
                # Tìm payslip của tháng hiện tại
                payslip = env['hr.payslip'].search([
                    ('employee_id', '=', employee.id),
                    ('date_from', '>=', first_day),
                    ('date_to', '<=', last_day)
                ], limit=1, order='date_from desc')
                
                if not payslip:
                    return ResponseFormatter.error_response(
                        'Chưa có bảng lương cho tháng này',
                        ResponseFormatter.HTTP_NOT_FOUND
                    )
                
                result = {
                    'id': payslip.id,
                    'name': payslip.name,
                    'number': payslip.number,
                    'date_from': payslip.date_from.isoformat() if payslip.date_from else None,
                    'date_to': payslip.date_to.isoformat() if payslip.date_to else None,
                    'state': payslip.state,
                    'basic_wage': payslip.basic_wage,
                    'gross_wage': payslip.gross_wage,
                    'net_wage': payslip.net_wage,
                }
                
                cr.commit()
                return ResponseFormatter.success_response(
                    'Lấy bảng lương tháng hiện tại thành công',
                    result,
                    ResponseFormatter.HTTP_OK
                )
            except Exception as e:
                cr.rollback()
                raise

        except Exception as e:
            _logger.error(f"Get current month payslip error: {str(e)}", exc_info=True)
            return ResponseFormatter.error_response(
                f'Lỗi: {str(e)}',
                ResponseFormatter.HTTP_INTERNAL_ERROR
            )

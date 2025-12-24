from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import date


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    start_work_date = fields.Date(
        string='Ngày bắt đầu làm việc',
        tracking=True
    )

    seniority_text = fields.Char(
        string='Thâm niên',
        compute='_compute_seniority',
        store=True
    )

    @api.depends('start_work_date')
    def _compute_seniority(self):
        """Tính thâm niên hiển thị theo dạng: X năm Y tháng"""
        for rec in self:
            if rec.start_work_date:
                today = date.today()
                start = rec.start_work_date

                years = today.year - start.year
                months = today.month - start.month

                # Nếu chưa tới ngày làm trong tháng ⇒ trừ 1 tháng
                if today.day < start.day:
                    months -= 1

                # Nếu tháng âm ⇒ giảm 1 năm và cộng 12 tháng
                if months < 0:
                    years -= 1
                    months += 12

                # Xuất dạng "X năm Y tháng"
                rec.seniority_text = f"{years} năm {months} tháng"
            else:
                rec.seniority_text = ""

    @api.model
    def api_get_employee_detail(self, employee_id, current_user_id):
        """
        API method để lấy thông tin chi tiết nhân viên
        Kiểm tra quyền truy cập và trả về data
        """
        # Tìm current user và employee
        current_user = self.env['res.users'].browse(current_user_id)
        if not current_user.exists():
            raise UserError('User không tồn tại')

        current_employee = current_user.employee_id
        if not current_employee:
            raise UserError('User hiện tại không phải là nhân viên')

        # Tìm target employee
        target_employee = self.browse(employee_id)
        if not target_employee.exists():
            raise UserError('Không tìm thấy nhân viên')

        # Kiểm tra quyền truy cập
        if not self._check_department_access(current_user, current_employee, target_employee):
            raise UserError('Không có quyền truy cập thông tin nhân viên này')

        # Trả về thông tin chi tiết
        return self._get_employee_detail_data(target_employee)

    def _check_department_access(self, current_user, current_employee, target_employee):
        """Kiểm tra quyền truy cập phòng ban"""
        # Rule 1: Admin có thể xem tất cả
        if current_user.has_group('base.group_system'):
            return True

        # Rule 4: HR có thể xem tất cả
        if current_user.has_group('hr.group_hr_manager') or current_user.has_group('hr.group_hr_user'):
            return True

        # Rule 3: Nhân viên có thể xem thông tin của chính mình
        if current_employee and current_employee.id == target_employee.id:
            return True

        # Rule 2: Trưởng phòng có thể xem nhân viên trong phòng ban và các phòng ban con
        if current_employee and current_employee.department_id:
            # Kiểm tra xem current_employee có phải là trưởng phòng không
            is_department_head = self.env['hr.department'].search([
                ('head_id', '=', current_employee.id)
            ])

            if is_department_head:
                # Lấy tất cả phòng ban con (đệ quy) của từng phòng ban mà trưởng phòng quản lý
                managed_department_ids = []
                for dept in is_department_head:
                    managed_department_ids.extend(self._get_child_departments_recursive(dept.id))

                # Kiểm tra target_employee có trong các phòng ban quản lý không (bao gồm con)
                if target_employee.department_id.id in managed_department_ids:
                    return True

        return False

    def _get_child_departments_recursive(self, parent_department_id, department_ids=None):
        """Lấy danh sách phòng ban con đệ quy"""
        if department_ids is None:
            department_ids = []

        # Thêm phòng ban cha vào list
        if parent_department_id not in department_ids:
            department_ids.append(parent_department_id)

        # Tìm tất cả phòng ban con trực tiếp
        child_departments = self.env['hr.department'].search([
            ('parent_id', '=', parent_department_id)
        ])

        # Đệ quy cho mỗi phòng ban con
        for child in child_departments:
            self._get_child_departments_recursive(child.id, department_ids)

        return department_ids

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
                'code': getattr(employee.department_id, 'department_code', '') if employee.department_id else ''
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
            'bank_account_id': employee.bank_account_id.acc_number if employee.bank_account_id else '',
            'identification_id': employee.identification_id or '',
            'passport_id': employee.passport_id or '',
            'visa_no': employee.visa_no or '',
            'visa_expire': employee.visa_expire.isoformat() if employee.visa_expire else None,
            'active': employee.active,
            'company': {
                'id': employee.company_id.id if employee.company_id else None,
                'name': employee.company_id.name if employee.company_id else ''
            }
        }
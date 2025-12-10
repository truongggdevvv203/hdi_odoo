from odoo import models, fields, api


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    # Personal Information Extensions
    id_number = fields.Char(
        string='Số CMND/CCCD',
        help='Số chứng minh nhân dân hoặc căn cước công dân'
    )

    id_issue_date = fields.Date(
        string='Ngày cấp CMND/CCCD'
    )

    id_issue_place = fields.Char(
        string='Nơi cấp CMND/CCCD'
    )

    tax_id = fields.Char(
        string='Mã số thuế cá nhân'
    )

    bank_account_number = fields.Char(
        string='Số tài khoản ngân hàng'
    )

    bank_name = fields.Char(
        string='Tên ngân hàng'
    )

    # Employment Information Extensions
    employment_date = fields.Date(
        string='Ngày tuyển dụng',
        help='Ngày bắt đầu làm việc tại công ty'
    )

    contract_expiry_date = fields.Date(
        string='Ngày hết hạn hợp đồng'
    )

    position_title = fields.Char(
        string='Chức danh công việc'
    )

    work_location = fields.Char(
        string='Địa điểm làm việc'
    )

    # Compensation Information
    basic_salary = fields.Monetary(
        string='Lương cơ bản',
        currency_field='company_id.currency_id'
    )

    allowance_ids = fields.One2many(
        'hr.employee.allowance',
        'employee_id',
        string='Các khoản trợ cấp'
    )

    total_allowance = fields.Monetary(
        string='Tổng trợ cấp',
        compute='_compute_total_allowance',
        currency_field='company_id.currency_id',
        store=True
    )

    @api.depends('allowance_ids.amount')
    def _compute_total_allowance(self):
        for record in self:
            record.total_allowance = sum(record.allowance_ids.mapped('amount'))

    # Skills and Qualifications
    skill_ids = fields.Many2many(
        'hr.skill',
        string='Kỹ năng'
    )

    certification_ids = fields.One2many(
        'hr.employee.certification',
        'employee_id',
        string='Chứng chỉ/Bằng cấp'
    )

    # Notes
    notes = fields.Text(
        string='Ghi chú'
    )


class HrEmployeeAllowance(models.Model):
    _name = 'hr.employee.allowance'
    _description = 'Employee Allowance (Trợ cấp nhân viên)'
    _order = 'employee_id, allowance_type'

    employee_id = fields.Many2one(
        'hr.employee',
        string='Nhân viên',
        required=True,
        ondelete='cascade'
    )

    allowance_type = fields.Selection([
        ('housing', 'Trợ cấp nhà ở'),
        ('transport', 'Trợ cấp đi lại'),
        ('meal', 'Trợ cấp ăn trưa'),
        ('phone', 'Trợ cấp điện thoại'),
        ('other', 'Khác'),
    ], string='Loại trợ cấp', required=True)

    description = fields.Char(
        string='Mô tả'
    )

    amount = fields.Monetary(
        string='Số tiền',
        required=True,
        currency_field='company_id.currency_id'
    )

    company_id = fields.Many2one(
        'res.company',
        string='Công ty',
        default=lambda self: self.env.company
    )

    active = fields.Boolean(
        string='Kích hoạt',
        default=True
    )

    notes = fields.Text(
        string='Ghi chú'
    )

    def name_get(self):
        result = []
        for record in self:
            name = f"{record.employee_id.name} - {record.get_allowance_type_display()} ({record.amount})"
            result.append((record.id, name))
        return result

    def get_allowance_type_display(self):
        return dict(self._fields['allowance_type'].selection).get(self.allowance_type)


class HrEmployeeCertification(models.Model):
    _name = 'hr.employee.certification'
    _description = 'Employee Certification (Chứng chỉ/Bằng cấp nhân viên)'
    _order = 'employee_id, issue_date desc'

    employee_id = fields.Many2one(
        'hr.employee',
        string='Nhân viên',
        required=True,
        ondelete='cascade'
    )

    certification_name = fields.Char(
        string='Tên chứng chỉ/bằng cấp',
        required=True
    )

    issuing_organization = fields.Char(
        string='Tổ chức cấp'
    )

    issue_date = fields.Date(
        string='Ngày cấp'
    )

    expiry_date = fields.Date(
        string='Ngày hết hạn'
    )

    certification_number = fields.Char(
        string='Số hiệu chứng chỉ'
    )

    level = fields.Selection([
        ('elementary', 'Sơ cấp'),
        ('intermediate', 'Trung cấp'),
        ('advanced', 'Cao cấp'),
        ('bachelor', 'Cử nhân'),
        ('master', 'Thạc sĩ'),
        ('doctor', 'Tiến sĩ'),
    ], string='Trình độ')

    document = fields.Binary(
        string='Tài liệu đính kèm',
        help='Scan chứng chỉ/bằng cấp'
    )

    notes = fields.Text(
        string='Ghi chú'
    )

    def name_get(self):
        result = []
        for record in self:
            name = f"{record.employee_id.name} - {record.certification_name} ({record.issue_date})"
            result.append((record.id, name))
        return result


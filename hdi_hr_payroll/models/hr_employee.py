# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    # ==================== THÔNG TIN THUẾ ====================
    tax_id = fields.Char('Mã số thuế', tracking=True)
    tax_registration_date = fields.Date('Ngày đăng ký thuế')

    # Người phụ thuộc
    dependent_ids = fields.One2many('hr.employee.dependent', 'employee_id', string='Người phụ thuộc')
    dependent_count = fields.Integer('Số người phụ thuộc', compute='_compute_dependent_count', store=True)

    # Currency for monetary fields
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True)

    # Giảm trừ thuế (theo quy định VN 2024)
    personal_deduction = fields.Monetary(
        'Giảm trừ bản thân',
        default=11000000,
        currency_field='currency_id',
        help='Giảm trừ gia cảnh cho bản thân (11tr/tháng theo 2024)'
    )
    dependent_deduction = fields.Monetary(
        'Giảm trừ mỗi người PT',
        default=4400000,
        currency_field='currency_id',
        help='Giảm trừ cho mỗi người phụ thuộc (4.4tr/tháng)'
    )
    total_deduction = fields.Monetary('Tổng giảm trừ', currency_field='currency_id', compute='_compute_total_deduction',
                                      store=True)

    # ==================== THÔNG TIN BẢO HIỂM ====================
    social_insurance_number = fields.Char('Số sổ BHXH', tracking=True)
    social_insurance_date = fields.Date('Ngày cấp sổ BHXH')
    health_insurance_number = fields.Char('Số thẻ BHYT')

    # ==================== KHOẢN VAY/TẠM ỨNG ====================
    loan_ids = fields.One2many('hr.loan', 'employee_id', string='Khoản vay/Tạm ứng')
    active_loan_count = fields.Integer('Số khoản vay đang trả', compute='_compute_loan_count')
    total_loan_balance = fields.Monetary('Tổng nợ còn lại', currency_field='currency_id',
                                         compute='_compute_loan_balance')

    # ==================== KHEN THƯỞNG/KỶ LUẬT ====================
    discipline_ids = fields.One2many('hr.discipline', 'employee_id', string='Kỷ luật')
    reward_ids = fields.One2many('hr.reward', 'employee_id', string='Khen thưởng')

    # ==================== PAYSLIP ====================
    payslip_ids = fields.One2many('hr.payslip', 'employee_id', string='Phiếu lương')
    payslip_count = fields.Integer('Số phiếu lương', compute='_compute_payslip_count')

    @api.depends('dependent_ids', 'dependent_ids.is_active')
    def _compute_dependent_count(self):
        for employee in self:
            employee.dependent_count = len(employee.dependent_ids.filtered('is_active'))

    @api.depends('personal_deduction', 'dependent_count', 'dependent_deduction')
    def _compute_total_deduction(self):
        for employee in self:
            employee.total_deduction = employee.personal_deduction + (
                        employee.dependent_count * employee.dependent_deduction)

    def _compute_loan_count(self):
        for employee in self:
            employee.active_loan_count = len(
                employee.loan_ids.filtered(lambda l: l.state == 'approved' and l.balance > 0))

    def _compute_loan_balance(self):
        for employee in self:
            employee.total_loan_balance = sum(
                employee.loan_ids.filtered(lambda l: l.state == 'approved').mapped('balance'))

    def _compute_payslip_count(self):
        for employee in self:
            employee.payslip_count = len(employee.payslip_ids)

    def action_view_payslips(self):
        self.ensure_one()
        return {
            'name': _('Phiếu lương'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.payslip',
            'view_mode': 'list,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {'default_employee_id': self.id},
        }

    def action_view_dependents(self):
        self.ensure_one()
        return {
            'name': _('Người phụ thuộc'),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.employee.dependent',
            'view_mode': 'list,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {'default_employee_id': self.id},
        }

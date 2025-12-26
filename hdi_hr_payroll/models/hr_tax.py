# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class HrTaxBracket(models.Model):
    """Biểu thuế lũy tiến TNCN theo quy định Việt Nam"""
    _name = 'hr.tax.bracket'
    _description = 'Bậc thuế thu nhập cá nhân'
    _order = 'from_amount'

    name = fields.Char('Bậc thuế', required=True)

    from_amount = fields.Monetary('Từ', required=True, default=0)
    to_amount = fields.Monetary('Đến', help='Để trống nếu không giới hạn trên')

    tax_rate = fields.Float('Thuế suất (%)', required=True, default=0)

    year = fields.Integer('Năm áp dụng', required=True, default=lambda self: fields.Date.today().year)

    active = fields.Boolean('Hoạt động', default=True)

    company_id = fields.Many2one('res.company', 'Công ty', default=lambda self: self.env.company)
    currency_id = fields.Many2one(related='company_id.currency_id')

    note = fields.Text('Ghi chú')

    _sql_constraints = [
        ('tax_rate_check', 'CHECK(tax_rate >= 0 AND tax_rate <= 100)', 'Thuế suất phải từ 0% đến 100%!')
    ]

    @api.constrains('from_amount', 'to_amount')
    def _check_amounts(self):
        for bracket in self:
            if bracket.to_amount and bracket.to_amount < bracket.from_amount:
                raise ValidationError(_('Số tiền "Đến" phải lớn hơn "Từ"!'))

    @api.model
    def calculate_tax(self, taxable_income, year=None):
        """
        Tính thuế TNCN lũy tiến

        :param taxable_income: Thu nhập tính thuế (sau giảm trừ)
        :param year: Năm áp dụng (mặc định năm hiện tại)
        :return: Số thuế phải nộp
        """
        if not year:
            year = fields.Date.today().year

        if taxable_income <= 0:
            return 0

        # Lấy các bậc thuế của năm
        brackets = self.search([
            ('year', '=', year),
            ('active', '=', True)
        ], order='from_amount')

        if not brackets:
            return 0

        total_tax = 0
        remaining_income = taxable_income

        for bracket in brackets:
            # Xác định khoảng thu nhập áp dụng bậc này
            bracket_from = bracket.from_amount
            bracket_to = bracket.to_amount if bracket.to_amount else float('inf')

            # Tính phần thu nhập trong bậc này
            if remaining_income <= bracket_from:
                break

            taxable_in_bracket = min(remaining_income, bracket_to) - bracket_from

            if taxable_in_bracket > 0:
                tax_in_bracket = taxable_in_bracket * (bracket.tax_rate / 100.0)
                total_tax += tax_in_bracket

            if remaining_income <= bracket_to:
                break

        return total_tax


class HrEmployeeDependent(models.Model):
    """Người phụ thuộc để giảm trừ thuế"""
    _name = 'hr.employee.dependent'
    _description = 'Người phụ thuộc'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'employee_id, relationship'

    name = fields.Char('Họ và tên', required=True, tracking=True)

    employee_id = fields.Many2one('hr.employee', 'Nhân viên', required=True, ondelete='cascade', tracking=True)

    relationship = fields.Selection([
        ('child', 'Con'),
        ('parent', 'Cha/Mẹ'),
        ('spouse', 'Vợ/Chồng'),
        ('sibling', 'Anh/Chị/Em'),
        ('other', 'Khác')
    ], 'Quan hệ', required=True, default='child', tracking=True)

    birth_date = fields.Date('Ngày sinh', tracking=True)
    age = fields.Integer('Tuổi', compute='_compute_age', store=True)

    tax_id = fields.Char('Mã số thuế', tracking=True)
    id_number = fields.Char('Số CMND/CCCD', tracking=True)

    # Điều kiện giảm trừ
    is_student = fields.Boolean('Đang đi học', tracking=True)
    is_disabled = fields.Boolean('Khuyết tật', tracking=True)

    # Thời gian áp dụng giảm trừ
    date_from = fields.Date('Giảm trừ từ ngày', required=True, default=fields.Date.today, tracking=True)
    date_to = fields.Date('Giảm trừ đến ngày', tracking=True)

    is_active = fields.Boolean('Đang được giảm trừ', compute='_compute_is_active', store=True)

    # Tài liệu chứng minh
    attachment_ids = fields.Many2many('ir.attachment', string='Giấy tờ chứng minh')

    note = fields.Text('Ghi chú')

    @api.depends('birth_date')
    def _compute_age(self):
        today = fields.Date.today()
        for dependent in self:
            if dependent.birth_date:
                dependent.age = (today - dependent.birth_date).days // 365
            else:
                dependent.age = 0

    @api.depends('date_from', 'date_to')
    def _compute_is_active(self):
        today = fields.Date.today()
        for dependent in self:
            dependent.is_active = (
                    (not dependent.date_from or dependent.date_from <= today) and
                    (not dependent.date_to or dependent.date_to >= today)
            )

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for dependent in self:
            if dependent.date_to and dependent.date_from and dependent.date_to < dependent.date_from:
                raise ValidationError(_('Ngày kết thúc phải sau ngày bắt đầu!'))

    @api.constrains('birth_date')
    def _check_birth_date(self):
        for dependent in self:
            if dependent.birth_date and dependent.birth_date > fields.Date.today():
                raise ValidationError(_('Ngày sinh không thể là ngày tương lai!'))

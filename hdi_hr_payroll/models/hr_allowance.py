# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class HrAllowanceType(models.Model):
    """Loại phụ cấp"""
    _name = 'hr.allowance.type'
    _description = 'Loại phụ cấp'
    _order = 'sequence, name'

    name = fields.Char('Tên phụ cấp', required=True, translate=True)
    code = fields.Char('Mã', required=True, help='Mã dùng trong salary rule')
    
    sequence = fields.Integer('Thứ tự', default=10)
    active = fields.Boolean('Hoạt động', default=True)
    
    # Cách tính
    amount_type = fields.Selection([
        ('fixed', 'Số tiền cố định'),
        ('percentage', 'Theo % lương'),
        ('per_day', 'Theo ngày công')
    ], 'Cách tính', default='fixed', required=True)
    
    default_amount = fields.Monetary('Số tiền mặc định', default=0)
    
    # Tính thuế & BH
    is_taxable = fields.Boolean('Chịu thuế TNCN', default=True, help='Tính vào thu nhập chịu thuế')
    is_insurance_base = fields.Boolean('Tính vào mức đóng BH', default=False)
    
    company_id = fields.Many2one('res.company', 'Công ty', default=lambda self: self.env.company)
    currency_id = fields.Many2one(related='company_id.currency_id')
    
    note = fields.Text('Ghi chú')

    _sql_constraints = [
        ('code_uniq', 'unique(code, company_id)', 'Mã phụ cấp phải duy nhất!')
    ]


class HrAllowanceAssignment(models.Model):
    """Gán phụ cấp cho nhân viên theo hợp đồng"""
    _name = 'hr.allowance.assignment'
    _description = 'Gán phụ cấp cho nhân viên'
    _order = 'date_from desc, id desc'

    name = fields.Char('Tên', compute='_compute_name', store=True)
    
    employee_id = fields.Many2one('hr.employee', 'Nhân viên', required=True, ondelete='cascade')
    contract_id = fields.Many2one('hr.contract', 'Hợp đồng', ondelete='cascade')
    
    allowance_type_id = fields.Many2one('hr.allowance.type', 'Loại phụ cấp', required=True)
    
    amount = fields.Monetary('Số tiền', required=True)
    
    date_from = fields.Date('Từ ngày', required=True, default=fields.Date.today)
    date_to = fields.Date('Đến ngày')
    
    is_active = fields.Boolean('Đang active', compute='_compute_is_active', store=True)
    
    company_id = fields.Many2one(related='employee_id.company_id', store=True)
    currency_id = fields.Many2one(related='company_id.currency_id')
    
    note = fields.Text('Ghi chú')

    @api.depends('employee_id', 'allowance_type_id', 'date_from')
    def _compute_name(self):
        for rec in self:
            if rec.employee_id and rec.allowance_type_id:
                rec.name = f"{rec.allowance_type_id.name} - {rec.employee_id.name}"
            else:
                rec.name = "Phụ cấp"

    @api.depends('date_from', 'date_to')
    def _compute_is_active(self):
        today = fields.Date.today()
        for rec in self:
            rec.is_active = (
                (not rec.date_from or rec.date_from <= today) and
                (not rec.date_to or rec.date_to >= today)
            )

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for rec in self:
            if rec.date_to and rec.date_from and rec.date_to < rec.date_from:
                raise ValidationError(_('Ngày kết thúc phải sau ngày bắt đầu!'))

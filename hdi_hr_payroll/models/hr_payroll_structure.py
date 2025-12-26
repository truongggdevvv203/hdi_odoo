# -*- coding: utf-8 -*-

from odoo import fields, models, _


class HrPayrollStructureType(models.Model):
    _inherit = 'hr.payroll.structure.type'
    
    # Mở rộng nếu cần thêm fields cho VN


class HrPayrollStructure(models.Model):
    _name = 'hr.payroll.structure'
    _description = 'Cấu trúc lương'
    _order = 'name'

    name = fields.Char('Tên cấu trúc', required=True)
    code = fields.Char('Mã', required=True)
    active = fields.Boolean('Hoạt động', default=True)
    
    company_id = fields.Many2one('res.company', 'Công ty', default=lambda self: self.env.company)
    
    # Liên kết với structure type
    type_id = fields.Many2one('hr.payroll.structure.type', 'Loại cấu trúc')
    
    # Các rule áp dụng
    rule_ids = fields.Many2many(
        'hr.salary.rule',
        'hr_structure_salary_rule_rel',
        'struct_id', 'rule_id',
        string='Quy tắc lương'
    )
    
    note = fields.Text('Ghi chú')

    _sql_constraints = [
        ('code_uniq', 'unique(code, company_id)', 'Mã cấu trúc phải duy nhất trong công ty!')
    ]


class HrSalaryRuleCategory(models.Model):
    _name = 'hr.salary.rule.category'
    _description = 'Nhóm quy tắc lương'
    _order = 'sequence, code'

    name = fields.Char('Tên nhóm', required=True, translate=True)
    code = fields.Char('Mã', required=True)
    sequence = fields.Integer('Thứ tự', default=10)
    
    parent_id = fields.Many2one('hr.salary.rule.category', 'Nhóm cha')
    children_ids = fields.One2many('hr.salary.rule.category', 'parent_id', 'Nhóm con')
    
    note = fields.Text('Ghi chú')
    color = fields.Integer('Màu')

    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'Mã nhóm phải duy nhất!')
    ]

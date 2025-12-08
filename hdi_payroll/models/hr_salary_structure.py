from odoo import models, fields, api


class HRSalaryStructure(models.Model):
    _name = 'hr.salary.structure'
    _description = 'Salary Structure (Cấu trúc lương)'
    _order = 'name'

    name = fields.Char(
        string='Tên cấu trúc lương',
        required=True
    )

    company_id = fields.Many2one(
        'res.company',
        string='Công ty',
        default=lambda self: self.env.company
    )

    rule_ids = fields.One2many(
        'hr.salary.rule',
        'structure_id',
        string='Các rule tính lương'
    )

    notes = fields.Text(
        string='Ghi chú'
    )

    active = fields.Boolean(
        string='Hoạt động',
        default=True
    )

    @api.model
    def get_default_structure(self):
        """Get default salary structure"""
        structure = self.search([
            ('company_id', '=', self.env.company.id),
            ('active', '=', True),
        ], limit=1)
        return structure

    def get_rules_by_category(self, category):
        """Get rules by category (allowance, deduction, etc.)"""
        return self.rule_ids.filtered(lambda r: r.category == category)

    def get_gross_rules(self):
        """Get rules that contribute to gross salary"""
        return self.rule_ids.filtered(lambda r: r.category in ['basic', 'allowance'])

    def get_deduction_rules(self):
        """Get all deduction rules"""
        return self.rule_ids.filtered(lambda r: r.category == 'deduction')

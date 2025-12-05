from odoo import models, fields, api


class HRSalaryGrade(models.Model):
    """
    Hệ số lương theo vị trí và level
    Grade = Position + Level + Base salary + Coefficient
    """
    _name = 'hr.salary.grade'
    _description = 'Salary Grade (Hệ số lương)'
    _rec_name = 'name'

    name = fields.Char(
        string='Tên hệ số lương',
        compute='_compute_name',
        store=True
    )

    job_id = fields.Many2one(
        'hr.job',
        string='Chức danh',
        required=True,
        ondelete='cascade'
    )

    level = fields.Selection(
        [
            ('intern', 'Thực tập sinh'),
            ('junior', 'Junior'),
            ('middle', 'Middle'),
            ('senior', 'Senior'),
            ('lead', 'Lead'),
            ('manager', 'Manager'),
        ],
        string='Level',
        required=True
    )

    base_salary = fields.Monetary(
        string='Lương cơ bản',
        required=True,
        currency_field='currency_id',
        help='Lương cơ bản cho level này'
    )

    coefficient = fields.Float(
        string='Hệ số lương',
        default=1.0,
        required=True,
        help='Hệ số nhân lên lương cơ bản (1.0 = 100%)'
    )

    allowance = fields.Monetary(
        string='Phụ cấp',
        default=0,
        currency_field='currency_id',
        help='Phụ cấp cố định theo level'
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Tiền tệ',
        default=lambda self: self.env.company.currency_id
    )

    company_id = fields.Many2one(
        'res.company',
        string='Công ty',
        default=lambda self: self.env.company
    )

    notes = fields.Text(
        string='Ghi chú'
    )

    @api.depends('job_id', 'level', 'base_salary')
    def _compute_name(self):
        """Compute display name"""
        for record in self:
            if record.job_id:
                level_name = dict(record._fields['level'].selection).get(record.level, record.level)
                record.name = f"{record.job_id.name} - {level_name}"
            else:
                record.name = "New Grade"

    @api.model
    def get_grade_for_employee(self, employee):
        """Get salary grade for specific employee"""
        grade = self.search([
            ('job_id', '=', employee.job_id.id),
        ], limit=1)
        return grade

    def calculate_salary_for_days(self, worked_days):
        """Calculate salary based on worked days"""
        salary_per_day = (self.base_salary * self.coefficient) / 26.0
        return salary_per_day * worked_days

from odoo import models, fields, api


class HRSalaryRule(models.Model):
    _name = 'hr.salary.rule'
    _description = 'Salary Rule (Công thức tính lương)'
    _order = 'sequence, id'

    name = fields.Char(string='Tên rule', required=True)

    code = fields.Char(
        string='Mã code',
        required=True,
        unique=True,
        help='Identifier duy nhất cho rule này'
    )

    structure_id = fields.Many2one(
        'hr.salary.structure',
        string='Cấu trúc lương',
        required=True,
        ondelete='cascade'
    )

    category = fields.Selection(
        [
            ('basic', 'Lương cơ bản'),
            ('allowance', 'Phụ cấp'),
            ('deduction', 'Khoản trừ'),
            ('insurance', 'Bảo hiểm'),
            ('tax', 'Thuế'),
        ],
        string='Loại',
        required=True,
        default='basic'
    )

    sequence = fields.Integer(
        string='Thứ tự',
        default=1,
        help='Thứ tự tính toán'
    )

    description = fields.Text(string='Mô tả')

    company_id = fields.Many2one(
        'res.company',
        string='Công ty',
        default=lambda self: self.env.company
    )

    active = fields.Boolean(string='Hoạt động', default=True)

    working_days_base = fields.Float(
        string="Ngày công chuẩn",
        default=22.0,
        help="Số ngày công dùng để chia khi tính lương/phụ cấp"
    )

    def compute(self, payslip, localdict):
        self.ensure_one()
        result = 0

        worked_days = localdict.get('worked_days', 0)
        base = self.working_days_base or 22.0  # fallback

        if self.category == 'basic':
            base_salary = localdict.get('base_salary', 0)
            coefficient = localdict.get('coefficient', 1)
            result = base_salary * coefficient * (worked_days / base)

        elif self.category == 'allowance':
            allowance = localdict.get('allowance', 0)
            result = allowance * (worked_days / base)

        elif self.category in ['deduction', 'insurance', 'tax']:
            result = 0

        return result

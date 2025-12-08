from odoo import models, fields, api


class HRSalaryRule(models.Model):
    _name = 'hr.salary.rule'
    _description = 'Salary Rule (Công thức tính lương)'
    _order = 'sequence, id'

    name = fields.Char(
        string='Tên rule',
        required=True
    )

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
        help='Thứ tự tính toán (thứ tự từ nhỏ đến lớn)'
    )

    description = fields.Text(
        string='Mô tả'
    )

    company_id = fields.Many2one(
        'res.company',
        string='Công ty',
        default=lambda self: self.env.company
    )

    active = fields.Boolean(
        string='Hoạt động',
        default=True
    )

    def compute(self, payslip, localdict):
      self.ensure_one()
      result = 0

      if self.category == 'basic':
        base_salary = localdict.get('base_salary', 0)
        coefficient = localdict.get('coefficient', 1)
        worked_days = localdict.get('worked_days', 0)

        # Công thức bạn yêu cầu
        result = base_salary * coefficient * (worked_days / 26.0)

      elif self.category == 'allowance':
        worked_days = localdict.get('worked_days', 0)
        allowance = localdict.get('allowance', 0)

        # Công thức phụ cấp
        result = allowance * (worked_days / 26.0)

      elif self.category in ['deduction', 'insurance', 'tax']:
        result = 0

      return result
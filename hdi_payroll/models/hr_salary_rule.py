from odoo import models, fields, api


class HRSalaryRule(models.Model):
    """
    Công thức tính lương - mỗi rule tính một phần (lương cơ bản, phụ cấp, trừ, BHXH...)
    """
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

    python_code = fields.Text(
        string='Python Code',
        help="Viết code Python, gán kết quả vào biến result"
    )

    active = fields.Boolean(
        string='Hoạt động',
        default=True
    )

    def compute(self, payslip, localdict):
        """Compute amount for this rule"""
        self.ensure_one()

        result = 0

        # Nếu rule có Python code
        if self.description and 'result' in self.description:
            result = self._execute_python_code(self.description, localdict)

        # Nếu không có python code → fallback theo category
        else:
            if self.category == 'basic':
                result = localdict.get('base_salary', 0) * localdict.get(
                    'coefficient', 1)
            elif self.category == 'allowance':
                result = 0
            elif self.category == 'deduction':
                result = 0

        return result

    @api.model
    def _execute_python_code(self, code, localdict):
        """Safely execute Python code for calculation"""
        try:
            safe_globals = {
                '__builtins__': {
                    'abs': abs,
                    'round': round,
                    'min': min,
                    'max': max,
                    'sum': sum,
                    'len': len,
                }
            }
            exec(code, safe_globals, localdict)
        except Exception as e:
            return 0
        return localdict.get('result', 0)



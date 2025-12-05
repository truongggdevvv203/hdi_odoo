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

    # Conditions & computation
    python_condition = fields.Text(
        string='Điều kiện Python',
        default='True',
        help='Python code để xác định có áp dụng rule hay không'
    )

    python_compute = fields.Text(
        string='Công thức Python',
        required=True,
        default='result = 0',
        help="""Python code để tính toán kết quả.
        Biến có sẵn:
        - employee: đối tượng employee
        - payslip: đối tượng payslip
        - worked_days: số ngày công
        - paid_leave: ngày nghỉ có lương
        - unpaid_leave: ngày nghỉ không lương
        - base_salary: lương cơ bản
        - coefficient: hệ số lương
        Luôn kết thúc bằng: result = [giá trị]
        """
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

    @api.model
    def _execute_python_code(self, code, localdict):
        """Safely execute Python code for calculation"""
        try:
            exec(code, {"__builtins__": {}}, localdict)
        except Exception as e:
            raise ValueError(f"Error in Python code: {str(e)}")
        return localdict.get('result', 0)

    def compute(self, payslip, localdict):
        """
        Compute the amount for this rule
        localdict: dictionary containing all variables
        """
        if not self.active:
            return 0

        # Check condition
        if self.python_condition:
            try:
                if not self._execute_python_code(self.python_condition, localdict):
                    return 0
            except:
                return 0

        # Execute computation
        return self._execute_python_code(self.python_compute, localdict)

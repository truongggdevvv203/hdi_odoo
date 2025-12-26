# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.tools.safe_eval import safe_eval
from odoo.exceptions import UserError, ValidationError


class HrSalaryRule(models.Model):
    _name = 'hr.salary.rule'
    _description = 'Quy tắc tính lương'
    _order = 'sequence, id'

    name = fields.Char('Tên quy tắc', required=True, translate=True)
    code = fields.Char(
        'Mã',
        required=True,
        help='Mã này được dùng trong công thức Python để tham chiếu. VD: BASIC, ALW, DED...'
    )
    sequence = fields.Integer('Thứ tự', default=5, help='Thứ tự tính toán trong payslip')
    
    active = fields.Boolean('Hoạt động', default=True)
    
    # Nhóm
    category_id = fields.Many2one('hr.salary.rule.category', 'Nhóm', required=True)
    
    # Cấu trúc lương áp dụng
    struct_id = fields.Many2one('hr.payroll.structure', 'Cấu trúc lương')
    
    # ==================== ĐIỀU KIỆN ÁP DỤNG ====================
    condition_select = fields.Selection([
        ('none', 'Luôn đúng'),
        ('range', 'Khoảng thời gian'),
        ('python', 'Biểu thức Python')
    ], 'Điều kiện', default='none', required=True)
    
    condition_range = fields.Char('Khoảng', help='Vd: contract.wage >= 5000000')
    condition_python = fields.Text(
        'Điều kiện Python',
        default='result = True',
        help='Kết quả = True thì áp dụng rule này. Có thể dùng: employee, contract, payslip, worked_days...'
    )
    
    # ==================== CÔNG THỨC TÍNH ====================
    amount_select = fields.Selection([
        ('fixed', 'Số tiền cố định'),
        ('percentage', 'Phần trăm'),
        ('code', 'Python Code')
    ], 'Loại tính toán', default='code', required=True)
    
    amount_fixed = fields.Float('Số tiền cố định', digits='Payroll')
    amount_percentage = fields.Float('Phần trăm (%)', help='Phần trăm của rule khác')
    amount_percentage_base = fields.Char(
        'Căn cứ tính %',
        help='Mã của rule khác làm cơ sở. VD: BASIC'
    )
    
    amount_python_compute = fields.Text(
        'Công thức Python',
        default="""# Có thể sử dụng:
# - employee: hr.employee
# - contract: hr.contract
# - payslip: hr.payslip
# - worked_days: dict {code: worked_days_line}
# - inputs: dict {code: input_line}
# - categories: dict {code: tổng theo category}
# - rules: dict {code: rule amount}

# Gán kết quả vào biến result
result = contract.wage
""",
        help='Viết code Python để tính. Kết quả gán vào biến "result"'
    )
    
    # ==================== HIỂN THỊ ====================
    appears_on_payslip = fields.Boolean(
        'Hiển thị trên phiếu lương',
        default=True,
        help='Nếu tắt, rule này vẫn được tính nhưng không hiện trên phiếu lương in ra'
    )
    
    note = fields.Text('Ghi chú')
    
    company_id = fields.Many2one('res.company', 'Công ty', default=lambda self: self.env.company)

    _sql_constraints = [
        ('code_uniq', 'unique(code, company_id)', 'Mã rule phải duy nhất trong công ty!')
    ]

    @api.constrains('amount_percentage')
    def _check_percentage(self):
        for rule in self:
            if rule.amount_select == 'percentage' and (rule.amount_percentage < 0 or rule.amount_percentage > 100):
                raise ValidationError(_('Phần trăm phải từ 0 đến 100'))

    def _satisfy_condition(self, localdict):
        """
        Kiểm tra điều kiện rule có được áp dụng không
        """
        self.ensure_one()
        
        if self.condition_select == 'none':
            return True
        elif self.condition_select == 'range':
            try:
                result = eval(self.condition_range, localdict)
                return bool(result)
            except Exception as e:
                raise UserError(_('Lỗi điều kiện range của rule %s: %s') % (self.code, str(e)))
        else:  # python
            try:
                safe_eval(self.condition_python, localdict, mode='exec', nocopy=True)
                return localdict.get('result', False)
            except Exception as e:
                raise UserError(_('Lỗi điều kiện Python của rule %s: %s') % (self.code, str(e)))

    def _compute_rule(self, localdict):
        """
        Tính toán số tiền của rule
        """
        self.ensure_one()
        
        if self.amount_select == 'fixed':
            return self.amount_fixed, 1.0, 100.0
            
        elif self.amount_select == 'percentage':
            # Lấy giá trị base
            base_code = self.amount_percentage_base
            if base_code and base_code in localdict.get('rules', {}):
                base_amount = localdict['rules'][base_code]
            else:
                base_amount = 0
            
            amount = base_amount * (self.amount_percentage / 100.0)
            return amount, 1.0, self.amount_percentage
            
        else:  # code
            try:
                safe_eval(self.amount_python_compute, localdict, mode='exec', nocopy=True)
                return localdict.get('result', 0), localdict.get('quantity', 1.0), localdict.get('rate', 100.0)
            except Exception as e:
                raise UserError(_('Lỗi tính toán Python của rule %s: %s\n\nCode:\n%s') % (
                    self.code, str(e), self.amount_python_compute
                ))

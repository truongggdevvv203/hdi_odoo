from odoo import models, fields


class HRPayslipLine(models.Model):
    """
    Dòng chi tiết trong phiếu lương
    Mỗi line đại diện cho kết quả tính toán của một salary rule
    """
    _name = 'hr.payslip.line'
    _description = 'Payslip Line (Dòng phiếu lương)'
    _order = 'payslip_id, sequence'

    payslip_id = fields.Many2one(
        'hr.payslip',
        string='Phiếu lương',
        required=True,
        ondelete='cascade'
    )

    rule_id = fields.Many2one(
        'hr.salary.rule',
        string='Rule',
        required=True,
        ondelete='cascade'
    )

    name = fields.Char(
        string='Tên',
        required=True
    )

    code = fields.Char(
        string='Mã',
        required=True
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
        required=True
    )

    amount = fields.Monetary(
        string='Số tiền',
        required=True,
        currency_field='currency_id'
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Tiền tệ',
        default=lambda self: self.env.company.currency_id,
        related='payslip_id.currency_id',
        store=True
    )

    sequence = fields.Integer(
        string='Thứ tự',
        related='rule_id.sequence',
        store=True
    )

# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class HrLoan(models.Model):
    """Khoản vay / Tạm ứng lương"""
    _name = 'hr.loan'
    _description = 'Khoản vay / Tạm ứng'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char('Số chứng từ', required=True, copy=False, default='New', tracking=True)

    employee_id = fields.Many2one('hr.employee', 'Nhân viên', required=True, tracking=True)

    loan_type = fields.Selection([
        ('advance', 'Tạm ứng lương'),
        ('loan', 'Khoản vay')
    ], 'Loại', required=True, default='advance', tracking=True)

    # Số tiền
    amount = fields.Monetary('Số tiền vay/tạm ứng', required=True, tracking=True)
    balance = fields.Monetary('Còn nợ', compute='_compute_balance', store=True)
    paid_amount = fields.Monetary('Đã trả', compute='_compute_balance', store=True)

    # Thời gian
    date = fields.Date('Ngày', required=True, default=fields.Date.today, tracking=True)

    # Trả góp
    installment_method = fields.Selection([
        ('manual', 'Thủ công'),
        ('auto', 'Tự động từ lương')
    ], 'Phương thức trả', default='auto', required=True)

    installment_count = fields.Integer('Số kỳ trả', default=1)
    installment_amount = fields.Monetary('Số tiền mỗi kỳ', compute='_compute_installment_amount', store=True)

    # Chi tiết trả góp
    line_ids = fields.One2many('hr.loan.line', 'loan_id', 'Chi tiết trả góp')

    # Trạng thái
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('approved', 'Đã duyệt'),
        ('paid', 'Đã trả xong'),
        ('cancel', 'Đã hủy')
    ], 'Trạng thái', default='draft', tracking=True)

    company_id = fields.Many2one('res.company', 'Công ty', default=lambda self: self.env.company, required=True)
    currency_id = fields.Many2one(related='company_id.currency_id')

    note = fields.Text('Ghi chú')

    @api.depends('amount', 'installment_count')
    def _compute_installment_amount(self):
        for loan in self:
            if loan.installment_count > 0:
                loan.installment_amount = loan.amount / loan.installment_count
            else:
                loan.installment_amount = loan.amount

    @api.depends('line_ids.paid')
    def _compute_balance(self):
        for loan in self:
            loan.paid_amount = sum(loan.line_ids.filtered('paid').mapped('amount'))
            loan.balance = loan.amount - loan.paid_amount
            # Chỉ chuyển sang 'paid' nếu có giá trị khoản vay > 0
            # và số tiền đã trả >= tổng khoản vay. Tránh trường hợp mới tạo (amount=0)
            if loan.amount and loan.paid_amount >= loan.amount and loan.state != 'paid':
                loan.state = 'paid'
            # Nếu trước đó là 'paid' nhưng bây giờ chưa đủ trả, trả về 'approved'
            elif loan.state == 'paid' and loan.paid_amount < loan.amount:
                loan.state = 'approved'

    def action_approve(self):
        """Duyệt khoản vay"""
        for loan in self:
            if loan.state != 'draft':
                continue

            # Tạo sequence number
            if loan.name == 'New':
                seq = 'hr.loan.advance' if loan.loan_type == 'advance' else 'hr.loan'
                loan.name = self.env['ir.sequence'].next_by_code(seq) or 'New'

            # Tạo các kỳ trả góp
            if loan.installment_method == 'auto' and not loan.line_ids:
                loan._create_installment_lines()

            loan.state = 'approved'

    def action_cancel(self):
        """Hủy khoản vay"""
        # Kiểm tra đã trả chưa
        if any(loan.paid_amount > 0 for loan in self):
            raise ValidationError(_('Không thể hủy khoản vay đã bắt đầu trả!'))
        return self.write({'state': 'cancel'})

    def action_draft(self):
        """Chuyển về nháp"""
        return self.write({'state': 'draft'})

    def _create_installment_lines(self):
        """Tạo các kỳ trả góp tự động"""
        self.ensure_one()

        lines = []
        for i in range(self.installment_count):
            lines.append({
                'loan_id': self.id,
                'installment_number': i + 1,
                'amount': self.installment_amount,
                'paid': False,
            })

        self.env['hr.loan.line'].create(lines)

    @api.model
    def create(self, vals):
        if 'state' not in vals:
            vals['state'] = 'draft'

        if vals.get('name', 'New') == 'New':
            loan_type = vals.get('loan_type', 'advance')
            seq_code = 'hr.loan.advance' if loan_type == 'advance' else 'hr.loan'
            vals['name'] = self.env['ir.sequence'].next_by_code(seq_code) or 'New'
        return super().create(vals)


class HrLoanLine(models.Model):
    _name = 'hr.loan.line'
    _description = 'Chi tiết trả góp'
    _order = 'installment_number'

    loan_id = fields.Many2one('hr.loan', 'Khoản vay', required=True, ondelete='cascade')

    installment_number = fields.Integer('Kỳ thứ', required=True)
    amount = fields.Monetary('Số tiền', required=True)

    paid = fields.Boolean('Đã trả', default=False)
    paid_date = fields.Date('Ngày trả')
    installment_date = fields.Date('Ngày kỳ trả', required=True, tracking=True)

    payslip_id = fields.Many2one('hr.payslip', 'Phiếu lương trừ', readonly=True)

    company_id = fields.Many2one(related='loan_id.company_id', store=True)
    currency_id = fields.Many2one(related='loan_id.currency_id')

    note = fields.Char('Ghi chú')

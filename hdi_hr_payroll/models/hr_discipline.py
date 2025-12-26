# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class HrDiscipline(models.Model):
    """Quyết định kỷ luật"""
    _name = 'hr.discipline'
    _description = 'Quyết định kỷ luật'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char('Số quyết định', required=True, tracking=True)
    
    employee_id = fields.Many2one('hr.employee', 'Nhân viên', required=True, tracking=True)
    
    discipline_type = fields.Selection([
        ('warning', 'Cảnh cáo'),
        ('fine', 'Phạt tiền'),
        ('suspension', 'Đình chỉ'),
        ('other', 'Khác')
    ], 'Loại kỷ luật', required=True, default='warning')
    
    reason = fields.Text('Lý do', required=True)
    
    # Phạt tiền
    fine_amount = fields.Monetary('Số tiền phạt', default=0)
    
    date = fields.Date('Ngày quyết định', required=True, default=fields.Date.today, tracking=True)
    effective_date = fields.Date('Ngày hiệu lực', tracking=True)
    
    # Khấu trừ vào lương
    deduct_from_payslip = fields.Boolean('Trừ vào lương', default=True)
    payslip_id = fields.Many2one('hr.payslip', 'Phiếu lương đã trừ', readonly=True)
    is_deducted = fields.Boolean('Đã khấu trừ', compute='_compute_is_deducted', store=True)
    
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('approved', 'Đã duyệt'),
        ('cancel', 'Đã hủy')
    ], 'Trạng thái', default='draft', tracking=True)
    
    company_id = fields.Many2one('res.company', 'Công ty', default=lambda self: self.env.company)
    currency_id = fields.Many2one(related='company_id.currency_id')
    
    attachment_ids = fields.Many2many('ir.attachment', string='Tài liệu đính kèm')
    note = fields.Text('Ghi chú')

    @api.depends('payslip_id')
    def _compute_is_deducted(self):
        for rec in self:
            rec.is_deducted = bool(rec.payslip_id)

    def action_approve(self):
        """Duyệt quyết định"""
        return self.write({'state': 'approved'})

    def action_cancel(self):
        """Hủy quyết định"""
        return self.write({'state': 'cancel'})

    def action_draft(self):
        """Chuyển về nháp"""
        return self.write({'state': 'draft'})


class HrReward(models.Model):
    """Quyết định khen thưởng"""
    _name = 'hr.reward'
    _description = 'Quyết định khen thưởng'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'

    name = fields.Char('Số quyết định', required=True, tracking=True)
    
    employee_id = fields.Many2one('hr.employee', 'Nhân viên', required=True, tracking=True)
    
    reward_type = fields.Selection([
        ('achievement', 'Thành tích'),
        ('kpi', 'Đạt KPI'),
        ('bonus', 'Thưởng'),
        ('other', 'Khác')
    ], 'Loại khen thưởng', required=True, default='achievement')
    
    reason = fields.Text('Lý do', required=True)
    
    # Số tiền thưởng
    amount = fields.Monetary('Số tiền thưởng', required=True, default=0)
    
    date = fields.Date('Ngày quyết định', required=True, default=fields.Date.today, tracking=True)
    effective_date = fields.Date('Ngày hiệu lực', tracking=True)
    
    # Tính vào lương
    add_to_payslip = fields.Boolean('Cộng vào lương', default=True)
    is_taxable = fields.Boolean('Chịu thuế TNCN', default=True)
    payslip_id = fields.Many2one('hr.payslip', 'Phiếu lương đã cộng', readonly=True)
    is_paid = fields.Boolean('Đã chi trả', compute='_compute_is_paid', store=True)
    
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('approved', 'Đã duyệt'),
        ('paid', 'Đã chi trả'),
        ('cancel', 'Đã hủy')
    ], 'Trạng thái', default='draft', tracking=True)
    
    company_id = fields.Many2one('res.company', 'Công ty', default=lambda self: self.env.company)
    currency_id = fields.Many2one(related='company_id.currency_id')
    
    attachment_ids = fields.Many2many('ir.attachment', string='Tài liệu đính kèm')
    note = fields.Text('Ghi chú')

    @api.depends('payslip_id')
    def _compute_is_paid(self):
        for rec in self:
            rec.is_paid = bool(rec.payslip_id)

    def action_approve(self):
        """Duyệt quyết định"""
        return self.write({'state': 'approved'})

    def action_paid(self):
        """Đánh dấu đã chi trả"""
        return self.write({'state': 'paid'})

    def action_cancel(self):
        """Hủy quyết định"""
        return self.write({'state': 'cancel'})

    def action_draft(self):
        """Chuyển về nháp"""
        return self.write({'state': 'draft'})

from odoo import models, fields, api
from datetime import datetime, timedelta


class ShippingOrderReconciliation(models.TransientModel):
    _name = 'shipping.order.reconciliation'
    _description = 'Đối soát Công nợ Phiếu Gửi Hàng'

    # Date range filters
    date_from = fields.Date(
        string='Từ ngày',
        default=lambda self: datetime.now().replace(day=1).date(),
        help='Ngày bắt đầu'
    )
    
    date_to = fields.Date(
        string='Đến ngày',
        default=lambda self: datetime.now().date(),
        help='Ngày kết thúc'
    )

    # Payment status filter
    payment_status = fields.Selection([
        ('paid', 'Đã trả tiền'),
        ('waiting_payment', 'Chờ trả tiền'),
        ('unpaid', 'Chưa trả tiền'),
    ], string='Trạng thái thanh toán', default='paid', help='Lọc theo trạng thái thanh toán')

    # Current user
    user_id = fields.Many2one(
        'res.users',
        string='Người dùng',
        default=lambda self: self.env.user,
        readonly=True,
        help='Người dùng hiện tại'
    )

    # Stats
    total_orders = fields.Integer(
        string='Tổng đơn hàng',
        compute='_compute_stats',
        readonly=True
    )
    
    total_amount = fields.Integer(
        string='Tổng tiền (VND)',
        compute='_compute_stats',
        readonly=True
    )
    
    total_paid = fields.Integer(
        string='Tổng tiền đã trả (VND)',
        compute='_compute_stats',
        readonly=True
    )
    
    total_unpaid = fields.Integer(
        string='Tổng tiền còn lại (VND)',
        compute='_compute_stats',
        readonly=True
    )

    # Order lines for display
    order_line_ids = fields.One2many(
        'shipping.order',
        compute='_compute_order_lines',
        readonly=True,
        help='Danh sách đơn hàng theo bộ lọc'
    )

    @api.depends('date_from', 'date_to', 'payment_status', 'user_id')
    def _compute_order_lines(self):
        """Get orders based on filters"""
        for record in self:
            domain = [
                ('sender_id', '=', record.user_id.id),
                ('payment_status', '=', record.payment_status),
            ]
            
            # Add date filters based on payment_date
            if record.date_from:
                domain.append(('payment_date', '>=', record.date_from))
            if record.date_to:
                domain.append(('payment_date', '<=', record.date_to))
            
            # For unpaid orders, check created date instead
            if record.payment_status == 'unpaid':
                domain = [
                    ('sender_id', '=', record.user_id.id),
                    ('payment_status', '=', record.payment_status),
                ]
                if record.date_from:
                    domain.append(('create_date', '>=', f'{record.date_from} 00:00:00'))
                if record.date_to:
                    domain.append(('create_date', '<=', f'{record.date_to} 23:59:59'))
            
            orders = self.env['shipping.order'].search(domain, order='code desc')
            record.order_line_ids = orders

    @api.depends('date_from', 'date_to', 'payment_status', 'user_id')
    def _compute_stats(self):
        """Calculate statistics based on filters"""
        for record in self:
            # Get orders based on filters
            record._compute_order_lines()
            orders = record.order_line_ids
            
            record.total_orders = len(orders)
            record.total_amount = sum(orders.mapped('total_shipping_fee') or [0])
            record.total_paid = sum(orders.mapped('paid_amount') or [0])
            record.total_unpaid = record.total_amount - record.total_paid

    def action_view_details(self):
        """Open detail list view for reconciliation"""
        self._compute_order_lines()
        orders = self.order_line_ids
        
        domain = [('id', 'in', orders.ids)] if orders else []
        
        return {
            'name': f'Danh sách {self.payment_status}',
            'type': 'ir.actions.act_window',
            'res_model': 'shipping.order',
            'view_mode': 'list,form',
            'domain': domain,
            'context': {'default_sender_id': self.user_id.id}
        }

    def action_export_reconciliation(self):
        """Export reconciliation report (placeholder for future enhancement)"""
        self._compute_stats()
        return {
            'type': 'ir.actions.client',
            'tag': 'reload'
        }

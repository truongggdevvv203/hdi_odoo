from odoo import models, fields, api
from datetime import datetime, timedelta


class ShippingOrderReconciliationLine(models.TransientModel):
    _name = 'shipping.order.reconciliation.line'
    _description = 'Dòng Đối soát Công nợ'

    reconciliation_id = fields.Many2one(
        'shipping.order.reconciliation',
        string='Đối soát',
        ondelete='cascade'
    )

    order_code = fields.Char(string='Số phiếu')
    sender_name = fields.Char(string='Người gửi')
    receiver_name = fields.Char(string='Người nhận')
    receiver_phone = fields.Char(string='Số điện thoại')
    total_shipping_fee = fields.Integer(string='Tiền cước (VND)')
    paid_amount = fields.Integer(string='Đã trả (VND)')
    unpaid_amount = fields.Integer(string='Còn lại (VND)')
    payment_status = fields.Selection([
        ('paid', 'Đã trả tiền'),
        ('waiting_payment', 'Chờ trả tiền'),
        ('unpaid', 'Chưa trả tiền'),
    ], string='Trạng thái thanh toán')
    payment_date = fields.Date(string='Ngày thanh toán')


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

    # Reconciliation lines
    reconciliation_line_ids = fields.One2many(
        'shipping.order.reconciliation.line',
        'reconciliation_id',
        string='Chi tiết đơn hàng',
        compute='_compute_reconciliation_lines',
        readonly=True,
        store=False
    )

    # Stats
    total_orders = fields.Integer(
        string='Tổng đơn hàng',
        compute='_compute_stats',
        readonly=True,
        store=False
    )
    
    total_amount = fields.Integer(
        string='Tổng tiền (VND)',
        compute='_compute_stats',
        readonly=True,
        store=False
    )
    
    total_paid = fields.Integer(
        string='Tổng tiền đã trả (VND)',
        compute='_compute_stats',
        readonly=True,
        store=False
    )
    
    total_unpaid = fields.Integer(
        string='Tổng tiền còn lại (VND)',
        compute='_compute_stats',
        readonly=True,
        store=False
    )

    @api.depends('date_from', 'date_to', 'payment_status', 'user_id')
    def _get_filtered_orders(self):
        """Get orders based on filters"""
        domain = [
            ('sender_id', '=', self.user_id.id),
            ('payment_status', '=', self.payment_status),
        ]
        
        # Add date filters based on payment_date or create_date
        if self.payment_status == 'unpaid':
            # For unpaid, use create_date
            if self.date_from:
                domain.append(('create_date', '>=', f'{self.date_from} 00:00:00'))
            if self.date_to:
                domain.append(('create_date', '<=', f'{self.date_to} 23:59:59'))
        else:
            # For paid/waiting, use payment_date
            if self.date_from:
                domain.append(('payment_date', '>=', self.date_from))
            if self.date_to:
                domain.append(('payment_date', '<=', self.date_to))
        
        return self.env['shipping.order'].search(domain, order='code desc')

    @api.depends('date_from', 'date_to', 'payment_status', 'user_id')
    def _compute_reconciliation_lines(self):
        """Populate reconciliation lines from filtered orders"""
        for record in self:
            orders = record._get_filtered_orders()
            lines = []
            
            for order in orders:
                lines.append({
                    'order_code': order.code,
                    'sender_name': order.sender_name,
                    'receiver_name': order.receiver_name,
                    'receiver_phone': order.receiver_phone,
                    'total_shipping_fee': order.total_shipping_fee or 0,
                    'paid_amount': order.paid_amount or 0,
                    'unpaid_amount': (order.total_shipping_fee or 0) - (order.paid_amount or 0),
                    'payment_status': order.payment_status,
                    'payment_date': order.payment_date,
                })
            
            # Create in-memory lines (transient model)
            reconciliation_line_model = self.env['shipping.order.reconciliation.line']
            record.reconciliation_line_ids = [reconciliation_line_model.new(vals) for vals in lines]

    @api.depends('date_from', 'date_to', 'payment_status', 'user_id')
    def _compute_stats(self):
        """Calculate statistics based on filters"""
        for record in self:
            orders = record._get_filtered_orders()
            
            record.total_orders = len(orders)
            record.total_amount = sum(orders.mapped('total_shipping_fee') or [0])
            record.total_paid = sum(orders.mapped('paid_amount') or [0])
            record.total_unpaid = record.total_amount - record.total_paid

    def action_search_reconciliation(self):
        """Trigger stats/lines computation"""
        self.ensure_one()
        # Force recomputation
        self._compute_stats()
        self._compute_reconciliation_lines()
        return True

    def action_export_reconciliation(self):
        """Export reconciliation report (placeholder for future enhancement)"""
        self._compute_stats()
        return {
            'type': 'ir.actions.client',
            'tag': 'reload'
        }

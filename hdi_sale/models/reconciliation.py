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

    # Visibility fields for Odoo 17+ (replacing attrs)
    hide_no_data_alert = fields.Boolean(
        string='Ẩn cảnh báo không có dữ liệu',
        compute='_compute_visibility',
        readonly=True,
        store=False
    )
    
    hide_export_button = fields.Boolean(
        string='Ẩn nút xuất Excel',
        compute='_compute_visibility',
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
    def _compute_stats(self):
        """Calculate statistics based on filters"""
        for record in self:
            orders = record._get_filtered_orders()
            
            record.total_orders = len(orders)
            record.total_amount = sum(orders.mapped('total_shipping_fee') or [0])
            record.total_paid = sum(orders.mapped('paid_amount') or [0])
            record.total_unpaid = record.total_amount - record.total_paid

    @api.depends('total_orders')
    def _compute_visibility(self):
        """Compute visibility fields for UI elements"""
        for record in self:
            record.hide_no_data_alert = record.total_orders != 0
            record.hide_export_button = record.total_orders == 0

    def action_view_details(self):
        """Open detail list view for reconciliation"""
        self.ensure_one()
        # Force computation of stats and visibility
        self._compute_stats()
        self._compute_visibility()
        
        orders = self._get_filtered_orders()
        
        domain = [('id', 'in', orders.ids)] if orders else []
        
        status_label = dict(self._fields['payment_status'].selection).get(self.payment_status, self.payment_status)
        
        return {
            'name': f'Danh sách {status_label} ({self.date_from} → {self.date_to})',
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

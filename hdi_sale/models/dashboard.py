from odoo import models, fields, api


class ShippingOrderDashboard(models.TransientModel):
    _name = 'shipping.order.dashboard'
    _description = 'Bảng điều khiển Phiếu Gửi Hàng'

    # Thống kê tổng quan
    total_orders = fields.Integer(
        string='Tổng số đơn hàng',
        compute='_compute_statistics',
        readonly=True
    )
    
    delivered_orders = fields.Integer(
        string='Đơn phát thành công',
        compute='_compute_statistics',
        readonly=True
    )
    
    pending_orders = fields.Integer(
        string='Đơn chờ xử lý',
        compute='_compute_statistics',
        readonly=True
    )
    
    cancelled_orders = fields.Integer(
        string='Đơn đã hủy',
        compute='_compute_statistics',
        readonly=True
    )
    
    success_rate = fields.Float(
        string='Tỷ lệ thành công (%)',
        compute='_compute_statistics',
        readonly=True
    )
    
    current_user_id = fields.Many2one(
        'res.users',
        string='Người dùng hiện tại',
        default=lambda self: self.env.user,
        readonly=True
    )

    @api.depends()
    def _compute_statistics(self):
        """Calculate statistics for current user"""
        for record in self:
            current_user = self.env.user
            
            # Lấy tất cả đơn hàng của người dùng hiện tại
            domain = [('sender_id', '=', current_user.id)]
            
            total = self.env['shipping.order'].search_count(domain)
            delivered = self.env['shipping.order'].search_count(
                domain + [('state', '=', 'delivered')]
            )
            cancelled = self.env['shipping.order'].search_count(
                domain + [('state', '=', 'cancelled')]
            )
            pending = total - delivered - cancelled
            
            # Tính tỷ lệ thành công
            success_rate = (delivered / total * 100) if total > 0 else 0
            
            record.total_orders = total
            record.delivered_orders = delivered
            record.pending_orders = pending
            record.cancelled_orders = cancelled
            record.success_rate = success_rate

from odoo import models, fields, api
import json


class ShippingOrderDashboard(models.TransientModel):
    _name = 'shipping.order.dashboard'
    _description = 'Bảng điều khiển Phiếu Gửi Hàng'

    # Thống kê tổng quan - Cards trên đầu
    total_orders = fields.Integer(
        string='Tổng đơn hàng',
        compute='_compute_statistics',
        readonly=True
    )
    
    delivered_orders = fields.Integer(
        string='Phát thành công', 
        compute='_compute_statistics',
        readonly=True
    )
    
    pending_orders = fields.Integer(
        string='Đang vận chuyển',
        compute='_compute_statistics',
        readonly=True
    )
    
    cancelled_orders = fields.Integer(
        string='Đơn đã hủy',
        compute='_compute_statistics',
        readonly=True
    )
    
    success_rate = fields.Float(
        string='Tỷ lệ thành công',
        compute='_compute_statistics',
        readonly=True
    )

    # Thống kê chi tiết cho biểu đồ
    waiting_pickup_orders = fields.Integer(
        string='Chờ lấy hàng',
        compute='_compute_detailed_statistics',
        readonly=True
    )
    
    in_transit_orders = fields.Integer(
        string='Đang vận chuyển',
        compute='_compute_detailed_statistics', 
        readonly=True
    )
    
    return_orders = fields.Integer(
        string='Đơn hoàn',
        compute='_compute_detailed_statistics',
        readonly=True
    )
    
    forwarded_orders = fields.Integer(
        string='Phát tiếp',
        compute='_compute_detailed_statistics',
        readonly=True
    )
    
    # Data cho biểu đồ
    chart_data = fields.Text(
        string='Dữ liệu biểu đồ',
        compute='_compute_chart_data',
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
        """Calculate main statistics for top cards"""
        for record in self:
            current_user = self.env.user
            domain = [('sender_id', '=', current_user.id)]
            
            total = self.env['shipping.order'].search_count(domain)
            delivered = self.env['shipping.order'].search_count(
                domain + [('state', '=', 'delivered')]
            )
            cancelled = self.env['shipping.order'].search_count(
                domain + [('state', '=', 'cancelled')]
            )
            pending = self.env['shipping.order'].search_count(
                domain + [('state', 'in', ['waiting_pickup', 'in_transit', 'forwarded'])]
            )
            
            success_rate = (delivered / total * 100) if total > 0 else 0
            
            record.total_orders = total
            record.delivered_orders = delivered
            record.pending_orders = pending
            record.cancelled_orders = cancelled
            record.success_rate = success_rate

    @api.depends()
    def _compute_detailed_statistics(self):
        """Calculate detailed statistics for charts"""
        for record in self:
            current_user = self.env.user
            domain = [('sender_id', '=', current_user.id)]
            
            record.waiting_pickup_orders = self.env['shipping.order'].search_count(
                domain + [('state', '=', 'waiting_pickup')]
            )
            record.in_transit_orders = self.env['shipping.order'].search_count(
                domain + [('state', '=', 'in_transit')]
            )
            record.return_orders = self.env['shipping.order'].search_count(
                domain + [('state', 'in', ['return_approved', 'return_completed'])]
            )
            record.forwarded_orders = self.env['shipping.order'].search_count(
                domain + [('state', '=', 'forwarded')]
            )

    @api.depends()
    def _compute_chart_data(self):
        """Generate chart data for pie chart"""
        for record in self:
            # Recalculate statistics
            record._compute_statistics()
            record._compute_detailed_statistics()
            
            # Pie chart data
            pie_data = [
                {'label': 'Phát thành công', 'value': record.delivered_orders, 'color': '#28a745'},
                {'label': 'Chờ lấy hàng', 'value': record.waiting_pickup_orders, 'color': '#ffc107'},
                {'label': 'Đang vận chuyển', 'value': record.in_transit_orders, 'color': '#17a2b8'},
                {'label': 'Phát tiếp', 'value': record.forwarded_orders, 'color': '#fd7e14'},
                {'label': 'Đơn hoàn', 'value': record.return_orders, 'color': '#6c757d'},
                {'label': 'Đã hủy', 'value': record.cancelled_orders, 'color': '#dc3545'},
            ]
            
            record.chart_data = json.dumps({
                'pie_data': pie_data,
                'total': record.total_orders
            })

    def action_refresh_dashboard(self):
        """Refresh dashboard data"""
        self._compute_statistics()
        self._compute_detailed_statistics()
        self._compute_chart_data()
        return {
            'type': 'ir.actions.client',
            'tag': 'reload'
        }

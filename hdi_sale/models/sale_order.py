from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # Custom fields for HDI
    hdi_order_type = fields.Selection([
        ('standard', 'Đơn hàng tiêu chuẩn'),
        ('quick', 'Đơn hàng nhanh'),
        ('bulk', 'Đơn hàng số lượng lớn'),
    ], string='Loại đơn hàng', default='standard', tracking=True)
    
    hdi_priority = fields.Selection([
        ('low', 'Thấp'),
        ('medium', 'Trung bình'),
        ('high', 'Cao'),
        ('urgent', 'Khẩn cấp'),
    ], string='Độ ưu tiên', default='medium', tracking=True)
    
    hdi_sale_channel = fields.Selection([
        ('direct', 'Bán trực tiếp'),
        ('online', 'Bán online'),
        ('retail', 'Bán lẻ'),
    ], string='Kênh bán hàng', default='direct')
    
    hdi_notes = fields.Text(string='Ghi chú nội bộ')
    
    @api.onchange('hdi_order_type')
    def _onchange_order_type(self):
        """Change order state based on order type"""
        if self.hdi_order_type == 'quick':
            self.hdi_priority = 'high'

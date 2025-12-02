from odoo import models, fields


class ShipmentItem(models.Model):
    _name = 'shipment.item'
    _description = 'Shipment Item'

    order_id = fields.Many2one('shipping.order', string='Đơn hàng', required=True, ondelete='cascade')
    
    name = fields.Char(string='Mô tả hàng hóa', required=True)
    category = fields.Selection([
        ('document', 'Tài liệu'),
        ('parcel', 'Bưu phẩm'),
        ('fragile', 'Dễ vỡ'),
        ('electronic', 'Điện tử'),
        ('other', 'Khác'),
    ], string='Loại hàng hóa', default='parcel')
    
    quantity = fields.Integer(string='Số lượng', default=1)
    weight = fields.Float(string='Trọng lượng (kg)', required=True)
    value = fields.Float(string='Giá trị (VND)')
    
    sequence = fields.Integer(string='Thứ tự', default=10)

    class Meta:
        ordering = ['sequence']

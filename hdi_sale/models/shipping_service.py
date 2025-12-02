from odoo import models, fields


class ShippingService(models.Model):
    _name = 'shipping.service'
    _description = 'Shipping Service'

    name = fields.Char(string='Tên dịch vụ', required=True)
    code = fields.Char(string='Mã dịch vụ', required=True, unique=True)
    base_price = fields.Float(string='Giá cơ bản (VND)', required=True)
    description = fields.Text(string='Mô tả')
    active = fields.Boolean(string='Kích hoạt', default=True)

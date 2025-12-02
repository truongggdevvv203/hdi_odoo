from odoo import models, fields, api
from datetime import datetime


class ShippingService(models.Model):
    _name = 'shipping.service'
    _description = 'Shipping Service (FUTA Express)'

    name = fields.Char(string='Tên dịch vụ', required=True)
    code = fields.Char(string='Mã dịch vụ', required=True, unique=True)
    description = fields.Text(string='Mô tả')
    base_price = fields.Float(string='Giá cơ sở (VND)', required=True)
    estimated_days = fields.Integer(string='Số ngày dự kiến')
    active = fields.Boolean(string='Kích hoạt', default=True)

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Mã dịch vụ phải duy nhất'),
    ]

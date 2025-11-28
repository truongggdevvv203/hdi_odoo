from odoo import models, fields


class HdiProductType(models.Model):
    _name = 'hdi.product.type'
    _description = 'HDI Product Type'

    name = fields.Char(string='Tên loại sản phẩm', required=True)
    code = fields.Char(string='Mã', required=True)
    active = fields.Boolean(string='Active', default=True)

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Mã loại phải duy nhất'),
    ]

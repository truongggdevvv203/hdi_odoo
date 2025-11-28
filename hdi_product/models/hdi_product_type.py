from odoo import models, fields


class HdiProductType(models.Model):
    _name = 'hdi.product.type'
    _description = 'HDI Product Type'

    name = fields.Char(string='Loại', required=True)
    code = fields.Selection(
        [('product', 'Storable Product'), ('consu', 'Consumable'), ('service', 'Service')],
        string='Mã (map tới product.template.type)',
        required=True,
        help='Giá trị code sẽ map tới field `product.template.type` (product/consu/service)'
    )
    active = fields.Boolean(string='Active', default=True)

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Mã loại phải duy nhất'),
    ]

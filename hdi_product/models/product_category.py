from odoo import models, fields

class ProductCategory(models.Model):
    _inherit = 'product.category'

    hdi_description = fields.Text("Category Description")
    hdi_image = fields.Binary("Image")

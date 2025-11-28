from odoo import models, fields

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    hdi_brand = fields.Char("Brand")
    hdi_warranty_months = fields.Integer("Warranty (months)")
    hdi_note = fields.Text("Additional Notes")

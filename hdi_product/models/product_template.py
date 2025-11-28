from odoo import models, fields, api

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    hdi_brand = fields.Char("Brand")
    hdi_warranty_months = fields.Integer("Warranty (months)")
    hdi_note = fields.Text("Additional Notes")
    hdi_type_id = fields.Many2one(
        'hdi.product.type',
        string='Loại sản phẩm (HDI)',
        help='Quản lý loại sản phẩm bởi HDI (synchronize with core field `type`).',
    )

    @api.onchange('hdi_type_id')
    def _onchange_hdi_type_id(self):
        for rec in self:
            if rec.hdi_type_id and rec.hdi_type_id.code:
                # propagate to core selection field
                rec.type = rec.hdi_type_id.code

    @api.onchange('type')
    def _onchange_type(self):
        """When core `type` changes, try to find corresponding HDI type by code."""
        for rec in self:
            if rec.type:
                t = self.env['hdi.product.type'].search([('code', '=', rec.type)], limit=1)
                rec.hdi_type_id = t.id or False

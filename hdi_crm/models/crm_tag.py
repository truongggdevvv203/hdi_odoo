from odoo import models, fields


class CrmTag(models.Model):
    _inherit = 'crm.tag'

    name = fields.Char(
        string='Tag Name',
        required=True,
    )
    
    color = fields.Integer(string='Color')

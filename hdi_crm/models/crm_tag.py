from odoo import models, fields


class CrmTag(models.Model):
    _name = 'crm.tag'
    _description = 'CRM Tag'

    name = fields.Char(
        string='Tag Name',
        required=True,
    )
    
    color = fields.Integer(string='Color')

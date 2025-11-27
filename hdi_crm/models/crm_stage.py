from odoo import models, fields, api


class CrmStage(models.Model):
    _inherit = 'crm.stage'

    name = fields.Char(
        string='Stage Name',
        required=True,
    )
    
    sequence = fields.Integer(
        string='Sequence',
        default=1,
    )
    
    is_won = fields.Boolean(
        string='Is Won Stage',
        default=False,
    )
    
    is_lost = fields.Boolean(
        string='Is Lost Stage',
        default=False,
    )
    
    probability = fields.Integer(
        string='Probability (%)',
        default=0,
    )
    
    description = fields.Text(string='Description')


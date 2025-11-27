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


class CrmSource(models.Model):
    _name = 'crm.source'
    _description = 'Lead Source'

    name = fields.Char(
        string='Source Name',
        required=True,
    )


class CrmIndustry(models.Model):
    _name = 'crm.industry'
    _description = 'Industry'

    name = fields.Char(
        string='Industry Name',
        required=True,
    )


class CrmLostReason(models.Model):
    _name = 'crm.lost.reason'
    _description = 'Lost Reason'

    name = fields.Char(
        string='Lost Reason',
        required=True,
    )



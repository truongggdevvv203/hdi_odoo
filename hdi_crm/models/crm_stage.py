from odoo import models, fields


class CrmStage(models.Model):
    _name = 'crm.stage'
    _description = 'CRM Stage'
    _order = 'sequence'

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


class CrmTag(models.Model):
    _name = 'crm.tag'
    _description = 'CRM Tag'

    name = fields.Char(
        string='Tag Name',
        required=True,
    )
    
    color = fields.Integer(string='Color')


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


class CrmTeam(models.Model):
    _name = 'crm.team'
    _description = 'Sales Team'
    _order = 'sequence'

    name = fields.Char(
        string='Team Name',
        required=True,
    )
    
    sequence = fields.Integer(
        string='Sequence',
        default=10,
    )
    
    active = fields.Boolean(
        string='Active',
        default=True,
    )
    
    member_ids = fields.Many2many(
        'res.users',
        string='Team Members',
    )
    
    user_id = fields.Many2one(
        'res.users',
        string='Team Leader',
    )


class CrmLostReason(models.Model):
    _name = 'crm.lost.reason'
    _description = 'Lost Reason'

    name = fields.Char(
        string='Lost Reason',
        required=True,
    )

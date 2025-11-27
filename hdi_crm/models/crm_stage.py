from odoo import models, fields, api


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
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )
    
    member_ids = fields.Many2many(
        'res.users',
        string='Team Members',
        compute='_compute_member_ids',
    )
    
    user_id = fields.Many2one(
        'res.users',
        string='Team Leader',
    )
    
    member_warning = fields.Text(
        string='Member Warning',
        compute='_compute_member_warning',
    )
    
    is_membership_multi = fields.Boolean(
        string='Multiple Memberships',
        compute='_compute_is_membership_multi',
    )
    
    invoiced_target = fields.Monetary(
        string='Invoiced Target',
        currency_field='currency_id',
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
    )
    
    member_company_ids = fields.Many2many(
        'res.company',
        string='Member Companies',
        compute='_compute_member_company_ids',
    )

    crm_team_member_ids = fields.One2many(
        'crm.team.member',
        'crm_team_id',
        string='Team Members',
    )

    @api.depends('crm_team_member_ids')
    def _compute_member_ids(self):
        for team in self:
            team.member_ids = team.crm_team_member_ids.mapped('user_id')

    @api.depends('member_ids')
    def _compute_member_warning(self):
        for team in self:
            if not team.member_ids:
                team.member_warning = "Please add at least one member to this sales team."
            else:
                team.member_warning = False

    @api.depends('member_ids')
    def _compute_is_membership_multi(self):
        for team in self:
            companies = team.member_ids.mapped('company_id')
            team.is_membership_multi = len(companies) > 1

    @api.depends('member_ids')
    def _compute_member_company_ids(self):
        for team in self:
            team.member_company_ids = team.member_ids.mapped('company_id')


class CrmTeamMember(models.Model):
    _name = 'crm.team.member'
    _description = 'Sales Team Member'

    crm_team_id = fields.Many2one(
        'crm.team',
        string='Sales Team',
        required=True,
    )
    
    user_id = fields.Many2one(
        'res.users',
        string='User',
        required=True,
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        related='user_id.company_id',
        store=True,
    )
    
    active = fields.Boolean(
        string='Active',
        default=True,
    )


class CrmLostReason(models.Model):
    _name = 'crm.lost.reason'
    _description = 'Lost Reason'

    name = fields.Char(
        string='Lost Reason',
        required=True,
    )

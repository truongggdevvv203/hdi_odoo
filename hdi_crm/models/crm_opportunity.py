from odoo import models, fields, api
from datetime import datetime, timedelta


class CrmOpportunity(models.Model):
    _inherit = 'crm.opportunity'

    name = fields.Char(
        string='Opportunity',
        required=True,
        tracking=True,
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        tracking=True,
    )
    
    # Partner Information
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True,
        tracking=True,
    )
    
    partner_name = fields.Char(
        string='Customer Name',
        related='partner_id.name',
        readonly=True,
    )
    
    email_from = fields.Char(
        string='Email',
        related='partner_id.email',
        readonly=True,
    )
    
    phone = fields.Char(
        string='Phone',
        related='partner_id.phone',
        readonly=True,
    )
    
    # Opportunity Details
    description = fields.Text(
        string='Internal Notes',
        tracking=True,
    )
    
    stage_id = fields.Many2one(
        'crm.stage',
        string='Stage',
        group_expand='_read_group_stage_ids',
        tracking=True,
    )
    
    # Revenue
    expected_revenue = fields.Monetary(
        string='Expected Revenue',
        currency_field='company_currency',
        tracking=True,
    )
    
    probability = fields.Integer(
        string='Probability (%)',
        default=0,
        tracking=True,
    )
    
    weighted_revenue = fields.Monetary(
        string='Weighted Revenue',
        currency_field='company_currency',
        compute='_compute_weighted_revenue',
        store=True,
    )
    
    company_currency = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        readonly=True,
    )
    
    # Assignment
    user_id = fields.Many2one(
        'res.users',
        string='Assigned to',
        default=lambda self: self.env.user,
        tracking=True,
    )
    
    team_id = fields.Many2one(
        'crm.team',
        string='Sales Team',
        tracking=True,
    )
    
    # Classification
    tag_ids = fields.Many2many(
        'crm.tag',
        string='Tags',
        tracking=True,
    )
    
    # Timeline
    date_deadline = fields.Date(
        string='Expected Closing Date',
        tracking=True,
    )
    
    date_open = fields.Datetime(
        string='Opened',
        readonly=True,
    )
    
    date_closed = fields.Datetime(
        string='Closed',
        readonly=True,
    )
    
    # Status
    active = fields.Boolean(
        string='Active',
        default=True,
    )
    
    priority = fields.Selection(
        [
            ('0', 'Low'),
            ('1', 'Medium'),
            ('2', 'High'),
            ('3', 'Very High'),
        ],
        string='Priority',
        default='1',
        tracking=True,
    )
    
    # Related Records
    lead_id = fields.Many2one(
        'crm.lead',
        string='Related Lead',
    )
    
    lost_reason_id = fields.Many2one(
        'crm.lost.reason',
        string='Lost Reason',
        tracking=True,
    )
    
    @api.depends('expected_revenue', 'probability')
    def _compute_weighted_revenue(self):
        for record in self:
            record.weighted_revenue = (record.expected_revenue or 0) * (record.probability or 0) / 100
    
    def _read_group_stage_ids(self, stages, domain, order):
        return stages.search([], order=order)
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('date_open'):
                vals['date_open'] = fields.Datetime.now()
        return super().create(vals_list)
    
    def write(self, vals):
        # Close opportunity when stage changes to won
        if vals.get('stage_id'):
            stage = self.env['crm.stage'].browse(vals['stage_id'])
            if stage.is_won and not self.date_closed:
                vals['date_closed'] = fields.Datetime.now()
            elif stage.is_lost and not self.date_closed:
                vals['date_closed'] = fields.Datetime.now()
        return super().write(vals)
    
    def action_set_won(self):
        """Mark opportunity as won"""
        won_stage = self.env['crm.stage'].search([('is_won', '=', True)], limit=1)
        if won_stage:
            self.write({
                'stage_id': won_stage.id,
                'probability': 100,
                'date_closed': fields.Datetime.now(),
            })
    
    def action_set_lost(self, lost_reason_id=None):
        """Mark opportunity as lost"""
        lost_stage = self.env['crm.stage'].search([('is_lost', '=', True)], limit=1)
        if lost_stage:
            self.write({
                'stage_id': lost_stage.id,
                'probability': 0,
                'lost_reason_id': lost_reason_id,
                'date_closed': fields.Datetime.now(),
            })
    
    def action_create_sale_order(self):
        """Create a sale order from opportunity"""
        action = self.env.ref('sale.action_quotations_new').read()[0]
        action['context'] = {
            'default_partner_id': self.partner_id.id,
            'default_opportunity_id': self.id,
        }
        return action

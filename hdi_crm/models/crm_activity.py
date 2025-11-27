from odoo import models, fields, api


class CrmActivity(models.Model):
    _inherit = ['crm.activity', 'mail.thread', 'mail.activity.mixin']
    _order = 'date_scheduled desc'

    name = fields.Char(
        string='Activity',
        required=True,
        tracking=True,
    )
    
    activity_type = fields.Selection(
        [
            ('call', 'Call'),
            ('email', 'Email'),
            ('meeting', 'Meeting'),
            ('task', 'Task'),
            ('note', 'Note'),
            ('other', 'Other'),
        ],
        string='Activity Type',
        required=True,
        default='other',
        tracking=True,
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )
    
    # Related Records
    lead_id = fields.Many2one(
        'crm.lead',
        string='Lead',
    )
    
    opportunity_id = fields.Many2one(
        'crm.opportunity',
        string='Opportunity',
    )
    
    customer_id = fields.Many2one(
        'crm.customer',
        string='Customer',
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Contact',
    )
    
    # Activity Details
    description = fields.Text(
        string='Description',
        tracking=True,
    )
    
    date_scheduled = fields.Datetime(
        string='Scheduled Date',
        required=True,
        tracking=True,
    )
    
    date_completed = fields.Datetime(
        string='Completed Date',
        readonly=True,
    )
    
    # Assignment
    user_id = fields.Many2one(
        'res.users',
        string='Assigned to',
        default=lambda self: self.env.user,
        required=True,
        tracking=True,
    )
    
    # Status
    state = fields.Selection(
        [
            ('scheduled', 'Scheduled'),
            ('in_progress', 'In Progress'),
            ('completed', 'Completed'),
            ('cancelled', 'Cancelled'),
        ],
        string='Status',
        default='scheduled',
        tracking=True,
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
    
    outcome = fields.Text(
        string='Outcome',
        tracking=True,
    )
    
    @api.model_create_multi
    def create(self, vals_list):
        # Auto-set date_scheduled to now if not provided
        for vals in vals_list:
            if not vals.get('date_scheduled'):
                vals['date_scheduled'] = fields.Datetime.now()
        return super().create(vals_list)
    
    def action_mark_completed(self):
        """Mark activity as completed"""
        self.write({
            'state': 'completed',
            'date_completed': fields.Datetime.now(),
        })
    
    def action_mark_in_progress(self):
        """Mark activity as in progress"""
        self.write({'state': 'in_progress'})
    
    def action_mark_cancelled(self):
        """Mark activity as cancelled"""
        self.write({'state': 'cancelled'})

from odoo import models, fields, api
from datetime import datetime, timedelta


class CrmLeadEnhancement(models.Model):
    """Enhancement fields for Lead Management"""
    _name = 'crm.lead'
    _inherit = 'crm.lead'
    
    # Lead Classification
    lead_type = fields.Selection(
        [
            ('cold', 'Cold Lead'),
            ('warm', 'Warm Lead'),
            ('hot', 'Hot Lead'),
            ('qualified', 'Qualified'),
        ],
        string='Lead Type',
        tracking=True,
        help='Temperature of the lead - probability of conversion',
    )
    
    # Lead Scoring
    lead_score = fields.Integer(
        string='Lead Score',
        compute='_compute_lead_score',
        store=True,
        help='Automated score based on lead activity and engagement',
    )
    
    engagement_level = fields.Selection(
        [
            ('0', 'No Engagement'),
            ('1', 'Low'),
            ('2', 'Medium'),
            ('3', 'High'),
            ('4', 'Very High'),
        ],
        string='Engagement Level',
        default='1',
        tracking=True,
    )
    
    # Lead Qualification
    qualified_date = fields.Date(
        string='Qualified Date',
        readonly=True,
        help='Date when the lead was qualified',
    )
    
    qualification_reason = fields.Text(
        string='Qualification Reason',
        tracking=True,
    )
    
    # Lead Details
    job_title = fields.Char(
        string='Job Title',
        tracking=True,
    )
    
    decision_maker = fields.Boolean(
        string='Decision Maker',
        default=False,
        tracking=True,
    )
    
    budget_approved = fields.Boolean(
        string='Budget Approved',
        default=False,
        tracking=True,
    )
    
    number_of_employees = fields.Integer(
        string='Number of Employees',
        tracking=True,
    )
    
    company_annual_revenue = fields.Monetary(
        string='Company Annual Revenue',
        currency_field='company_currency',
        tracking=True,
    )
    
    # Lead Activities
    activity_count = fields.Integer(
        string='Activity Count',
        compute='_compute_activity_count',
        store=False,
    )
    
    last_activity_date = fields.Date(
        string='Last Activity Date',
        compute='_compute_last_activity_date',
        store=False,
    )
    
    days_since_last_activity = fields.Integer(
        string='Days Since Last Activity',
        compute='_compute_days_since_last_activity',
        store=False,
    )
    
    # Lead Status Tracking
    response_time = fields.Integer(
        string='Response Time (hours)',
        readonly=True,
        help='Time taken to respond to lead inquiry',
    )
    
    follow_up_scheduled = fields.Boolean(
        string='Follow-up Scheduled',
        compute='_compute_follow_up_scheduled',
        store=False,
    )
    
    # Lead Conversion
    conversion_probability = fields.Float(
        string='Conversion Probability',
        compute='_compute_conversion_probability',
        store=True,
    )
    
    estimated_conversion_value = fields.Monetary(
        string='Est. Conversion Value',
        currency_field='company_currency',
        compute='_compute_estimated_conversion_value',
        store=False,
    )
    
    @api.depends('lead_score', 'engagement_level', 'probability', 'budget_approved', 'decision_maker')
    def _compute_conversion_probability(self):
        """Calculate conversion probability based on multiple factors"""
        for lead in self:
            base_score = lead.probability or 0
            
            # Bonus points for qualifiers
            if lead.budget_approved:
                base_score += 10
            if lead.decision_maker:
                base_score += 15
            if lead.lead_type == 'qualified':
                base_score += 20
            
            # Engagement multiplier
            engagement_multiplier = 1.0
            if lead.engagement_level == '4':
                engagement_multiplier = 1.2
            elif lead.engagement_level == '3':
                engagement_multiplier = 1.15
            elif lead.engagement_level == '2':
                engagement_multiplier = 1.0
            else:
                engagement_multiplier = 0.8
            
            conversion_prob = min(100, base_score * engagement_multiplier)
            lead.conversion_probability = conversion_prob
    
    @api.depends('probability', 'expected_revenue', 'conversion_probability')
    def _compute_estimated_conversion_value(self):
        """Estimate value if lead is converted"""
        for lead in self:
            if lead.expected_revenue:
                lead.estimated_conversion_value = (lead.expected_revenue * lead.conversion_probability) / 100
            else:
                lead.estimated_conversion_value = 0.0
    
    @api.depends('probability', 'engagement_level', 'lead_type')
    def _compute_lead_score(self):
        """Compute lead score based on various factors"""
        for lead in self:
            score = 0
            
            # Base score from probability
            score += (lead.probability or 0) / 5
            
            # Engagement level bonus
            engagement_scores = {
                '0': 0,
                '1': 10,
                '2': 20,
                '3': 30,
                '4': 40,
            }
            score += engagement_scores.get(lead.engagement_level, 0)
            
            # Lead type bonus
            if lead.lead_type == 'qualified':
                score += 30
            elif lead.lead_type == 'hot':
                score += 25
            elif lead.lead_type == 'warm':
                score += 15
            
            # Tag count bonus
            score += len(lead.tag_ids) * 5
            
            lead.lead_score = int(min(100, score))
    
    def _compute_activity_count(self):
        """Count related activities"""
        for lead in self:
            activities = self.env['crm.activity'].search([
                '|',
                ('lead_id', '=', lead.id),
                ('email_from', 'like', lead.email_from) if lead.email_from else ('id', '=', -1),
            ])
            lead.activity_count = len(activities)
    
    def _compute_last_activity_date(self):
        """Get last activity date"""
        for lead in self:
            activities = self.env['crm.activity'].search([
                ('lead_id', '=', lead.id),
            ], order='date_scheduled desc', limit=1)
            lead.last_activity_date = activities.date_scheduled.date() if activities else None
    
    def _compute_days_since_last_activity(self):
        """Calculate days since last activity"""
        for lead in self:
            if lead.last_activity_date:
                days = (fields.Date.context_today(self) - lead.last_activity_date).days
                lead.days_since_last_activity = days
            else:
                lead.days_since_last_activity = 0
    
    def _compute_follow_up_scheduled(self):
        """Check if follow-up activity is scheduled"""
        for lead in self:
            follow_up = self.env['mail.activity'].search([
                ('res_model', '=', 'crm.lead'),
                ('res_id', '=', lead.id),
                ('state', '=', 'todo'),
            ], limit=1)
            lead.follow_up_scheduled = bool(follow_up)
    
    def action_qualify_lead(self):
        """Qualify the lead and set date"""
        self.write({
            'lead_type': 'qualified',
            'qualified_date': fields.Date.context_today(self),
            'probability': 50,
        })
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Lead Qualified',
                'message': 'Lead has been marked as qualified',
                'type': 'success',
                'sticky': False,
            }
        }
    
    def action_schedule_followup(self):
        """Schedule a follow-up activity"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Schedule Follow-up',
            'res_model': 'mail.activity',
            'view_mode': 'form',
            'context': {
                'default_res_model': 'crm.lead',
                'default_res_id': self.id,
                'default_activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
            },
            'target': 'new',
        }
    
    def action_view_activities(self):
        """View all activities related to this lead"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Lead Activities',
            'res_model': 'crm.activity',
            'view_mode': 'list,calendar,form',
            'domain': [('lead_id', '=', self.id)],
            'context': {
                'default_lead_id': self.id,
            },
        }
    
    def action_convert_and_notify(self):
        """Convert lead to opportunity and notify"""
        result = self.action_convert_to_opportunity()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Conversion Successful',
                'message': f'Lead {self.name} has been converted to Opportunity',
                'type': 'success',
                'sticky': False,
            }
        }

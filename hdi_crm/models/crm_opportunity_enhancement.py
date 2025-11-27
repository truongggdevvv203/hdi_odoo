from odoo import models, fields, api
from datetime import datetime, timedelta


class CrmOpportunityEnhancement(models.Model):
    """Enhancement fields for Opportunity Management"""
    _inherit = 'crm.opportunity'
    
    # Sales Process
    sales_stage = fields.Selection(
        [
            ('discovery', 'Discovery'),
            ('proposal', 'Proposal'),
            ('negotiation', 'Negotiation'),
            ('closing', 'Closing'),
            ('won', 'Won'),
            ('lost', 'Lost'),
        ],
        string='Sales Stage',
        tracking=True,
        help='Custom sales process stage',
    )
    
    # Opportunity Details
    opportunity_type = fields.Selection(
        [
            ('new_business', 'New Business'),
            ('expansion', 'Expansion'),
            ('renewal', 'Renewal'),
            ('upsell', 'Upsell'),
            ('cross_sell', 'Cross-sell'),
        ],
        string='Opportunity Type',
        tracking=True,
    )
    
    win_probability = fields.Integer(
        string='Win Probability (%)',
        compute='_compute_win_probability',
        store=True,
    )
    
    # Deal Information
    deal_size = fields.Selection(
        [
            ('small', 'Small (<$10K)'),
            ('medium', 'Medium ($10K-$50K)'),
            ('large', 'Large ($50K-$100K)'),
            ('enterprise', 'Enterprise (>$100K)'),
        ],
        string='Deal Size',
        compute='_compute_deal_size',
        store=False,
    )
    
    deal_value_category = fields.Float(
        string='Deal Value (USD)',
        compute='_compute_deal_value_category',
        store=False,
    )
    
    # Competition
    competitor = fields.Char(
        string='Main Competitor',
        tracking=True,
    )
    
    competitive_win_probability = fields.Integer(
        string='Win vs Competition (%)',
        default=50,
        tracking=True,
    )
    
    differentiation = fields.Text(
        string='Our Differentiation',
        tracking=True,
        help='Key factors that differentiate us from competitors',
    )
    
    # Deal Stages Tracking
    discovery_date = fields.Date(
        string='Discovery Date',
        tracking=True,
    )
    
    proposal_sent_date = fields.Date(
        string='Proposal Sent Date',
        tracking=True,
    )
    
    negotiation_start_date = fields.Date(
        string='Negotiation Start Date',
        tracking=True,
    )
    
    expected_close_date = fields.Date(
        string='Expected Close Date',
        tracking=True,
    )
    
    actual_close_date = fields.Date(
        string='Actual Close Date',
        readonly=True,
    )
    
    # Deal Contacts
    contact_ids = fields.Many2many(
        'res.partner',
        string='Deal Contacts',
        tracking=True,
        help='Key contacts involved in the deal',
    )
    
    primary_contact_id = fields.Many2one(
        'res.partner',
        string='Primary Contact',
        tracking=True,
    )
    
    decision_maker_id = fields.Many2one(
        'res.partner',
        string='Decision Maker',
        tracking=True,
    )
    
    # Deal Conditions
    special_conditions = fields.Text(
        string='Special Conditions',
        tracking=True,
        help='Any special terms or conditions for this deal',
    )
    
    requires_approval = fields.Boolean(
        string='Requires Approval',
        default=False,
        tracking=True,
    )
    
    approval_ids = fields.Many2many(
        'res.users',
        string='Approvers',
        tracking=True,
    )
    
    # Deal Performance
    days_in_pipeline = fields.Integer(
        string='Days in Pipeline',
        compute='_compute_days_in_pipeline',
        store=False,
    )
    
    stage_progress = fields.Float(
        string='Stage Progress (%)',
        compute='_compute_stage_progress',
        store=False,
    )
    
    close_probability = fields.Float(
        string='Close Probability',
        compute='_compute_close_probability',
        store=False,
    )
    
    # Expected Outcomes
    expected_cost = fields.Monetary(
        string='Expected Cost',
        currency_field='company_currency',
        tracking=True,
        help='Expected cost to close this deal',
    )
    
    expected_profit = fields.Monetary(
        string='Expected Profit',
        currency_field='company_currency',
        compute='_compute_expected_profit',
        store=False,
    )
    
    profit_margin_percentage = fields.Float(
        string='Profit Margin %',
        compute='_compute_profit_margin',
        store=False,
    )
    
    # Deal Risks
    risk_level = fields.Selection(
        [
            ('low', 'Low Risk'),
            ('medium', 'Medium Risk'),
            ('high', 'High Risk'),
        ],
        string='Risk Level',
        default='medium',
        tracking=True,
    )
    
    risk_description = fields.Text(
        string='Risk Description',
        tracking=True,
    )
    
    # Next Steps
    next_step = fields.Text(
        string='Next Step',
        tracking=True,
    )
    
    next_step_date = fields.Date(
        string='Next Step Date',
        tracking=True,
    )
    
    @api.depends('probability', 'competitive_win_probability', 'deal_size')
    def _compute_win_probability(self):
        """Calculate win probability"""
        for opp in self:
            base_prob = opp.probability or 0
            comp_factor = (opp.competitive_win_probability or 50) / 100
            win_prob = int(base_prob * comp_factor)
            opp.win_probability = min(100, win_prob)
    
    def _compute_deal_size(self):
        """Categorize deal size"""
        for opp in self:
            value = opp.expected_revenue or 0
            if value < 10000:
                opp.deal_size = 'small'
            elif value < 50000:
                opp.deal_size = 'medium'
            elif value < 100000:
                opp.deal_size = 'large'
            else:
                opp.deal_size = 'enterprise'
    
    def _compute_deal_value_category(self):
        """Get numeric deal value"""
        for opp in self:
            opp.deal_value_category = opp.expected_revenue or 0.0
    
    def _compute_days_in_pipeline(self):
        """Calculate days in pipeline"""
        for opp in self:
            if opp.date_open:
                days = (fields.Datetime.now() - opp.date_open).days
                opp.days_in_pipeline = max(0, days)
            else:
                opp.days_in_pipeline = 0
    
    @api.depends('stage_id')
    def _compute_stage_progress(self):
        """Calculate stage progress"""
        for opp in self:
            if opp.stage_id:
                all_stages = self.env['crm.stage'].search([], order='sequence')
                total_stages = len(all_stages)
                current_index = list(all_stages).index(opp.stage_id) + 1 if opp.stage_id in all_stages else 0
                opp.stage_progress = (current_index / total_stages * 100) if total_stages > 0 else 0
            else:
                opp.stage_progress = 0.0
    
    @api.depends('win_probability', 'expected_revenue')
    def _compute_close_probability(self):
        """Calculate close probability"""
        for opp in self:
            opp.close_probability = (opp.win_probability or 0) / 100.0
    
    @api.depends('expected_revenue', 'expected_cost')
    def _compute_expected_profit(self):
        """Calculate expected profit"""
        for opp in self:
            revenue = opp.expected_revenue or 0.0
            cost = opp.expected_cost or 0.0
            opp.expected_profit = revenue - cost
    
    @api.depends('expected_profit', 'expected_revenue')
    def _compute_profit_margin(self):
        """Calculate profit margin percentage"""
        for opp in self:
            if opp.expected_revenue and opp.expected_revenue > 0:
                opp.profit_margin_percentage = (opp.expected_profit / opp.expected_revenue) * 100
            else:
                opp.profit_margin_percentage = 0.0
    
    def action_move_to_discovery(self):
        """Move opportunity to discovery stage"""
        self.write({
            'sales_stage': 'discovery',
            'discovery_date': fields.Date.context_today(self),
        })
    
    def action_move_to_proposal(self):
        """Move opportunity to proposal stage"""
        self.write({
            'sales_stage': 'proposal',
            'proposal_sent_date': fields.Date.context_today(self),
        })
    
    def action_move_to_negotiation(self):
        """Move opportunity to negotiation stage"""
        self.write({
            'sales_stage': 'negotiation',
            'negotiation_start_date': fields.Date.context_today(self),
        })
    
    def action_move_to_closing(self):
        """Move opportunity to closing stage"""
        self.write({
            'sales_stage': 'closing',
        })
    
    def action_schedule_review(self):
        """Schedule a deal review meeting"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Schedule Review',
            'res_model': 'mail.activity',
            'view_mode': 'form',
            'context': {
                'default_res_model': 'crm.opportunity',
                'default_res_id': self.id,
                'default_activity_type_id': self.env.ref('mail.mail_activity_data_meeting').id,
            },
            'target': 'new',
        }
    
    def action_add_contact(self):
        """Add a contact to the deal"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Add Contact',
            'res_model': 'res.partner',
            'view_mode': 'list,form',
            'domain': [('id', '=', self.partner_id.id)],
            'target': 'new',
        }
    
    def action_view_deal_contacts(self):
        """View all contacts related to this deal"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Deal Contacts',
            'res_model': 'res.partner',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.contact_ids.ids)],
        }
    
    def action_create_sale_order_advanced(self):
        """Create sale order with deal details"""
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_id.id,
            'opportunity_id': self.id,
            'origin': self.name,
        })
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'New Sale Order',
            'res_model': 'sale.order',
            'res_id': sale_order.id,
            'view_mode': 'form',
        }
    
    def action_mark_deal_won(self):
        """Mark deal as won"""
        self.write({
            'sales_stage': 'won',
            'actual_close_date': fields.Date.context_today(self),
        })
        self.action_set_won()
    
    def action_mark_deal_lost(self):
        """Mark deal as lost"""
        self.write({
            'sales_stage': 'lost',
            'actual_close_date': fields.Date.context_today(self),
        })
        self.action_set_lost()

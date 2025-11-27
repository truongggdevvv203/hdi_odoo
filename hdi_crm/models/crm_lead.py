from odoo import models, fields, api
from datetime import datetime, timedelta
from odoo.exceptions import ValidationError


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    name = fields.Char(
        string='Lead Name',
        required=True,
        tracking=True,
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        tracking=True,
    )
    
    # Contact Information
    contact_name = fields.Char(
        string='Contact Name',
        tracking=True,
    )
    
    email_from = fields.Char(
        string='Email',
        tracking=True,
    )
    
    phone = fields.Char(
        string='Phone',
        tracking=True,
    )
    
    mobile = fields.Char(
        string='Mobile',
        tracking=True,
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Customer',
        tracking=True,
    )
    
    # Lead Details
    description = fields.Text(
        string='Description',
        tracking=True,
    )
    
    stage_id = fields.Many2one(
        'crm.stage',
        string='Stage',
        default=lambda self: self.env['crm.stage'].search([], limit=1),
        group_expand='_read_group_stage_ids',
        tracking=True,
    )
    
    probability = fields.Integer(
        string='Probability (%)',
        default=0,
        tracking=True,
    )
    
    expected_revenue = fields.Monetary(
        string='Expected Revenue',
        currency_field='company_currency',
        tracking=True,
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
    
    source_id = fields.Many2one(
        'crm.source',
        string='Source',
        tracking=True,
    )
    
    # Dates
    date_action = fields.Date(
        string='Next Activity Date',
        tracking=True,
    )
    
    date_deadline = fields.Date(
        string='Expected Closing Date',
        tracking=True,
    )
    
    create_date = fields.Datetime(
        string='Created On',
        readonly=True,
    )
    
    # Status
    active = fields.Boolean(
        string='Active',
        default=True,
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
    
    lost_reason_id = fields.Many2one(
        'crm.lost.reason',
        string='Lost Reason',
        tracking=True,
    )

    quotation_count = fields.Integer(
        string='Quotation Count',
        compute='_compute_quotation_count',
        store=False,
    )

    sale_amount_total = fields.Monetary(
        string='Total Quotation Amount',
        compute='_compute_sale_amount_total',
        currency_field='company_currency',
        store=False,
    )

    sale_order_count = fields.Integer(
        string='Sale Order Count',
        compute='_compute_sale_order_count',
        store=False,
    )
    
    def _read_group_stage_ids(self, stages, domain, order=None):
        if order:
            return stages.search([], order=order)
        return stages.search([])
    
    @api.constrains('probability')
    def _check_probability(self):
        for record in self:
            if record.probability < 0 or record.probability > 100:
                raise ValidationError("Probability must be between 0 and 100")
    
    def action_convert_to_opportunity(self):
        """Convert Lead to Opportunity"""
        for lead in self:
            if not lead.partner_id:
                lead.partner_id = self.env['res.partner'].create({
                    'name': lead.name,
                    'email': lead.email_from,
                    'phone': lead.phone,
                    'mobile': lead.mobile,
                })
            
            opportunity = self.env['crm.opportunity'].create({
                'name': lead.name,
                'partner_id': lead.partner_id.id,
                'description': lead.description,
                'user_id': lead.user_id.id,
                'team_id': lead.team_id.id,
                'tag_ids': lead.tag_ids.ids,
                'expected_revenue': lead.expected_revenue,
                'probability': lead.probability,
                'date_deadline': lead.date_deadline,
                'lead_id': lead.id,
            })
            lead.write({'active': False})
        return True
    
    def action_mark_as_lost(self, lost_reason_id=None):
        """Mark lead as lost"""
        self.write({
            'active': False,
            'lost_reason_id': lost_reason_id,
        })
    
    def action_mark_as_spam(self):
        """Mark lead as spam and deactivate"""
        self.write({'active': False})
    
    def action_send_email(self):
        """Open compose email window"""
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'mail.compose.message',
            'view_mode': 'form',
            'context': {
                'default_model': 'crm.lead',
                'default_res_id': self.id,
            },
            'target': 'new',
        }
    def _compute_quotation_count(self):
        SaleOrder = self.env['sale.order']
        for rec in self:
            try:
                rec.quotation_count = SaleOrder.search_count([('opportunity_id', '=', rec.id)])
            except Exception:
                rec.quotation_count = 0

    def _compute_sale_amount_total(self):
        SaleOrder = self.env['sale.order']
        for rec in self:
            try:
                orders = SaleOrder.search([('opportunity_id', '=', rec.id)])
                rec.sale_amount_total = sum(o.amount_total or 0.0 for o in orders)
            except Exception:
                rec.sale_amount_total = 0.0

    def _compute_sale_order_count(self):
        SaleOrder = self.env['sale.order']
        for rec in self:
            try:
                rec.sale_order_count = SaleOrder.search_count([('opportunity_id', '=', rec.id)])
            except Exception:
                rec.sale_order_count = 0


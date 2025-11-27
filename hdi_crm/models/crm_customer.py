from odoo import models, fields, api


class CrmCustomer(models.Model):
    _name = 'crm.customer'
    _inherit = 'res.partner'
    _order = 'name'

    name = fields.Char(
        string='Customer Name',
        required=True,
        tracking=True,
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        tracking=True,
    )
    
    # Link to res.partner
    partner_id = fields.Many2one(
        'res.partner',
        string='Contact',
        required=True,
        tracking=True,
    )
    
    # Customer Details
    customer_type = fields.Selection(
        [
            ('individual', 'Individual'),
            ('business', 'Business'),
        ],
        string='Customer Type',
        default='business',
        tracking=True,
    )
    
    industry_id = fields.Many2one(
        'crm.industry',
        string='Industry',
        tracking=True,
    )
    
    company_size = fields.Selection(
        [
            ('1-10', '1-10 employees'),
            ('11-50', '11-50 employees'),
            ('51-200', '51-200 employees'),
            ('201-500', '201-500 employees'),
            ('500+', '500+ employees'),
        ],
        string='Company Size',
        tracking=True,
    )
    
    # Contact Information
    email = fields.Char(
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
    
    website = fields.Char(
        string='Website',
        tracking=True,
    )
    
    # Address
    street = fields.Char(string='Street')
    street2 = fields.Char(string='Street 2')
    city = fields.Char(string='City')
    state_id = fields.Many2one('res.country.state', string='State')
    zip = fields.Char(string='ZIP')
    country_id = fields.Many2one('res.country', string='Country')
    
    # Relationship
    user_id = fields.Many2one(
        'res.users',
        string='Account Manager',
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
    
    # Financial Information
    annual_revenue = fields.Monetary(
        string='Annual Revenue',
        currency_field='company_currency',
        tracking=True,
    )
    
    company_currency = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        readonly=True,
    )
    
    # Status
    active = fields.Boolean(
        string='Active',
        default=True,
        tracking=True,
    )
    
    customer_since = fields.Date(
        string='Customer Since',
        default=fields.Date.context_today,
        tracking=True,
    )
    
    last_interaction_date = fields.Date(
        string='Last Interaction',
        readonly=True,
    )
    
    description = fields.Text(
        string='Notes',
        tracking=True,
    )
    
    def action_view_opportunities(self):
        """View all opportunities for this customer"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Opportunities',
            'res_model': 'crm.opportunity',
            'view_mode': 'kanban,list,form',
            'domain': [('partner_id', '=', self.partner_id.id)],
            'context': {'default_partner_id': self.partner_id.id},
        }
    
    def action_view_orders(self):
        """View all sales orders for this customer"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Sales Orders',
            'res_model': 'sale.order',
            'view_mode': 'tree,form',
            'domain': [('partner_id', '=', self.partner_id.id)],
        }

{
  'name': 'HDI CRM',
  'version': '18.0.1.0.0',
  'category': 'hdi',
  'summary': 'CRM with Lead, Opportunity, and Customer management',
  'description': 'Enhanced CRM module for Odoo 18: Leads, Opportunities, Customers, Tags, Stages, Sales Teams',
  'author': 'HDI Development Team',
  'license': 'LGPL-3',
  'depends': [
    'crm',
    'contacts',
    'mail',
    'sale_management',
  ],
  'data': [
    # Security
    'security/crm_security.xml',
    'security/ir.model.access.csv',

    'views/crm_activity_views.xml',
    'views/crm_lead_views.xml',
    'views/crm_opportunity_views.xml',
    'views/crm_customer_views.xml',
    'views/crm_team_views.xml',
    'views/crm_menu.xml',
  ],

  'installable': True,
  'application': True,
  'auto_install': False,
}

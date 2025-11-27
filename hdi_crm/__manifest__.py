{
    'name': 'HDI CRM',
    'version': '18.0.1.0.0',
    'category': 'hdi',
    'summary': 'Complete CRM module with Lead, Opportunity, and Customer management',
    'description': 'Full-featured CRM module for Odoo 18 with built-in functionality for managing leads, opportunities, customers, and sales activities',
    'author': 'HDI Development Team',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'sale',
        'contacts',
        'mail',
    ],
    'data': [
        # Security
        'security/crm_security.xml',
        'security/ir.model.access.csv',
        
        # Data
        'data/crm_stage.xml',
        'data/crm_tag.xml',
        
        # Views
        'views/crm_lead_views.xml',
        'views/crm_opportunity_views.xml',
        'views/crm_customer_views.xml',
        'views/crm_activity_views.xml',
        'views/crm_team_views.xml',
        'views/crm_menu.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'images': ['static/description/icon.png'],
}

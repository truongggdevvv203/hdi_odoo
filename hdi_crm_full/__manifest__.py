{
    'name': 'HDI CRM Full Bridge',
    'version': '1.0',
    'summary': 'Expose core CRM menus and views under an HDI module (Odoo 18)',
    'category': 'CRM',
    'author': 'HDI Dev',
    'license': 'LGPL-3',
    'depends': ['crm', 'contacts', 'mail', 'sale_management'],
    'data': [
        'security/ir.model.access.csv',
        'views/crm_full_menu.xml',
    ],
    'installable': True,
    'application': False,
}

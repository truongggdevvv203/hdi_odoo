{
    'name': 'HDI Sale Management',
    'version': '18.0.1.0.0',
    'category': 'Sales',
    'description': 'Extended sales management features for HDI',
    'author': 'HDI',
    'depends': ['sale_management'],
    'data': [
        'security/ir.model.access.csv',
        'views/menu.xml',
        'views/sale_order_views.xml',
    ],
    'installable': True,
    'application': False,
}

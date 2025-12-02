{
    'name': 'HDI Sale Management',
    'version': '18.0.1.0.0',
    'category': 'hdi',
    'description': 'Extended sales management features for HDI',
    'author': 'HDI',
    'depends': ['sale_management'],
    'data': [
        'security/ir.model.access.csv',
        'views/sale_order_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': False,
}

{
    'name': 'HDI Sale Management',
    'version': '18.0.1.0.0',
    'category': 'hdi',
    'description': 'Extended sales management features for HDI',
    'author': 'HDI',
    'depends': ['sale_management'],
    'data': [
        'data/shipping_order_sequence.xml',
        'security/ir.model.access.csv',
        'views/shipping_service_views.xml',
        'views/shipping_order_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': False,
}

{
    'name': 'HDI Sale Management',
    'version': '18.0.1.1.0',
    'category': 'hdi',
    'description': 'Extended sales management features for HDI',
    'author': 'HDI',
    'depends': ['sale_management', 'bus'],
    'data': [
        'data/shipping_order_sequence.xml',
        'security/ir.model.access.csv',
        'views/dashboard_views.xml',
        'views/shipping_service_views.xml',
        'views/shipping_order_views.xml',
        'views/reconciliation_views.xml',
        'views/menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'hdi_sale/static/src/js/dashboard_component.js',
            'hdi_sale/static/src/xml/dashboard_template.xml',
        ],
    },
    'installable': True,
    'application': False,
}

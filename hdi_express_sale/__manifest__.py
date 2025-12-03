{
    'name': 'HDI Sale Management',
    'version': '18.0.1.1.0',
    'category': 'hdi',
    'description': 'Extended sales management features for HDI',
    'author': 'HDI',
    'depends': ['sale_management', 'bus'],
    'data': [
        'data/express_shipping_order_sequence.xml',
        'security/ir.model.access.csv',
        'views/express_dashboard_views.xml',
        'views/express_shipping_service_views.xml',
        'views/express_shipping_order_views.xml',
        'views/express_order_search_views.xml',
        # 'views/express_debt_reconciliation_views.xml',
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

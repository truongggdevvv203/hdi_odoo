{
    'name': 'HDI Shipping',
    'version': '18.0.1.0.0',
    'summary': 'Shipping order management',
    'category': 'hdi',
    'description': 'Manage shipping orders: sender address, receiver info, shipment items, services, fees',
    'author': 'HDI Development Team',
    'license': 'LGPL-3',
    'depends': [
        'contacts',
    ],
    'data': [
        'data/sequence_data.xml',
        'security/ir.model.access.csv',
        'views/shipping_order_views.xml',
        'views/sender_address_views.xml',
        'views/shipping_service_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}

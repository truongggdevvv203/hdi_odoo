{
    'name': 'HDI Product',
    'version': '18.0.1.0.0',
    'summary': 'HDI extensions for Odoo Product',
    'category': 'hdi',
    'description': 'Inherit Odoo base product models to add HDI custom fields and views. Does NOT create new models with conflicting table names.',
    'author': 'HDI Development Team',
    'license': 'LGPL-3',
    'depends': [
        'product',
        'uom',
    ],
    'data': [
        'views/menu.xml',
        'views/product_category_views.xml',
        'views/product_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}

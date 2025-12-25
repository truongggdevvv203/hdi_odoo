# -*- coding: utf-8 -*-
{
    'name': 'HDI WMS - Warehouse Management System',
    'version': '18.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Advanced WMS with Batch/LPN, Putaway Strategy, and Scanner Support',
    'description': """
HDI Warehouse Management System
    """,
    'author': 'HDI',
    'website': 'https://www.hdi.com',
    'depends': [
        'stock',
        'barcodes',
    ],
    'data': [
        # Security
        'security/wms_security.xml',
        'security/ir.model.access.csv',

        # Data
        'data/wms_data.xml',

        # Views - Core Extensions (Inherit)
        'views/stock_picking_views.xml',
        'views/stock_move_views.xml',
        'views/stock_location_views.xml',
        'views/stock_quant_views.xml',

        # Views - Custom Models (New)
        'views/hdi_batch_views.xml',
        'views/hdi_putaway_suggestion_views.xml',
        'views/hdi_loose_line_views.xml',
        'views/hdi_picking_list_views.xml',

        # Wizards
        'wizard/batch_creation_wizard_views.xml',
        'wizard/putaway_wizard_views.xml',
        'wizard/picking_suggestion_wizard_views.xml',

        # Menus
        'views/wms_menus.xml',
    ],
    # 'assets': {
    #     'web.assets_backend': [
    #         'hdi_wms/static/src/js/barcode_scanner.js',
    #         'hdi_wms/static/src/xml/scanner_templates.xml',
    #         'hdi_wms/static/src/scss/wms.scss',
    #     ],
    # },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}

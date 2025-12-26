# -*- coding: utf-8 -*-
{
    'name': 'HDI Attendance Kiosk',
    'version': '18.0.1.0.0',
    'category': 'hdi',
    'description': 'Attendance check-in/check-out kiosk interface',
    'author': 'HDI',
    'license': 'AGPL-3',
    'depends': ['hr_attendance', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'views/menu.xml',
        'views/attendance_kiosk_views.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'hdi_attendance_kiosk/static/src/js/attendance_kiosk.js',
            'hdi_attendance_kiosk/static/src/css/attendance_kiosk.css',
        ],
    },
    'installable': True,
    'auto_install': False,
}

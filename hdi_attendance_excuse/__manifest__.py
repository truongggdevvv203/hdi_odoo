{
  'name': 'HDI Attendance Excuse Management',
  'version': '18.0.1.0.0',
  'category': 'hdi',
  'description': """ """,
  'author': 'HDI',
  'depends': [
    'base',
    'hr',
    'hr_attendance',
    'hdi_payroll',
  ],
  'data': [
    # Security
    'security/ir.model.access.csv',

    # Data
    'data/ir_cron.xml',

    # Views
    'views/attendance_excuse_views.xml',
    'views/hr_attendance_views.xml',
    'views/excuse_limit_views.xml',

    # Menu
    'views/menu.xml',
  ],
  'assets': {
    'web.assets_backend': [
    ],
  },
  'installable': True,
  'application': False,
  'auto_install': False,
}

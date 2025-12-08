{
  'name': 'HDI Attendance Excuse Management',
  'version': '18.0.1.0.0',
  'category': 'hdi',
  'description': """
    Complete Attendance Excuse Management System for HDI
    - Handle late arrival and early departure
    - Handle missing check-in/check-out
    - Handle incorrect check-in/check-out time
    - Auto-generate excuse requests
    - Track approval workflow
  """,
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
    'data/excuse_types_data.xml',

    # Views
    'views/attendance_excuse_views.xml',
    'views/attendance_excuse_request_views.xml',
    'views/hr_attendance_views.xml',

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

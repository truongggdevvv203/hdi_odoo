{
  'name': 'HDI Human Resources Extensions',
  'version': '18.0.1.0.0',
  'category': 'hdi',
  'description': """
    Human Resources module extensions for HDI
  """,
  'author': 'HDI',
  'depends': [
    'base',
    'hr',
    'hr_attendance',
    'hr_holidays',
  ],
  'data': [
    # Security
    'security/ir.model.access.csv',

    # Views
    'views/hr_employee_views.xml',
    'views/hr_department_views.xml',

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

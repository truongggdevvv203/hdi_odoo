{
  'name': 'HDI Payroll Management',
  'version': '18.0.1.0.0',
  'category': 'hdi',
  'description': """
        Complete Payroll Management System for HDI
    """,
  'author': 'HDI',
  'depends': [
    'base',
    'hr',
    'hr_holidays',
    'hr_attendance',
  ],
  'data': [
    # Security
    'security/ir.model.access.csv',

    # Views
    'views/hr_work_summary_views.xml',
    'views/hr_salary_grade_views.xml',
    'views/hr_salary_structure_views.xml',
    'views/hr_salary_rule_views.xml',
    'views/hr_payslip_views.xml',

    # Menu
    'views/menu.xml',
  ],
  'assets': {
    'web.assets_backend': [
    ],
  },
  'installable': True,
  'application': True,
  'auto_install': False,
}

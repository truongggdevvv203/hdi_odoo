{
    'name': 'HDI Payroll Management',
    'version': '18.0.1.0.0',
    'category': 'hdi',
    'description': """
        Complete Payroll Management System for HDI
        
        Features:
        - Attendance Summary (Bảng công)
        - Salary Grades by position and level
        - Salary Structure definitions
        - Salary Rules with Python formula evaluation
        - Payslip generation with automatic calculations
        - Integration with HR attendance and leaves
        - Vietnamese business workflows
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

# -*- coding: utf-8 -*-
{
    'name': 'HDI HR Payroll Management',
    'version': '18.0.1.0.0',
    'category': 'hdi',
    'summary': 'Quản lý tính lương HDI',
    'description': """
HDI Payroll Management System
    """,
    'author': 'HDI Development Team',
    'website': '',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'hr',
        'hr_contract',
        'hr_attendance',
        'hr_work_entry',
        'hr_work_entry_contract',
        'hr_holidays',
    ],
    'data': [
        # Security
        'security/payroll_security.xml',
        'security/ir.model.access.csv',

        # Data - Load theo thứ tự QUAN TRỌNG
        'data/hr_salary_rule_category_data.xml',
        'data/hr_payroll_structure_type_data.xml',
        'data/hr_salary_structure_data.xml',
        'data/hr_tax_bracket_data.xml',
        'data/hr_allowance_type_data.xml',
        'data/hr_salary_rule_data.xml',

        # Views - Placeholder
        'views/hr_employee_views.xml',
        'views/hr_contract_views.xml',
        'views/hr_payslip_views.xml',
        'views/hr_salary_rule_views.xml',
        'views/hr_allowance_views.xml',
        'views/hr_loan_views.xml',
        'views/hr_discipline_views.xml',
        'views/hr_tax_views.xml',

        # Menu
        'views/menu.xml',

        # Report
        'report/payroll_reports.xml',
        'report/payslip_report_template.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}

{
    'name': 'HDI API - Mobile App Integration',
    'version': '18.0.1.0.0',
    'category': 'hdi',
    'description': """
        API endpoints for mobile app integration with JWT Token authentication
    """,
    'author': 'HDI',
    'depends': [
        'base',
        'web',
        'hr_attendance',
        'hr',
        'hdi_hr',
    ],
    'external_dependencies': {
        'python': ['pyjwt', 'werkzeug'],
    },
    'data': [
        'security/ir.model.access.csv',
        'data/jwt_token_blacklist_cron.xml',
    ],
    'installable': True,
    'auto_install': False,
}

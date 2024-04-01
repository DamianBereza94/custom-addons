{
    'name': 'Trilab Car Mileage',
    'description': """
        The module allowing for the management of vehicle mileage records.
    """,
    'author': 'Bereza Damian',
    'category': 'Fleet Management',
    'application': True,
    'version': '1.0',
    'depends': ['base'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/vehicle_view.xml',
        'views/mileage_view.xml',
        'report/mileage_report_view.xml',
        'views/menuitem.xml',
    ],
    'license': 'LGPL-3',
}

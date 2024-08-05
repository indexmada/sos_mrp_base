# -*- coding: utf-8 -*-
{
    'name': "SOS MRP BASE",

    'summary': """
        Filtre des articles dans le components par Catégorie d'article""",

    'description': """
        - Filtre des articles dans le components par Catégorie d'article dans BoM
        - Filtre des articles dans le components par Catégorie d'article dans MO
        - Ajout automatique du catégorie selectionné dans BoM dans MO
    """,

    'author': "My Company",
    'website': "https://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/16.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'mrp'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/stock_move_view.xml',
        'views/mrp_menu.xml',
        'views/mrp_routing_workcenter.xml',
        "wizard/mrp_confirm_wizard.xml"
    ],
}

# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    "name": "MTSMTE Specific Project Module",
    "version": "10.0.1.0.0",
    'description': '''Specific module for MTSMTE.

    Adds a chatter to the project.project.
    Adds default task stages.
    ''',
    "depends": [
        'project',
        'project_task_default_stage',
        'mtsmte_sale',
        'account',
    ],
    "author": 'Camptocamp,Odoo Community Association (OCA)',
    "website": 'http://www.camptocamp.com',
    "license": 'AGPL-3',
    "category": 'Project',
    "data": [
        'data/project_task.xml',
        'views/project_project.xml',
        'views/sale_order.xml',
        'views/account_invoice.xml',
    ],
    'installable': True,
}

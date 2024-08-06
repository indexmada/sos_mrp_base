# -*- coding: utf-8 -*-

from . import models
from . import wizard
from odoo import api, SUPERUSER_ID

def _copy_operations(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    bom_ids = env['mrp.bom'].search([])
    for bom in bom_ids:
        bom.operations_ids = bom.operation_ids
from odoo import models, api, fields

class ConfirmWizard(models.TransientModel):
    _name = "mrp.confirm_wizard"

    name = fields.Char('Validation')
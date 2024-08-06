from odoo import api, fields,models

class MrpRoutingWorkcenter(models.Model):
    _inherit = "mrp.routing.workcenter"

    allowed_bom_ids = fields.One2many('mrp.routing.bom', 'route_workcenter_id', string="Allowed nomenclature")
    taken_boom_ids = fields.Many2many('mrp.bom', compute="_compute_taken_bom_ids")
    
    @api.depends('allowed_bom_ids.bom_id')
    def _compute_taken_bom_ids(self):
        for rec in self:
            rec.taken_boom_ids = (rec.allowed_bom_ids.mapped('bom_id') + rec.bom_id).ids

class MrpBom(models.Model):
    _inherit ="mrp.bom"

    operation_ids = fields.Many2many('mrp.routing.workcenter', 'bom_id', string='Operations', copy=True)
    allowed_operation_ids = fields.Many2many('mrp.routing.workcenter', compute="_compute_allowed_operations")

    
    def _compute_allowed_operations(self):
        routing_bom = self.env['mrp.routing.bom']
        workcenter = self.env['mrp.routing.workcenter']

        for rec in self:
            workcenter_id_via_config = routing_bom.search([('bom_id', '=', rec.id)]).route_workcenter_id
            workcenter_id = workcenter.search([('bom_id', '=', rec.id)])
            rec.allowed_operation_ids = (workcenter_id_via_config + workcenter_id).mapped('id')

class StockMove(models.Model):
    _inherit = "stock.move"

    allowed_operation_ids = fields.Many2many(
        'mrp.routing.workcenter', related='raw_material_production_id.bom_id.operation_ids')
    
class MrpBomLine(models.Model):
    _inherit = "mrp.bom.line"

    allowed_operation_ids = fields.Many2many('mrp.routing.workcenter', related='bom_id.operation_ids')

class MrpBomByProduct(models.Model):
    _inherit = "mrp.bom.byproduct"

    allowed_operation_ids = fields.Many2many('mrp.routing.workcenter', related='bom_id.operation_ids')

class MrpRoutingBom(models.Model):
    _name = "mrp.routing.bom"

    route_workcenter_id = fields.Many2one("mrp.routing.workcenter", string="Opération")
    bom_id = fields.Many2one("mrp.bom", string="Nomenclature")
    workcenter_id = fields.Many2one('mrp.workcenter', string="Poste de travail", default=lambda self: self.route_workcenter_id.workcenter_id.id)
    taken_boom_ids = fields.Many2many(related='route_workcenter_id.taken_boom_ids')








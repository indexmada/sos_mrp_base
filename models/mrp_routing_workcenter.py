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

    operations_ids = fields.Many2many('mrp.routing.workcenter', 'bom_id', string='Operations', copy=True)
    allowed_operations_ids = fields.Many2many('mrp.routing.workcenter', compute="_compute_allowed_operations")

    def toggle_active(self):
        self.with_context({'active_test': False}).operation_ids.toggle_active()
        return super().toggle_active()
    
    @api.onchange('operations_ids')
    @api.depends('operations_ids')
    
    def _onchange_operations_ids(self):
        for rec in self:
            rec.operation_ids = rec.operations_ids
    
    def _compute_allowed_operations(self):
        routing_bom = self.env['mrp.routing.bom']
        workcenter = self.env['mrp.routing.workcenter']

        for rec in self:
            workcenter_id_via_config = routing_bom.search([('bom_id', '=', rec.id)]).route_workcenter_id
            workcenter_id = workcenter.search([('bom_id', '=', rec.id)])
            rec.allowed_operations_ids = (workcenter_id_via_config + workcenter_id).mapped('id')

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.bom_line_ids.bom_product_template_attribute_value_ids = False
            self.operations_ids.bom_product_template_attribute_value_ids = False
            self.byproduct_ids.bom_product_template_attribute_value_ids = False
    
    @api.constrains('product_id', 'product_tmpl_id', 'bom_line_ids', 'byproduct_ids', 'operations_ids')
    def _check_bom_lines(self):
        for bom in self:
            apply_variants = bom.bom_line_ids.bom_product_template_attribute_value_ids | bom.operations_ids.bom_product_template_attribute_value_ids | bom.byproduct_ids.bom_product_template_attribute_value_ids
            if bom.product_id and apply_variants:
                raise ValidationError(_("You cannot use the 'Apply on Variant' functionality and simultaneously create a BoM for a specific variant."))
            for ptav in apply_variants:
                if ptav.product_tmpl_id != bom.product_tmpl_id:
                    raise ValidationError(_(
                        "The attribute value %(attribute)s set on product %(product)s does not match the BoM product %(bom_product)s.",
                        attribute=ptav.display_name,
                        product=ptav.product_tmpl_id.display_name,
                        bom_product=bom.product_tmpl_id.display_name
                    ))
            for byproduct in bom.byproduct_ids:
                if bom.product_id:
                    same_product = bom.product_id == byproduct.product_id
                else:
                    same_product = bom.product_tmpl_id == byproduct.product_id.product_tmpl_id
                if same_product:
                    raise ValidationError(_("By-product %s should not be the same as BoM product.") % bom.display_name)
                if byproduct.cost_share < 0:
                    raise ValidationError(_("By-products cost shares must be positive."))
            if sum(bom.byproduct_ids.mapped('cost_share')) > 100:
                raise ValidationError(_("The total cost share for a BoM's by-products cannot exceed 100."))
            
    
    def copy(self, default=None):
        res = super().copy(default)
        if self.operations_ids:
            operations_mapping = {}
            for original, copied in zip(self.operations_ids, res.operations_ids.sorted()):
                operations_mapping[original] = copied
            for bom_line in res.bom_line_ids:
                if bom_line.operation_id:
                    bom_line.operation_id = operations_mapping[bom_line.operation_id]
            for operation in self.operations_ids:
                if operation.blocked_by_operation_ids:
                    copied_operation = operations_mapping[operation]
                    dependencies = []
                    for dependency in operation.blocked_by_operation_ids:
                        dependencies.append(Command.link(operations_mapping[dependency].id))
                    copied_operation.blocked_by_operation_ids = dependencies

        return res
    
class StockMove(models.Model):
    _inherit = "stock.move"

    allowed_operations_ids = fields.Many2many(
        'mrp.routing.workcenter', related='raw_material_production_id.bom_id.operations_ids')
    
    operation_id = fields.Many2one(domain="[('id', 'in', allowed_operations_ids)]")

    
class MrpBomLine(models.Model):
    _inherit = "mrp.bom.line"

    allowed_operations_ids = fields.Many2many('mrp.routing.workcenter', related='bom_id.operations_ids')

class MrpBomByProduct(models.Model):
    _inherit = "mrp.bom.byproduct"

    allowed_operations_ids = fields.Many2many('mrp.routing.workcenter', related='bom_id.operations_ids')


class MrpRoutingBom(models.Model):
    _name = "mrp.routing.bom"

    route_workcenter_id = fields.Many2one("mrp.routing.workcenter", string="Opération")
    bom_id = fields.Many2one("mrp.bom", string="Nomenclature")
    workcenter_id = fields.Many2one('mrp.workcenter', string="Poste de travail", default=lambda self: self.route_workcenter_id.workcenter_id.id)
    taken_boom_ids = fields.Many2many(related='route_workcenter_id.taken_boom_ids')








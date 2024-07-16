# -*- coding: utf-8 -*-

from odoo import models, fields, api



class MrpProduction(models.Model):
	_inherit = "mrp.production"

	product_taken_ids = fields.Many2many('product.product', string="Produit déjà pris", compute="_set_product_taken_ids")

	@api.depends('move_raw_ids.product_id')
	def _set_product_taken_ids(self):
		for rec in self:
			rec.product_taken_ids = rec.move_raw_ids.mapped('product_id.id')

class MrpBomLine(models.Model):
	_inherit = "mrp.bom.line"

	categ_id = fields.Many2one(comodel_name="product.category", string="Catégorie")
	

	@api.onchange('categ_id')
	def _onchange_field_categ_id(self):
		if self.categ_id:
			domain = [('categ_id', '=', self.categ_id.id), ('company_id', 'in', [self.company_id.id, False])]
			return {'domain': {'product_id': domain}}
		else:
			return {'domain': {'product_id': []}}


class StockMove(models.Model):
	_inherit = "stock.move"

	categ_id = fields.Many2one(comodel_name="product.category", string="Catégorie")
	product_taken_ids = fields.Many2many(related="raw_material_production_id.product_taken_ids", string="Produit déjà pris")

	@api.model
	def create(self, vals):
		if vals.get('product_id') and not vals.get('categ_id'):
			product_id = self.env['product.product'].sudo().browse(vals.get('product_id'))
			vals['categ_id'] = product_id.categ_id.id
		res = super(StockMove, self).create(vals)
		return res

class MrpProduction(models.Model):

	_inherit = "mrp.production"

	normal_product_ids = fields.Many2many(string="Normal Product", comodel_name="product.product", compute="_compute_normal_product", default=lambda self: self.product_domain())

	def _compute_normal_product(self):
		for rec in self:
			rec.normal_product_ids = [(6, 0, self.product_domain())]

	def product_domain(self):
		bom_ids = self.env['mrp.bom'].sudo().search([('type', '=', 'normal')])
		product_product_ids = self.env['product.product'].sudo().search([('product_tmpl_id', 'in', bom_ids.mapped('product_tmpl_id').ids)])
		# product_ids = self.env['product.product'].sudo().search([('type', 'in', ['product', 'consu']), ('id', 'in', product_product_ids.ids)])
		return product_product_ids.ids

	def _get_move_raw_values(self, product_id, product_uom_qty, product_uom, operation_id=False, bom_line=False):
		data = super(MrpProduction, self)._get_move_raw_values(product_id, product_uom_qty, product_uom, operation_id, bom_line)

		data['categ_id'] = bom_line.categ_id.id

		return data
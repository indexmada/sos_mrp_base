# -*- coding: utf-8 -*-

from odoo import models, fields, api


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

	@api.model
	def create(self, vals):
		if vals.get('product_id') and not vals.get('categ_id'):
			product_id = self.env['product.product'].sudo().browse(vals.get('product_id'))
			vals['categ_id'] = product_id.categ_id.id
		res = super(StockMove, self).create(vals)
		return res

class MrpProduction(models.Model):

	_inherit = "mrp.production"

	def _get_move_raw_values(self, product_id, product_uom_qty, product_uom, operation_id=False, bom_line=False):
		data = super(MrpProduction, self)._get_move_raw_values(product_id, product_uom_qty, product_uom, operation_id, bom_line)

		data['categ_id'] = bom_line.categ_id.id

		return data
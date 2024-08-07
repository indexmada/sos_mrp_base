# -*- coding: utf-8 -*-

from odoo import models, fields, api,_
from odoo.exceptions import UserError, ValidationError
import logging
import json

_logger = logging.getLogger(__name__)



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
	product_taken_vals = fields.Char(related="raw_material_production_id.product_taken_vals", string="Produit déjà pris: JSON format")
	

	@api.model
	def create(self, vals):
		if vals.get('product_id') and not vals.get('categ_id'):
			product_id = self.env['product.product'].sudo().browse(vals.get('product_id'))
			vals['categ_id'] = product_id.categ_id.id
		res = super(StockMove, self).create(vals)
		return res
	
	def _get_count_product_takens(self):
		return json.loads(self.product_taken_vals or "{}")


		return product_count
	@api.depends('product_taken_vals')
	@api.onchange('product_id')
	def _onchange_product(self):
		all_count = self._get_count_product_takens()
		vals = all_count.get(str(self.product_id.id), {})
		if  self.raw_material_production_id and vals.get('count', 0) > 1:
			return {
				'warning': {'title': "Confirmation", 'message': """Votre fabrication contient déjà l’article : %s (%s %s) . Souhaitez vous en
rajouter à nouveau ?"""  % (self.product_id.name, vals.get('qty', ''), vals.get('uom', ''))},
			}


class MrpProduction(models.Model):

	_inherit = "mrp.production"

	normal_product_ids = fields.Many2many(string="Normal Product", comodel_name="product.product", compute="_compute_normal_product", default=lambda self: self.product_domain())
	product_taken_ids = fields.Many2many('product.product', string="Produit déjà pris", compute="_set_product_taken_ids")
	product_taken_vals = fields.Char(string="Produit déjà pris: JSON format", compute="_set_product_taken_ids")

	def _compute_normal_product(self):
		for rec in self:
			rec.normal_product_ids = [(6, 0, self.product_domain())]

	def product_domain(self):
		bom_ids = self.env['mrp.bom'].sudo().search([('type', '=', 'normal')])
		product_product_ids = self.env['product.product'].sudo().search([('product_tmpl_id', 'in', bom_ids.mapped('product_tmpl_id').ids)])
		return product_product_ids.ids

	def _get_move_raw_values(self, product_id, product_uom_qty, product_uom, operation_id=False, bom_line=False):
		data = super(MrpProduction, self)._get_move_raw_values(product_id, product_uom_qty, product_uom, operation_id, bom_line)

		data['categ_id'] = bom_line.categ_id.id

		return data
	
	def action_open_confirm(self):
		return {
			'type': 'ir.actions.client',
			'tag': 'display_notification',
			'name': _('Alert : Produit existant'),
		}
	
	def button_mark_done(self):

		for rec in self:
			picking = rec.picking_ids.filtered(lambda d: d.state not in ('done', 'cancel'))

			if picking:
				raise ValidationError("""Vous ne pouvez pas marquer cette fabrication comme terminée tant que le transfert associé n'est pas effectué ou terminé. 
						  \nVeuillez d'abord terminer ou marquer comme fait le transfert""")
		res = super(MrpProduction, self).button_mark_done()		
		return res

	
	@api.depends('move_raw_ids.product_id')
	def _set_product_taken_ids(self):
		for rec in self:
			values = {}
			rec.product_taken_ids = rec.move_raw_ids.mapped('product_id.id')
			for line in rec.move_raw_ids:
				
				if "ref=" in str(line) or line._origin:
					product_id = line.product_id.id
					if product_id in values:
						values[product_id]['count'] += 1
						values[product_id]['qty'] += line.product_uom_qty
					else:					
						values[product_id]= {'qty': line.product_uom_qty, 'count': 1, 'uom': line.product_uom.name}
			rec.product_taken_vals = json.dumps(values)



class StockMoveLine(models.Model):
	_inherit = "stock.move.line"

	operation_id = fields.Many2one(related="move_id.operation_id", string="Consommé dans l'opération",store=True)




	

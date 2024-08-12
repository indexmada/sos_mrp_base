# -*- coding: utf-8 -*-

from odoo import models, fields, api,_
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, float_round, float_is_zero, OrderedSet

from dateutil.relativedelta import relativedelta

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

	@api.depends('raw_material_production_id.qty_producing', 'product_uom_qty', 'product_uom', 'raw_material_production_id.need_recompute_qty')
	def _compute_should_consume_qty(self):
		for move in self:
			mo = move.raw_material_production_id
			if not mo or not move.product_uom:
				move.should_consume_qty = 0
				continue
			qty_producing = mo.product_uom_qty
			if mo.need_recompute_qty:
				_logger.info('need' *50)
				_logger.info(mo.qty_producing)
				_logger.info(mo.qty_produced)
				_logger.info('need' *50)
				qty_producing = mo.qty_producing
			
			move.should_consume_qty = float_round(( qty_producing- mo.qty_produced) * move.unit_factor, precision_rounding=move.product_uom.rounding)

class MrpProduction(models.Model):

	_inherit = "mrp.production"

	normal_product_ids = fields.Many2many(string="Normal Product", comodel_name="product.product", compute="_compute_normal_product", default=lambda self: self.product_domain())
	product_taken_ids = fields.Many2many('product.product', string="Produit déjà pris", compute="_set_product_taken_ids")
	product_taken_vals = fields.Char(string="Produit déjà pris: JSON format", compute="_set_product_taken_ids")
	need_recompute_qty = fields.Boolean(string="Voulez-vous mettre à jours les composants ?", default=False)
	date_end = fields.Datetime(string="Date de fin", default=False)

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
		self._compute_product_qty()
		return {
			'type': 'ir.actions.client',
			'tag': 'display_notification',
			'name': _('Alert : Produit existant'),
		}
	
	def button_mark_done(self):

		for rec in self:
			picking = rec.picking_ids.filtered(lambda d: d.state not in ('waiting', 'confirmed', 'done', 'cancel') and d.location_id.id == rec.location_dest_id.id)

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

	def _set_qty_producing(self):
		if self.need_recompute_qty:		
			super(MrpProduction,self)._set_qty_producing()

	@api.onchange('qty_producing', 'lot_producing_id')
	def _onchange_producing(self):

		self._set_qty_producing()
		self.compute_prod_qty_pickings()
		if self.state != 'draft':

			if self.need_recompute_qty:
				message = "Votre composant a été recalculé. Veuillez décocher 'Voulez-vous mettre à jour les composants ?' si vous ne souhaitez pas lancer un nouveau recalcul."

			else:
				message = "Votre composant n'a pas été recalculé. Veuillez cocher 'Voulez-vous mettre à jour les composants ?' si vous souhaitez lancer le recalcul."
			return {
				'warning': {'title': "Warning", 'message': message}
			}
	
	@api.onchange('need_recompute_qty')
	def _onchange_need_recompute_qty(self):
		self._set_qty_producing()
		self.compute_prod_qty_pickings()
		if self.state != 'draft':
			if self.need_recompute_qty:
				message = "Votre composant sera recalculé. Veuillez décocher 'Voulez-vous mettre à jour les composants ?' si vous ne souhaitez pas lancer un nouveau recalcul."

			else:
				message = "Votre composant ne sera pas recalculé. Veuillez cocher 'Voulez-vous mettre à jour les composants ?' si vous souhaitez lancer le recalcul."

			return {
				'warning': {'title': "Warning", 'message': message}
			}
	
	def compute_prod_qty_pickings(self):
		move_raw = self.move_raw_ids
		for picking in self.picking_ids:
			move_ids = picking.move_ids_without_package
			if len(move_ids) == 1 and move_ids.location_id.id == self.location_dest_id.id:
				move_ids._origin.write({'product_uom_qty': self.qty_producing})
			else:
				i = 0
				for move in move_ids:
					rec =  move_raw[i]
					if move.product_id.id == rec.product_id.id:
						move._origin.write({'product_uom_qty': rec.should_consume_qty})
					i+=1

class StockMoveLine(models.Model):
	_inherit = "stock.move.line"

	operation_id = fields.Many2one(related="move_id.operation_id", string="Consommé dans l'opération",store=True)




# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class PutawayWizard(models.TransientModel):
    _name = 'hdi.putaway.wizard'
    _description = 'Putaway Location Wizard'

    batch_id = fields.Many2one(
        'hdi.batch',
        string='Batch',
        default=lambda self: self.env.context.get('default_batch_id'),
    )

    picking_id = fields.Many2one(
        'stock.picking',
        string='Picking',
        default=lambda self: self.env.context.get('default_picking_id'),
    )

    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True,
    )

    quantity = fields.Float(
        string='Quantity',
        required=True,
    )

    suggestion_ids = fields.Many2many(
        'hdi.putaway.suggestion',
        string='Suggestions',
    )

    selected_location_id = fields.Many2one(
        'stock.location',
        string='Selected Location',
    )

    def action_generate_suggestions(self):
        """Generate putaway suggestions and open them"""
        self.ensure_one()

        if not self.batch_id or not self.product_id:
            raise UserError(_('Batch and Product are required.'))

        # Clear old suggestions for this batch
        old_suggestions = self.env['hdi.putaway.suggestion'].search([
            ('batch_id', '=', self.batch_id.id)
        ])
        old_suggestions.unlink()

        # Generate new suggestions
        suggestions = self.env['hdi.putaway.suggestion'].generate_suggestions(
            self.batch_id,
            max_suggestions=5
        )

        if not suggestions:
            raise UserError(_('No suitable locations found.'))

        # Open suggestions in new window
        return {
            'name': _('Chọn Vị trí Lưu kho'),
            'type': 'ir.actions.act_window',
            'res_model': 'hdi.putaway.suggestion',
            'view_mode': 'list,form',
            'domain': [('batch_id', '=', self.batch_id.id)],
            'target': 'new',
        }

    def action_confirm_location(self):
        """Confirm selected location and update batch"""
        self.ensure_one()

        if not self.selected_location_id:
            raise UserError(_('Please select a location first.'))

        # Update batch
        self.batch_id.write({
            'location_dest_id': self.selected_location_id.id,
        })

        # Update picking WMS state
        if self.picking_id:
            self.picking_id.wms_state = 'putaway_pending'

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Location Set'),
                'message': _('Putaway location set to %s') % self.selected_location_id.complete_name,
                'type': 'success',
                'sticky': False,
            }
        }

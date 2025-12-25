# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class StockMove(models.Model):

    _inherit = 'stock.move'

    # ===== WMS EXTENSIONS =====
    batch_id = fields.Many2one(
        'hdi.batch',
        string='Batch/LPN',
        index=True,
        tracking=True,
        help="Batch containing this move - links to custom WMS model"
    )

    scanned_barcodes = fields.Text(
        string='Scanned Barcodes',
        help="List of barcodes scanned for this move (JSON or line-separated)"
    )

    is_batched = fields.Boolean(
        compute='_compute_is_batched',
        store=True,
        string='Is Batched',
    )

    loose_line_id = fields.Many2one(
        'hdi.loose.line',
        string='Loose Line',
        help="Link to loose item line (items not in batch)"
    )

    @api.depends('batch_id')
    def _compute_is_batched(self):
        """Check if move is part of a batch"""
        for move in self:
            move.is_batched = bool(move.batch_id)

    def _action_done(self, cancel_backorder=False):
        """
        ✅ OVERRIDE nhưng GỌI super() - giữ 100% core logic
        Chỉ thêm batch status update sau khi move done
        """
        # ✅ GỌI core logic - KHÔNG bỏ qua
        result = super()._action_done(cancel_backorder=cancel_backorder)

        # Update batch state if all moves done
        batches_to_update = self.mapped('batch_id').filtered(lambda b: b)
        for batch in batches_to_update:
            if all(move.state == 'done' for move in batch.move_ids):
                if batch.state == 'in_picking':
                    batch.state = 'shipped'

        return result

    def _update_reserved_quantity(
            self, need, location_id, lot_id=None, package_id=None,
            owner_id=None, strict=True
    ):

        result = super()._update_reserved_quantity(
            need, location_id,
            lot_id=lot_id, package_id=package_id,
            owner_id=owner_id, strict=strict
        )

        if self.batch_id:
            self.batch_id._compute_quantities()

        return result

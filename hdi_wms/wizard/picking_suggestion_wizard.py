# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime


class PickingSuggestionWizard(models.TransientModel):
    """Wizard gợi ý lấy hàng theo FIFO và ưu tiên vị trí"""
    _name = 'hdi.picking.suggestion.wizard'
    _description = 'Gợi ý lấy hàng xuất kho'

    picking_id = fields.Many2one(
        'stock.picking',
        string='Phiếu xuất kho',
        required=True,
        default=lambda self: self.env.context.get('default_picking_id'),
    )

    picking_type = fields.Selection(
        related='picking_id.picking_type_id.code',
        string='Loại phiếu',
    )

    suggestion_line_ids = fields.One2many(
        'hdi.picking.suggestion.line',
        'wizard_id',
        string='Gợi ý lấy hàng',
    )

    notes = fields.Text(
        string='Ghi chú',
        default='Danh sách gợi ý được sắp xếp theo:\n'
                '1. Nguyên tắc FIFO (hàng nhập trước xuất trước)\n'
                '2. Ưu tiên vị trí (location_priority thấp lấy trước)\n'
                '3. Batch có available_quantity đủ'
    )

    total_qty_needed = fields.Float(
        compute='_compute_total_qty',
        string='Tổng SL cần lấy',
    )

    total_qty_suggested = fields.Float(
        compute='_compute_total_qty',
        string='Tổng SL gợi ý',
    )

    @api.depends('suggestion_line_ids.qty_needed', 'suggestion_line_ids.suggested_qty')
    def _compute_total_qty(self):
        for wizard in self:
            wizard.total_qty_needed = sum(wizard.suggestion_line_ids.mapped('qty_needed'))
            wizard.total_qty_suggested = sum(wizard.suggestion_line_ids.mapped('suggested_qty'))

    @api.model
    def create(self, vals):
        """Auto-generate suggestions when wizard is created"""
        wizard = super().create(vals)
        if wizard.picking_id:
            wizard._generate_suggestions()
        return wizard

    def _generate_suggestions(self):
        """Generate FIFO-based picking suggestions"""
        self.suggestion_line_ids.unlink()

        if not self.picking_id or not self.picking_id.move_ids_without_package:
            return

        suggestions = []

        # Duyệt qua từng move cần xuất
        for move in self.picking_id.move_ids_without_package:
            product = move.product_id
            qty_needed = move.product_uom_qty
            qty_remaining = qty_needed

            # Tìm tất cả batch có sản phẩm này ở trạng thái 'stored'
            batches = self.env['hdi.batch'].search([
                ('product_id', '=', product.id),
                ('state', '=', 'stored'),
                ('available_quantity', '>', 0),
            ], order='create_date asc')  # FIFO only

            # Sort by location priority manually (if location has priority field)
            batches = batches.sorted(key=lambda b: (b.create_date, b.location_id.location_priority or 999))

            # Phân bổ số lượng vào các batch
            for batch in batches:
                if qty_remaining <= 0:
                    break

                available = batch.available_quantity
                qty_to_pick = min(available, qty_remaining)

                suggestions.append((0, 0, {
                    'product_id': product.id,
                    'batch_id': batch.id,
                    'location_id': batch.location_id.id,
                    'qty_needed': qty_needed,
                    'available_qty': available,
                    'suggested_qty': qty_to_pick,
                    'fifo_date': batch.create_date,
                    'sequence': len(suggestions) + 1,
                }))

                qty_remaining -= qty_to_pick

            # Cảnh báo nếu không đủ hàng
            if qty_remaining > 0:
                suggestions.append((0, 0, {
                    'product_id': product.id,
                    'qty_needed': qty_needed,
                    'available_qty': 0,
                    'suggested_qty': 0,
                    'warning': _('Thiếu %d sản phẩm trong kho') % qty_remaining,
                    'sequence': len(suggestions) + 1,
                }))

        self.suggestion_line_ids = suggestions

    def action_create_picking_list(self):
        """Tạo bảng kê lấy hàng từ gợi ý - Bước 4"""
        self.ensure_one()

        if not self.suggestion_line_ids:
            raise UserError(_('Không có gợi ý lấy hàng nào.'))

        # Tạo picking list
        picking_list = self.env['hdi.picking.list'].create({
            'picking_id': self.picking_id.id,
            'state': 'draft',
            'notes': _('Được tạo từ gợi ý FIFO'),
        })

        # Tạo các line từ suggestions
        for suggestion in self.suggestion_line_ids.filtered(lambda s: s.suggested_qty > 0):
            self.env['hdi.picking.list.line'].create({
                'picking_list_id': picking_list.id,
                'product_id': suggestion.product_id.id,
                'batch_id': suggestion.batch_id.id if suggestion.batch_id else False,
                'location_id': suggestion.location_id.id,
                'planned_qty': suggestion.suggested_qty,
                'sequence': suggestion.sequence,
            })

        # Mở bảng kê vừa tạo
        return {
            'name': _('Bảng kê lấy hàng'),
            'type': 'ir.actions.act_window',
            'res_model': 'hdi.picking.list',
            'res_id': picking_list.id,
            'view_mode': 'form',
            'target': 'current',
        }


class PickingSuggestionLine(models.TransientModel):
    """Chi tiết gợi ý lấy hàng"""
    _name = 'hdi.picking.suggestion.line'
    _description = 'Chi tiết gợi ý lấy hàng'
    _order = 'sequence, fifo_date'

    wizard_id = fields.Many2one(
        'hdi.picking.suggestion.wizard',
        string='Wizard',
        required=True,
        ondelete='cascade',
    )

    sequence = fields.Integer(string='Thứ tự', default=10)

    product_id = fields.Many2one(
        'product.product',
        string='Sản phẩm',
        required=True,
    )

    batch_id = fields.Many2one(
        'hdi.batch',
        string='Batch gợi ý',
    )

    location_id = fields.Many2one(
        'stock.location',
        string='Vị trí',
    )

    location_priority = fields.Integer(
        related='location_id.location_priority',
        string='Ưu tiên',
    )

    fifo_date = fields.Datetime(
        string='Ngày nhập (FIFO)',
        help="Batch create_date - dùng để sắp xếp FIFO"
    )

    qty_needed = fields.Float(
        string='SL cần',
        digits='Product Unit of Measure',
    )

    available_qty = fields.Float(
        string='SL có sẵn',
        digits='Product Unit of Measure',
    )

    suggested_qty = fields.Float(
        string='SL gợi ý lấy',
        digits='Product Unit of Measure',
    )

    warning = fields.Char(string='Cảnh báo')

    is_sufficient = fields.Boolean(
        compute='_compute_is_sufficient',
        string='Đủ hàng',
    )

    @api.depends('available_qty', 'suggested_qty')
    def _compute_is_sufficient(self):
        for line in self:
            line.is_sufficient = line.available_qty >= line.suggested_qty

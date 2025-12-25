# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class HdiLooseLine(models.Model):
    _name = 'hdi.loose.line'
    _description = 'Dòng hàng lẻ'
    _order = 'picking_id, sequence, id'

    sequence = fields.Integer(string='Thứ tự', default=10)

    picking_id = fields.Many2one(
        'stock.picking',
        string='Phiếu kho',
        required=True,
        ondelete='cascade',
        index=True,
    )

    move_id = fields.Many2one(
        'stock.move',
        string='Dòng dịch chuyển kho',
        help="Liên kết với bản ghi stock.move"
    )

    # ===== THÔNG TIN SẢN PHẨM =====
    product_id = fields.Many2one(
        'product.product',
        string='Sản phẩm',
        required=True,
    )

    product_uom_id = fields.Many2one(
        'uom.uom',
        string='Đơn vị tính',
        required=True,
    )

    quantity = fields.Float(
        string='Số lượng',
        required=True,
        digits='Product Unit of Measure',
    )

    # ===== KHO VẬN =====
    location_id = fields.Many2one(
        'stock.location',
        string='Vị trí nguồn',
        required=True,
    )

    location_dest_id = fields.Many2one(
        'stock.location',
        string='Vị trí đích',
        required=True,
    )

    # ===== THEO DÕI =====
    lot_id = fields.Many2one(
        'stock.lot',
        string='Lô/Số Serial',
    )

    barcode_scanned = fields.Char(
        string='Mã vạch quét được',
    )

    # ===== TRẠNG THÁI =====
    state = fields.Selection([
        ('pending', 'Chờ xử lý'),
        ('processing', 'Đang xử lý'),
        ('done', 'Hoàn thành'),
        ('cancel', 'Hủy'),
    ], string='Trạng thái', default='pending')

    notes = fields.Text(string='Ghi chú')

    company_id = fields.Many2one(
        'res.company',
        related='picking_id.company_id',
        store=True,
        readonly=True,
        string="Công ty",
    )

    @api.model
    def create(self, vals):
        result = super().create(vals)
        if not result.move_id and result.picking_id:
            move_vals = {
                'name': result.product_id.name,
                'product_id': result.product_id.id,
                'product_uom': result.product_uom_id.id,
                'product_uom_qty': result.quantity,
                'location_id': result.location_id.id,
                'location_dest_id': result.location_dest_id.id,
                'picking_id': result.picking_id.id,
                'loose_line_id': result.id,
                'company_id': result.company_id.id,
            }
            move = self.env['stock.move'].create(move_vals)
            result.move_id = move.id

        return result

    def write(self, vals):
        result = super().write(vals)

        # Đồng bộ thông tin sang stock.move
        move_vals = {}
        if 'quantity' in vals:
            move_vals['product_uom_qty'] = vals['quantity']
        if 'location_id' in vals:
            move_vals['location_id'] = vals['location_id']
        if 'location_dest_id' in vals:
            move_vals['location_dest_id'] = vals['location_dest_id']

        if move_vals:
            for line in self:
                if line.move_id:
                    line.move_id.write(move_vals)

        return result

    def action_process(self):
        self.write({'state': 'processing'})

    def action_done(self):
        for line in self:
            if line.move_id and line.move_id.state not in ['done', 'cancel']:
                line.move_id._action_done()
            line.state = 'done'

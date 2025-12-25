# -*- coding: utf-8 -*-

from odoo import models, fields, api


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    # ===== INVENTORY CHECK TYPE (2 workflows) =====
    check_type = fields.Selection([
        ('batch', 'Kiểm kê theo Batch'),
        ('barcode', 'Kiểm kê theo Barcode')
    ], string='Loại kiểm kê', default='batch',
        help="Chọn luồng kiểm kê: Batch (theo lô) hoặc Barcode (quét từng mã)")

    batch_id = fields.Many2one(
        'hdi.batch',
        string='Batch/LPN',
        index=True,
        help="Batch containing this inventory quant"
    )

    is_batched = fields.Boolean(
        compute='_compute_is_batched',
        store=True,
        string='Is Batched',
    )

    scan_mode = fields.Boolean(
        string='Chế độ quét',
        default=False,
        help="Bật để quét barcode liên tục (chỉ dùng cho KK_NV_02)"
    )

    last_scanned_code = fields.Char(
        string='Mã vừa quét',
        readonly=True,
        help="Barcode cuối cùng được quét"
    )

    scanned_count = fields.Integer(
        string='Số lần quét',
        default=0,
        help="Đếm số lần quét barcode"
    )

    @api.depends('batch_id')
    def _compute_is_batched(self):
        for quant in self:
            quant.is_batched = bool(quant.batch_id)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            if record.check_type == 'batch' and record.batch_id and not record.product_id:
                existing_quants = self.search([
                    ('location_id', '=', record.location_id.id),
                    ('batch_id', '=', record.batch_id.id),
                    ('id', '!=', record.id)
                ])

                if existing_quants:
                    first_quant = existing_quants[0]
                    record.write({
                        'product_id': first_quant.product_id.id,
                        'lot_id': first_quant.lot_id.id if first_quant.lot_id else False,
                        'package_id': first_quant.package_id.id if first_quant.package_id else False,
                    })

        return records

    def write(self, vals):
        result = super().write(vals)

        # If location changed, update batch location
        if 'location_id' in vals:
            for quant in self:
                if quant.batch_id and quant.batch_id.location_id != quant.location_id:
                    quant.batch_id.location_id = quant.location_id

        if 'quantity' in vals or 'reserved_quantity' in vals:
            batches = self.mapped('batch_id').filtered(lambda b: b)
            batches._compute_quantities()

        if 'batch_id' in vals and vals.get('batch_id'):
            for quant in self:
                if quant.check_type == 'batch' and quant.batch_id:
                    existing_quants = self.search([
                        ('location_id', '=', quant.location_id.id),
                        ('batch_id', '=', quant.batch_id.id),
                        ('id', '!=', quant.id)
                    ], limit=1)

                    if existing_quants:
                        quant.write({
                            'product_id': existing_quants.product_id.id,
                            'lot_id': existing_quants.lot_id.id if existing_quants.lot_id else False,
                        })

        return result

    @api.onchange('check_type')
    def _onchange_check_type(self):
        if self.check_type != 'barcode':
            self.scan_mode = False
            self.last_scanned_code = False
            self.scanned_count = 0

    def action_toggle_scan_mode(self):
        self.ensure_one()
        self.scan_mode = not self.scan_mode
        if self.scan_mode:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Chế độ quét Barcode',
                    'message': 'Đã bật chế độ quét. Vui lòng quét barcode sản phẩm.',
                    'type': 'success',
                    'sticky': False,
                }
            }

    def on_barcode_scanned(self, barcode):
        self.ensure_one()

        if not self.scan_mode:
            return {
                'warning': {
                    'title': 'Lỗi',
                    'message': 'Vui lòng bật chế độ quét trước!'
                }
            }

        self.last_scanned_code = barcode
        self.scanned_count += 1

        # Try to find product by barcode
        product = self.env['product.product'].search([
            '|', ('barcode', '=', barcode),
            ('default_code', '=', barcode)
        ], limit=1)

        if product:
            # Update inventory quantity for this product
            self.product_id = product
            self.inventory_quantity += 1  # Increment counted quantity

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Đã quét',
                    'message': f'Sản phẩm: {product.name} | Tổng: {self.inventory_quantity}',
                    'type': 'info',
                    'sticky': False,
                }
            }
        else:
            return {
                'warning': {
                    'title': 'Không tìm thấy',
                    'message': f'Không tìm thấy sản phẩm với barcode: {barcode}'
                }
            }


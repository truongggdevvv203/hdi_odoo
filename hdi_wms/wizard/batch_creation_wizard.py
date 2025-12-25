# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class BatchCreationWizard(models.TransientModel):
    _name = 'hdi.batch.creation.wizard'
    _description = 'Batch Creation Wizard'

    picking_id = fields.Many2one(
        'stock.picking',
        string='Picking',
        required=True,
        default=lambda self: self.env.context.get('default_picking_id'),
    )

    mode = fields.Selection([
        ('new', 'Tạo Lô mới'),
        ('existing', 'Chọn Lô có sẵn'),
    ], string='Chế độ', default='new', required=True)

    existing_batch_id = fields.Many2one(
        'hdi.batch',
        string='Chọn Lô hàng',
        domain="[('state', 'in', ['draft', 'in_receiving', 'in_putaway']), '|', ('picking_id', '=', False), ('picking_id', '=', picking_id)]",
        help="Chọn lô hàng đang có sẵn chưa hoàn thành"
    )

    batch_type = fields.Selection([
        ('pallet', 'Pallet'),
        ('lpn', 'LPN'),
        ('container', 'Container'),
    ], string='Batch Type', default='pallet', required=True)

    product_id = fields.Many2one(
        'product.product',
        string='Product',
        help="Leave empty for mixed product batch"
    )

    quantity = fields.Float(
        string='Quantity',
        digits='Product Unit of Measure',
    )

    location_id = fields.Many2one(
        'stock.location',
        string='Current Location',
        required=True,
    )

    auto_generate_barcode = fields.Boolean(
        string='Auto Generate Barcode',
        default=True,
    )

    barcode = fields.Char(string='Barcode/LPN')

    weight = fields.Float(string='Weight (kg)')
    volume = fields.Float(string='Volume (m³)')

    # Import document fields
    import_invoice_number = fields.Char(string='Import Invoice / Hóa đơn nhập khẩu')
    import_packing_list = fields.Char(string='Import Packing List / Phiếu đóng gói')
    import_bill_of_lading = fields.Char(string='Bill of Lading / Vận đơn')

    def action_create_batch(self):
        """Create batch or link existing batch to picking"""
        self.ensure_one()

        if self.mode == 'existing':
            # Use existing batch
            if not self.existing_batch_id:
                raise UserError(_('Vui lòng chọn lô hàng có sẵn hoặc chuyển sang chế độ Tạo mới.'))

            batch = self.existing_batch_id

            # Link to picking if not already linked
            if not batch.picking_id:
                batch.write({'picking_id': self.picking_id.id})

            # Update picking WMS state
            if self.picking_id.wms_state == 'none':
                self.picking_id.wms_state = 'batch_creation'

            return {
                'name': _('Đã chọn Lô hàng'),
                'type': 'ir.actions.act_window',
                'res_model': 'hdi.batch',
                'res_id': batch.id,
                'view_mode': 'form',
                'target': 'current',
            }

        else:
            # Create new batch
            vals = {
                'picking_id': self.picking_id.id,
                'batch_type': self.batch_type,
                'product_id': self.product_id.id if self.product_id else False,
                'planned_quantity': self.quantity,
                'location_id': self.location_id.id,
                'weight': self.weight,
                'volume': self.volume,
                'state': 'in_receiving',
                'company_id': self.picking_id.company_id.id,
            }

            if self.barcode:
                vals['barcode'] = self.barcode

            # Import document references
            if self.import_invoice_number:
                vals['import_invoice_number'] = self.import_invoice_number
            if self.import_packing_list:
                vals['import_packing_list'] = self.import_packing_list
            if self.import_bill_of_lading:
                vals['import_bill_of_lading'] = self.import_bill_of_lading

            # Create batch
            batch = self.env['hdi.batch'].create(vals)

            # Update picking WMS state
            if self.picking_id.wms_state == 'none':
                self.picking_id.wms_state = 'batch_creation'

            # Return to batch form
            return {
                'name': _('Đã tạo Lô hàng'),
                'type': 'ir.actions.act_window',
                'res_model': 'hdi.batch',
                'res_id': batch.id,
                'view_mode': 'form',
                'target': 'current',
            }

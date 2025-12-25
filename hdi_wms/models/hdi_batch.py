# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class HdiBatch(models.Model):
    _name = 'hdi.batch'
    _description = 'Batch / LPN / Pallet'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'barcodes.barcode_events_mixin']
    _order = 'create_date desc, id desc'

    # ===== BASIC INFO =====
    name = fields.Char(
        string='Batch Number',
        required=True,
        copy=False,
        readonly=True,
        index=True,
        default=lambda self: _('New'),
        tracking=True,
    )

    barcode = fields.Char(
        string='Barcode/LPN',
        copy=False,
        index=True,
        tracking=True,
        help="Barcode or License Plate Number for scanning"
    )

    batch_type = fields.Selection([
        ('pallet', 'Pallet'),
        ('lpn', 'LPN'),
        ('container', 'Container'),
        ('loose', 'Loose Items'),
    ], string='Batch Type', default='pallet', required=True, tracking=True)

    picking_id = fields.Many2one(
        'stock.picking',
        string='Related Picking',
        index=True,
        tracking=True,
        help="Link to core stock.picking (Incoming/Outgoing/Internal Transfer)"
    )

    move_ids = fields.One2many(
        'stock.move',
        'batch_id',
        string='Stock Moves',
        help="All stock.move linked to this batch - maintains core inventory flow"
    )

    quant_ids = fields.One2many(
        'stock.quant',
        'batch_id',
        string='Quants',
        help="Actual inventory quants in this batch - CORE inventory data"
    )

    putaway_suggestion_ids = fields.One2many(
        'hdi.putaway.suggestion',
        'batch_id',
        string='Putaway Suggestions',
        help="Location suggestions for this batch"
    )

    location_id = fields.Many2one(
        'stock.location',
        string='Current Location',
        required=True,
        index=True,
        tracking=True,
        help="Current storage location (from core stock.location)"
    )

    location_dest_id = fields.Many2one(
        'stock.location',
        string='Destination Location',
        tracking=True,
        help="Planned destination for putaway"
    )

    # ===== WMS SPECIFIC FIELDS =====
    state = fields.Selection([
        ('draft', 'Mới tạo'),
        ('in_receiving', 'Đang nhận hàng'),
        ('in_putaway', 'Đang đưa vào vị trí'),
        ('stored', 'Đã vào vị trí'),
        ('in_picking', 'Đang lấy hàng'),
        ('shipped', 'Đã xuất kho'),
        ('cancel', 'Đã hủy'),
    ], string='Trạng thái', default='draft', required=True, tracking=True)

    wms_status = fields.Selection([
        ('empty', 'Trống'),
        ('partial', 'Chứa một phần'),
        ('full', 'Đầy'),
        ('mixed', 'Nhiều sản phẩm'),
    ], string='Tình trạng WMS', compute='_compute_wms_status', store=True)

    # ===== PRODUCT & QUANTITY =====
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        help="Primary product (for single-product batches)"
    )

    planned_quantity = fields.Float(
        string='Planned Quantity',
        digits='Product Unit of Measure',
        help="Expected quantity (entered when creating batch, before actual receipt)"
    )

    total_quantity = fields.Float(
        string='Total Quantity',
        compute='_compute_quantities',
        store=True,
        help="Total quantity from all quants"
    )

    available_quantity = fields.Float(
        string='Available Quantity',
        compute='_compute_quantities',
        store=True,
    )

    reserved_quantity = fields.Float(
        string='Reserved Quantity',
        compute='_compute_quantities',
        store=True,
    )

    # ===== PHYSICAL ATTRIBUTES =====
    weight = fields.Float(string='Trọng lượng (kg)', digits='Stock Weight')
    volume = fields.Float(string='Thể tích (m³)', digits=(16, 4))
    height = fields.Float(string='Chiều cao (cm)', digits=(16, 2))
    width = fields.Float(string='Chiều rộng (cm)', digits=(16, 2))
    length = fields.Float(string='Chiều dài (cm)', digits=(16, 2))

    user_id = fields.Many2one(
        'res.users',
        string='Responsible',
        default=lambda self: self.env.user,
        tracking=True,
    )

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True,
    )

    notes = fields.Text(string='Notes')

    # ===== IMPORT / INBOUND DOCUMENTS =====
    import_invoice_number = fields.Char(
        string='Import Invoice Number',
        help='Số hóa đơn nhập khẩu / Import invoice reference'
    )
    import_packing_list = fields.Char(
        string='Import Packing List',
        help='Phiếu đóng gói / Packing list reference'
    )
    import_bill_of_lading = fields.Char(
        string='Bill of Lading',
        help='Vận đơn / Bill of Lading reference'
    )

    # ===== COMPUTED FIELDS =====
    move_count = fields.Integer(compute='_compute_counts', string='Moves')
    quant_count = fields.Integer(compute='_compute_counts', string='Quants')
    product_count = fields.Integer(
        compute='_compute_product_count',
        string='Products',
        help="Number of different products in this batch"
    )

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('hdi.batch') or _('New')
        return super().create(vals)

    def name_get(self):
        """Custom display name showing batch info"""
        result = []
        for batch in self:
            name_parts = [batch.name]

            # Add barcode if exists
            if batch.barcode:
                name_parts.append(f"[{batch.barcode}]")

            # Add product info
            if batch.product_id:
                name_parts.append(f"- {batch.product_id.name}")

            # Add quantity info
            qty = batch.total_quantity or batch.planned_quantity or 0
            if qty > 0:
                name_parts.append(f"({qty:.0f})")

            # Add state
            state_label = dict(batch._fields['state'].selection).get(batch.state, '')
            if state_label:
                name_parts.append(f"[{state_label}]")

            name = ' '.join(name_parts)
            result.append((batch.id, name))
        return result

    @api.depends('quant_ids', 'quant_ids.quantity', 'quant_ids.reserved_quantity')
    def _compute_quantities(self):
        for batch in self:
            batch.total_quantity = sum(batch.quant_ids.mapped('quantity'))
            batch.available_quantity = sum(
                quant.quantity - quant.reserved_quantity
                for quant in batch.quant_ids
            )
            batch.reserved_quantity = sum(batch.quant_ids.mapped('reserved_quantity'))

    @api.depends('quant_ids', 'product_id')
    def _compute_wms_status(self):
        for batch in self:
            if not batch.quant_ids or batch.total_quantity == 0:
                batch.wms_status = 'empty'
            elif len(batch.quant_ids.mapped('product_id')) > 1:
                batch.wms_status = 'mixed'
            elif batch.reserved_quantity > 0 and batch.available_quantity > 0:
                batch.wms_status = 'partial'
            else:
                batch.wms_status = 'full'

    @api.depends('move_ids', 'quant_ids')
    def _compute_counts(self):
        for batch in self:
            batch.move_count = len(batch.move_ids)
            batch.quant_count = len(batch.quant_ids)

    @api.depends('quant_ids.product_id')
    def _compute_product_count(self):
        """Count distinct products in batch"""
        for batch in self:
            batch.product_count = len(batch.quant_ids.mapped('product_id'))

    def action_start_receiving(self):
        """Start receiving process"""
        self.ensure_one()
        if self.state != 'draft':
            raise UserError(_('Only draft batches can start receiving.'))
        self.state = 'in_receiving'

    def action_start_putaway(self):
        """Move batch to putaway process"""
        self.ensure_one()
        if self.state != 'in_receiving':
            raise UserError(_('Batch must be in receiving to start putaway.'))
        if not self.location_dest_id:
            # Trigger putaway suggestion
            return self.action_suggest_putaway()
        self.state = 'in_putaway'

    def action_confirm_storage(self):
        self.ensure_one()
        if self.state != 'in_putaway':
            raise UserError(_('Batch must be in putaway to confirm storage.'))

        if not self.location_dest_id:
            raise UserError(_('Please set destination location first.'))

        # Update quants to destination location (CORE operation)
        for quant in self.quant_ids:
            if quant.location_id != self.location_dest_id:
                quant.location_id = self.location_dest_id

        self.location_id = self.location_dest_id
        self.state = 'stored'

    # ===== OUTGOING / PICKING OPERATIONS =====
    def action_start_picking(self):
        """Bắt đầu lấy hàng cho xuất kho"""
        self.ensure_one()
        if self.state != 'stored':
            raise UserError(_('Chỉ có thể lấy hàng từ batch đã lưu kho (stored).'))
        
        if self.available_quantity <= 0:
            raise UserError(_('Batch này không có hàng khả dụng để lấy.'))
        
        self.state = 'in_picking'

    def action_confirm_picked(self):
        """Xác nhận đã lấy hàng xong, sẵn sàng xuất kho"""
        self.ensure_one()
        if self.state != 'in_picking':
            raise UserError(_('Batch phải ở trạng thái "Đang lấy hàng".'))
        
        # Không chuyển sang shipped ngay, đợi stock.move done
        # State shipped sẽ được set tự động trong stock_move._action_done()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Đã xác nhận'),
                'message': _('Batch %s đã sẵn sàng xuất kho') % self.name,
                'type': 'success',
                'sticky': False,
            }
        }

    def action_suggest_putaway(self):
        self.ensure_one()
        return {
            'name': _('Suggest Putaway Location'),
            'type': 'ir.actions.act_window',
            'res_model': 'hdi.putaway.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_batch_id': self.id,
                'default_product_id': self.product_id.id if self.product_id else False,
            }
        }

    def action_view_moves(self):
        """View all stock moves linked to this batch"""
        self.ensure_one()
        return {
            'name': _('Stock Moves'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.move',
            'view_mode': 'list,form',
            'domain': [('batch_id', '=', self.id)],
            'context': {'create': False},
        }

    def action_view_quants(self):
        """View all quants (inventory) in this batch"""
        self.ensure_one()
        return {
            'name': _('Inventory Quants'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.quant',
            'view_mode': 'list,form',
            'domain': [('batch_id', '=', self.id)],
            'context': {'create': False},
        }

    @api.constrains('barcode')
    def _check_unique_barcode(self):
        """Ensure barcode is unique"""
        for batch in self:
            if batch.barcode:
                duplicate = self.search([
                    ('id', '!=', batch.id),
                    ('barcode', '=', batch.barcode),
                    ('state', '!=', 'cancel'),
                ], limit=1)
                if duplicate:
                    raise ValidationError(_(
                        'Barcode %s is already used by batch %s'
                    ) % (batch.barcode, duplicate.name))

    def on_barcode_scanned(self, barcode):
        pass

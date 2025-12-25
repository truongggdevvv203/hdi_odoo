# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class HdiPickingList(models.Model):
    """Bảng kê lấy hàng - Picking List for warehouse operations"""
    _name = 'hdi.picking.list'
    _description = 'Bảng kê lấy hàng'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc, id desc'

    # ===== BASIC INFO =====
    name = fields.Char(
        string='Mã bảng kê',
        required=True,
        copy=False,
        readonly=True,
        index=True,
        default=lambda self: _('New'),
        tracking=True,
    )

    picking_id = fields.Many2one(
        'stock.picking',
        string='Phiếu xuất kho',
        required=True,
        index=True,
        tracking=True,
        ondelete='cascade',
    )

    picking_type = fields.Selection(
        related='picking_id.picking_type_id.code',
        string='Loại phiếu',
        store=True,
    )

    # ===== PHÂN LOẠI XUẤT KHO =====
    outgoing_type = fields.Selection([
        ('sale', 'Xuất bán hàng'),
        ('transfer', 'Chuyển kho thành phẩm khác'),
        ('production', 'Chuyển về kho sản xuất'),
        ('other', 'Xuất khác'),
    ], string='Loại xuất kho',
        compute='_compute_outgoing_type',
        store=True,
        tracking=True,
        help="Phân loại theo mục đích xuất kho")

    destination_warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Kho đích',
        help="Kho thành phẩm đích (nếu chuyển kho)"
    )

    # ===== NGƯỜI THỰC HIỆN =====
    created_by_id = fields.Many2one(
        'res.users',
        string='Người tạo',
        default=lambda self: self.env.user,
        readonly=True,
        tracking=True,
    )

    assigned_user_id = fields.Many2one(
        'res.users',
        string='Người thực hiện',
        tracking=True,
        help="Nhân viên kho được gán thực hiện lấy hàng"
    )

    # ===== TRẠNG THÁI =====
    state = fields.Selection([
        ('draft', 'Mới tạo'),
        ('waiting', 'Chờ thực hiện'),
        ('in_progress', 'Đang thực hiện'),
        ('done', 'Đã thực hiện'),
        ('scanned', 'Đã quét barcode'),
        ('completed', 'Hoàn thành'),
        ('cancel', 'Đã hủy'),
    ], string='Trạng thái', default='draft', required=True, tracking=True)

    # ===== CHI TIẾT LẤY HÀNG =====
    line_ids = fields.One2many(
        'hdi.picking.list.line',
        'picking_list_id',
        string='Chi tiết lấy hàng',
    )

    line_count = fields.Integer(
        compute='_compute_line_count',
        string='Số dòng',
    )

    # ===== THỐNG KÊ =====
    total_planned_qty = fields.Float(
        compute='_compute_quantities',
        string='Tổng SL dự kiến',
        store=True,
    )

    total_picked_qty = fields.Float(
        compute='_compute_quantities',
        string='Tổng SL đã lấy',
        store=True,
    )

    total_scanned_qty = fields.Float(
        compute='_compute_quantities',
        string='Tổng SL đã quét',
        store=True,
    )

    completion_rate = fields.Float(
        compute='_compute_completion_rate',
        string='Tỷ lệ hoàn thành (%)',
        store=True,
    )

    # ===== THỜI GIAN =====
    assigned_date = fields.Datetime(
        string='Thời gian gán',
        readonly=True,
    )

    start_date = fields.Datetime(
        string='Bắt đầu thực hiện',
        readonly=True,
    )

    done_date = fields.Datetime(
        string='Hoàn thành lấy hàng',
        readonly=True,
    )

    scanned_date = fields.Datetime(
        string='Hoàn thành quét',
        readonly=True,
    )

    # ===== GHI CHÚ =====
    notes = fields.Text(string='Ghi chú')

    warning_message = fields.Text(
        compute='_compute_warning_message',
        string='Cảnh báo',
    )

    company_id = fields.Many2one(
        'res.company',
        string='Công ty',
        default=lambda self: self.env.company,
        required=True,
    )

    @api.depends('picking_id', 'picking_id.location_dest_id', 'picking_id.partner_id')
    def _compute_outgoing_type(self):
        """Tự động phân loại xuất kho dựa vào destination"""
        for rec in self:
            if not rec.picking_id:
                rec.outgoing_type = 'other'
                continue

            dest_location = rec.picking_id.location_dest_id

            # Xuất bán hàng: customer location
            if dest_location.usage == 'customer':
                rec.outgoing_type = 'sale'
            # Chuyển kho: internal location của warehouse khác
            elif dest_location.usage == 'internal' and dest_location.warehouse_id != rec.picking_id.location_id.warehouse_id:
                rec.outgoing_type = 'transfer'
                rec.destination_warehouse_id = dest_location.warehouse_id
            # Chuyển về sản xuất: production location
            elif dest_location.usage == 'production':
                rec.outgoing_type = 'production'
            else:
                rec.outgoing_type = 'other'

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('hdi.picking.list') or _('New')
        return super().create(vals)

    @api.depends('line_ids')
    def _compute_line_count(self):
        for rec in self:
            rec.line_count = len(rec.line_ids)

    @api.depends('line_ids.planned_qty', 'line_ids.picked_qty', 'line_ids.scanned_qty')
    def _compute_quantities(self):
        for rec in self:
            rec.total_planned_qty = sum(rec.line_ids.mapped('planned_qty'))
            rec.total_picked_qty = sum(rec.line_ids.mapped('picked_qty'))
            rec.total_scanned_qty = sum(rec.line_ids.mapped('scanned_qty'))

    @api.depends('total_planned_qty', 'total_picked_qty')
    def _compute_completion_rate(self):
        for rec in self:
            if rec.total_planned_qty > 0:
                rec.completion_rate = (rec.total_picked_qty / rec.total_planned_qty) * 100
            else:
                rec.completion_rate = 0

    @api.depends('line_ids', 'line_ids.warning')
    def _compute_warning_message(self):
        for rec in self:
            warnings = rec.line_ids.filtered(lambda l: l.warning).mapped('warning')
            rec.warning_message = '\n'.join(warnings) if warnings else ''

    def action_assign_user(self):
        """Gán người thực hiện - Bước 4"""
        self.ensure_one()
        if not self.assigned_user_id:
            raise UserError(_('Vui lòng chọn người thực hiện.'))

        self.write({
            'state': 'waiting',
            'assigned_date': fields.Datetime.now(),
        })

        # Gửi thông báo cho nhân viên kho
        self.message_post(
            body=_('Bảng kê lấy hàng đã được gán cho %s') % self.assigned_user_id.name,
            subject=_('Thông báo lấy hàng'),
            partner_ids=[self.assigned_user_id.partner_id.id],
        )

    def action_start_picking(self):
        """Bắt đầu thực hiện lấy hàng - Bước 7"""
        self.ensure_one()
        if self.state != 'waiting':
            raise UserError(_('Chỉ có thể bắt đầu với bảng kê ở trạng thái "Chờ thực hiện".'))

        self.write({
            'state': 'in_progress',
            'start_date': fields.Datetime.now(),
        })

    def action_confirm_picked(self):
        """Xác nhận đã lấy hàng xong - Bước 9"""
        self.ensure_one()
        if self.state != 'in_progress':
            raise UserError(_('Chỉ có thể xác nhận với bảng kê đang thực hiện.'))

        # Kiểm tra các line đã được xác nhận
        unpicked_lines = self.line_ids.filtered(lambda l: not l.is_picked)
        if unpicked_lines:
            raise UserError(_(
                'Vẫn còn %d vị trí chưa xác nhận lấy hàng.\n'
                'Vui lòng xác nhận tất cả các vị trí hoặc đánh dấu "Không có hàng".'
            ) % len(unpicked_lines))

        self.write({
            'state': 'done',
            'done_date': fields.Datetime.now(),
        })

        # Thông báo cho quản lý kho
        self.message_post(
            body=_('Đã hoàn thành lấy hàng. Tổng SL: %d') % self.total_picked_qty,
            subject=_('Hoàn thành lấy hàng'),
            partner_ids=[self.created_by_id.partner_id.id],
        )

    def action_start_scan_barcode(self):
        """Bắt đầu quét barcode - Bước 13"""
        self.ensure_one()
        if self.state != 'done':
            raise UserError(_('Chỉ có thể quét barcode sau khi hoàn thành lấy hàng.'))

        return {
            'name': _('Quét Barcode - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'hdi.picking.list',
            'res_id': self.id,
            'view_mode': 'form',
            'views': [(self.env.ref('hdi_wms.view_picking_list_form_scanner').id, 'form')],
            'target': 'fullscreen',
        }

    def action_confirm_scanned(self):
        """Xác nhận đã quét barcode xong - Bước 15.2"""
        self.ensure_one()
        if self.state != 'done':
            raise UserError(_('Chỉ có thể xác nhận quét sau khi hoàn thành lấy hàng.'))

        # Kiểm tra đã quét đủ barcode
        if self.total_scanned_qty < self.total_picked_qty:
            raise UserError(_(
                'Chưa quét đủ barcode.\n'
                'Đã quét: %d / Cần quét: %d'
            ) % (self.total_scanned_qty, self.total_picked_qty))

        self.write({
            'state': 'scanned',
            'scanned_date': fields.Datetime.now(),
        })

        # Thông báo sẵn sàng xuất kho
        self.message_post(
            body=_('Đã quét barcode xong. Sẵn sàng xuất kho.'),
            subject=_('Sẵn sàng xuất kho'),
            partner_ids=[self.created_by_id.partner_id.id],
        )

    def action_complete(self):
        """Hoàn thành bảng kê - Bước 11.2"""
        self.ensure_one()
        if self.state != 'scanned':
            raise UserError(_('Chỉ có thể hoàn thành sau khi quét barcode xong.'))

        self.state = 'completed'

    def action_cancel(self):
        """Hủy bảng kê"""
        self.ensure_one()
        if self.state == 'completed':
            raise UserError(_('Không thể hủy bảng kê đã hoàn thành.'))

        self.state = 'cancel'

    def action_create_supplementary_list(self):
        """Tạo bảng kê bổ sung - Bước 11.1"""
        self.ensure_one()

        # Tính số lượng thiếu
        shortage_lines = self.line_ids.filtered(lambda l: l.picked_qty < l.planned_qty)
        if not shortage_lines:
            raise UserError(_('Không có vị trí nào thiếu hàng.'))

        # Tạo bảng kê mới
        new_list = self.copy({
            'name': _('New'),
            'state': 'draft',
            'line_ids': False,
            'notes': _('Bảng kê bổ sung từ %s') % self.name,
        })

        # Tạo các line thiếu
        for line in shortage_lines:
            shortage_qty = line.planned_qty - line.picked_qty
            if shortage_qty > 0:
                self.env['hdi.picking.list.line'].create({
                    'picking_list_id': new_list.id,
                    'product_id': line.product_id.id,
                    'batch_id': line.batch_id.id,
                    'location_id': line.location_id.id,
                    'planned_qty': shortage_qty,
                    'sequence': line.sequence,
                })

        return {
            'name': _('Bảng kê bổ sung'),
            'type': 'ir.actions.act_window',
            'res_model': 'hdi.picking.list',
            'res_id': new_list.id,
            'view_mode': 'form',
            'target': 'current',
        }


class HdiPickingListLine(models.Model):
    """Chi tiết bảng kê lấy hàng"""
    _name = 'hdi.picking.list.line'
    _description = 'Chi tiết bảng kê lấy hàng'
    _order = 'sequence, location_priority, id'

    picking_list_id = fields.Many2one(
        'hdi.picking.list',
        string='Bảng kê',
        required=True,
        ondelete='cascade',
        index=True,
    )

    sequence = fields.Integer(string='Thứ tự', default=10)

    # ===== SẢN PHẨM =====
    product_id = fields.Many2one(
        'product.product',
        string='Sản phẩm',
        required=True,
    )

    # ===== VỊ TRÍ VÀ BATCH =====
    location_id = fields.Many2one(
        'stock.location',
        string='Vị trí lấy',
        required=True,
        domain="[('usage', '=', 'internal')]"
    )

    location_priority = fields.Integer(
        related='location_id.location_priority',
        string='Ưu tiên vị trí',
        store=True,
    )

    batch_id = fields.Many2one(
        'hdi.batch',
        string='Batch/LPN',
        domain="[('location_id', '=', location_id), ('product_id', '=', product_id), ('state', '=', 'stored')]"
    )

    # ===== SỐ LƯỢNG =====
    planned_qty = fields.Float(
        string='SL dự kiến',
        required=True,
        digits='Product Unit of Measure',
    )

    available_qty = fields.Float(
        compute='_compute_available_qty',
        string='SL có sẵn',
        store=True,
    )

    picked_qty = fields.Float(
        string='SL đã lấy',
        digits='Product Unit of Measure',
        default=0,
    )

    scanned_qty = fields.Float(
        string='SL đã quét',
        digits='Product Unit of Measure',
        default=0,
    )

    # ===== TRẠNG THÁI =====
    is_picked = fields.Boolean(
        string='Đã lấy',
        default=False,
        help="Nhân viên đã xác nhận lấy hàng từ vị trí này"
    )

    is_out_of_stock = fields.Boolean(
        string='Không có hàng',
        default=False,
        help="Xác nhận vị trí này không có hàng hoặc không đủ hàng"
    )

    is_location_changed = fields.Boolean(
        string='Đã đổi vị trí',
        default=False,
    )

    new_location_id = fields.Many2one(
        'stock.location',
        string='Vị trí mới',
        domain="[('usage', '=', 'internal')]"
    )

    # ===== BARCODE =====
    scanned_barcodes = fields.Text(
        string='Barcode đã quét',
        help="Danh sách barcode đã quét (JSON hoặc text)"
    )

    # ===== CẢNH BÁO =====
    warning = fields.Char(
        compute='_compute_warning',
        string='Cảnh báo',
    )

    notes = fields.Text(string='Ghi chú')

    company_id = fields.Many2one(
        related='picking_list_id.company_id',
        store=True,
        readonly=True,
    )

    @api.depends('location_id', 'product_id', 'batch_id')
    def _compute_available_qty(self):
        """Tính số lượng có sẵn tại vị trí"""
        for line in self:
            if line.batch_id:
                line.available_qty = line.batch_id.available_quantity
            elif line.location_id and line.product_id:
                quants = self.env['stock.quant'].search([
                    ('location_id', '=', line.location_id.id),
                    ('product_id', '=', line.product_id.id),
                ])
                line.available_qty = sum(q.quantity - q.reserved_quantity for q in quants)
            else:
                line.available_qty = 0

    @api.depends('planned_qty', 'available_qty', 'is_out_of_stock')
    def _compute_warning(self):
        """Cảnh báo nếu không đủ hàng"""
        for line in self:
            if line.is_out_of_stock:
                line.warning = _('Vị trí không có hàng')
            elif line.available_qty < line.planned_qty:
                line.warning = _('Không đủ hàng: Có %d / Cần %d') % (line.available_qty, line.planned_qty)
            else:
                line.warning = ''

    def action_confirm_picked(self):
        """Xác nhận đã lấy hàng - Bước 8.2"""
        self.ensure_one()
        if self.picked_qty <= 0:
            self.picked_qty = self.planned_qty

        self.is_picked = True

        # Chuyển batch sang trạng thái picking
        if self.batch_id and self.batch_id.state == 'stored':
            self.batch_id.action_start_picking()

    def action_mark_out_of_stock(self):
        """Xác nhận không có hàng - Bước 8.1"""
        self.ensure_one()
        self.write({
            'is_out_of_stock': True,
            'is_picked': True,
            'picked_qty': 0,
        })

    def action_change_location(self):
        """Sửa vị trí lấy hàng - Bước 8.1.1"""
        self.ensure_one()
        if not self.new_location_id:
            raise UserError(_('Vui lòng chọn vị trí mới.'))

        self.write({
            'location_id': self.new_location_id.id,
            'is_location_changed': True,
            'new_location_id': False,
        })

        # Tính lại available_qty
        self._compute_available_qty()

# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    batch_ids = fields.One2many(
        'hdi.batch',
        'picking_id',
        string='Batches',
        help="All batches created from this picking"
    )

    batch_count = fields.Integer(
        compute='_compute_batch_count',
        string='Batch Count',
    )

    wms_state = fields.Selection([
        ('none', 'No WMS'),
        ('batch_creation', 'Batch Creation'),
        ('putaway_pending', 'Putaway Pending'),
        ('putaway_done', 'Putaway Done'),
        ('picking_ready', 'Ready to Pick'),
        ('picking_progress', 'Picking in Progress'),
        ('wms_done', 'WMS Complete'),
    ], string='WMS State', default='none', tracking=True,
        help="WMS workflow state - parallel to Odoo core picking state")

    use_batch_management = fields.Boolean(
        string='Use Batch Management',
        default=False,
        help="Enable batch/LPN management for this picking"
    )

    require_putaway_suggestion = fields.Boolean(
        string='Require Putaway Suggestion',
        compute='_compute_require_putaway',
        store=True,
        help="Auto-enabled for incoming pickings"
    )

    loose_line_ids = fields.One2many(
        'hdi.loose.line',
        'picking_id',
        string='Loose Items',
        help="Items not in any batch (loose picking)"
    )

    # ===== SCANNER SUPPORT =====
    last_scanned_barcode = fields.Char(
        string='Last Scanned',
        readonly=True,
    )

    scan_mode = fields.Selection([
        ('none', 'Không quét'),
        ('batch', 'Quét Lô'),
        ('product', 'Quét Sản phẩm'),
        ('location', 'Quét Vị trí'),
    ], string='Chế độ Quét / Scan Mode', default='none')

    scan_detail_level = fields.Selection([
        ('batch_only', 'Chỉ quét Lô '),
        ('batch_plus_products', 'Quét Lô + Sản phẩm'),
        ('full_item', 'Quét Chi tiết từng Kiện'),
    ], string='Mức độ Quét', default='batch_only',
        help="Kiểm soát mức độ chi tiết khi quét:\n"
             "• Chỉ quét Lô: Chỉ quét mã vạch lô hàng/pallet (nhanh nhất, dùng cho hàng đồng nhất)\n"
             "• Quét Lô + Sản phẩm: Quét mã lô + xác nhận từng loại sản phẩm (kiểm soát vừa phải)\n"
             "• Quét Chi tiết từng Kiện: Quét từng kiện với serial/lot riêng (kiểm soát cao nhất, dùng cho hàng có số lô/serial)")

    production_handover_signed_by = fields.Many2one(
        'res.users',
        string='Người Bàn giao',
        help="Người ký xác nhận bàn giao từ sản xuất sang kho"
    )
    production_handover_signature = fields.Binary(
        string='Chữ ký Bàn giao',
        help="Chữ ký điện tử hoặc ảnh chụp chứng từ bàn giao đã ký"
    )
    production_handover_date = fields.Datetime(
        string='Thời gian Bàn giao',
        help="Thời điểm sản xuất bàn giao hàng cho kho"
    )

    picking_list_ids = fields.One2many(
        'hdi.picking.list',
        'picking_id',
        string='Bảng kê lấy hàng',
        help="Danh sách bảng kê lấy hàng cho phiếu xuất này"
    )

    picking_list_count = fields.Integer(
        compute='_compute_picking_list_count',
        string='Số bảng kê',
    )

    picking_type_code = fields.Selection(
        related='picking_type_id.code',
        string='Loại phiếu',
        store=True,
    )

    outgoing_type = fields.Selection([
        ('sale', 'Xuất bán hàng'),
        ('transfer', 'Chuyển kho thành phẩm khác'),
        ('production', 'Chuyển về kho sản xuất'),
    ], string='Loại xuất kho',
        compute='_compute_outgoing_type',
        store=True,
        readonly=False,
        tracking=True,
        help="Phân loại theo mục đích xuất kho")

    destination_warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Kho đích',
        help="Kho thành phẩm đích (nếu chuyển kho)"
    )

    receiving_type = fields.Selection([
        ('production_export', 'Sản xuất hàng trong nước'),
        ('production_export_high_value', 'Sản xuất hàng xuất khẩu'),
        ('import', ' Nhập khẩu'),
        ('transfer_return', 'Chuyển kho - Hàng trả lại'),
    ], string='Loại nhập kho',
        tracking=True,
        help="Phân loại loại nhập kho theo quy trình")

    require_batch_qc = fields.Boolean(
        string='Yêu cầu QC Batch',
        compute='_compute_qc_requirements',
        store=True,
        help="Tự động bật cho NK_NV_02, 03, 04"
    )

    require_product_qc = fields.Boolean(
        string='Yêu cầu QC Hàng',
        compute='_compute_qc_requirements',
        store=True,
        help="Tự động bật cho NK_NV_03, 04"
    )

    require_return_check = fields.Boolean(
        string='Yêu cầu kiểm tra hàng trả',
        compute='_compute_qc_requirements',
        store=True,
        help="Tự động bật cho NK_NV_04"
    )

    require_officer_approval = fields.Boolean(
        string='Yêu cầu ký xác nhận',
        compute='_compute_qc_requirements',
        store=True,
        help="Tự động bật cho NK_NV_02, 03, 04"
    )

    # QC Status fields
    batch_qc_status = fields.Selection([
        ('pending', 'Chờ kiểm tra'),
        ('in_progress', 'Đang kiểm tra'),
        ('passed', 'Đạt'),
        ('failed', 'Không đạt'),
    ], string='Trạng thái QC Batch', default='pending', tracking=True)

    product_qc_status = fields.Selection([
        ('pending', 'Chờ kiểm tra'),
        ('in_progress', 'Đang kiểm tra'),
        ('passed', 'Đạt'),
        ('failed', 'Không đạt'),
        ('partial', 'Đạt một phần'),
    ], string='Trạng thái QC Hàng', default='pending', tracking=True)

    return_reason = fields.Selection([
        ('defect', 'Lỗi sản phẩm'),
        ('wrong_item', 'Sai hàng'),
        ('excess', 'Thừa hàng'),
        ('customer_return', 'Khách hàng trả'),
        ('other', 'Khác'),
    ], string='Lý do trả hàng')

    return_condition = fields.Selection([
        ('new', 'Mới '),
        ('good', 'Tốt'),
        ('damaged', 'Hư hỏng '),
        ('scrap', 'Hỏng hoàn toàn - Thanh lý'),
    ], string='Tình trạng hàng trả')

    can_restock = fields.Boolean(string='Có thể nhập kho lại', default=True)

    # Approval fields (NK_NV_02, 03, 04)
    warehouse_officer_id = fields.Many2one(
        'res.users',
        string='Nhân viên kho ký',
        help="Nhân viên kho ký xác nhận"
    )

    officer_signature = fields.Binary(
        string='Chữ ký xác nhận',
        help="Chữ ký điện tử xác nhận"
    )

    approval_date = fields.Datetime(
        string='Ngày ký',
        readonly=True,
        help="Thời điểm ký xác nhận"
    )

    odoo_receipt_number = fields.Char(
        string='Số phiếu mã Odoo',
        readonly=True,
        help="Mã phiếu được tạo tự động"
    )

    @api.depends('receiving_type', 'picking_type_code')
    def _compute_qc_requirements(self):
        for picking in self:
            if picking.picking_type_code != 'incoming':
                picking.require_batch_qc = False
                picking.require_product_qc = False
                picking.require_return_check = False
                picking.require_officer_approval = False
                continue

            rec_type = picking.receiving_type

            # NK_NV_02, 03, 04 cần QC Batch
            picking.require_batch_qc = rec_type in ['production_export_high_value', 'import', 'transfer_return']

            # NK_NV_03, 04 cần QC Hàng
            picking.require_product_qc = rec_type in ['import', 'transfer_return']

            # NK_NV_04 cần kiểm tra hàng trả
            picking.require_return_check = rec_type == 'transfer_return'

            # NK_NV_02, 03, 04 cần ký xác nhận
            picking.require_officer_approval = rec_type in ['production_export_high_value', 'import', 'transfer_return']

    @api.depends('picking_type_id', 'picking_type_id.code')
    def _compute_require_putaway(self):
        """Auto-enable putaway for incoming pickings"""
        for picking in self:
            picking.require_putaway_suggestion = (
                    picking.picking_type_id.code == 'incoming'
            )

    @api.depends('location_dest_id', 'location_dest_id.usage', 'location_dest_id.warehouse_id', 'picking_type_code')
    def _compute_outgoing_type(self):
        for picking in self:
            if picking.picking_type_code != 'outgoing':
                picking.outgoing_type = False
                continue

            dest_location = picking.location_dest_id
            if not dest_location:
                picking.outgoing_type = 'other'
                continue

            # Xuất bán hàng: customer location
            if dest_location.usage == 'customer':
                picking.outgoing_type = 'sale'
            # Chuyển kho: internal location của warehouse khác
            elif dest_location.usage == 'internal' and dest_location.warehouse_id != picking.location_id.warehouse_id:
                picking.outgoing_type = 'transfer'
                picking.destination_warehouse_id = dest_location.warehouse_id
            # Chuyển về sản xuất: production location
            elif dest_location.usage == 'production':
                picking.outgoing_type = 'production'
            else:
                picking.outgoing_type = 'other'

    @api.depends('batch_ids')
    def _compute_batch_count(self):
        for picking in self:
            picking.batch_count = len(picking.batch_ids)

    @api.depends('picking_list_ids')
    def _compute_picking_list_count(self):
        """Count picking lists"""
        for picking in self:
            picking.picking_list_count = len(picking.picking_list_ids)

    def action_create_batch(self):
        self.ensure_one()
        return {
            'name': _('Create Batch'),
            'type': 'ir.actions.act_window',
            'res_model': 'hdi.batch.creation.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_picking_id': self.id,
                'default_location_id': self.location_dest_id.id,
            }
        }

    def action_suggest_putaway_all(self):
        self.ensure_one()
        if not self.batch_ids:
            raise UserError(_('No batches found in this picking.'))

        return {
            'name': _('Suggest Putaway for All Batches'),
            'type': 'ir.actions.act_window',
            'res_model': 'hdi.putaway.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_picking_id': self.id,
                'default_batch_ids': [(6, 0, self.batch_ids.ids)],
            }
        }

    # ===== QC & APPROVAL ACTIONS =====
    def action_start_batch_qc(self):
        self.ensure_one()
        self.batch_qc_status = 'in_progress'
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('QC Batch'),
                'message': _('Bắt đầu kiểm tra chất lượng batch'),
                'type': 'info',
            }
        }

    def action_pass_batch_qc(self):
        """QC Batch đạt"""
        self.ensure_one()
        self.batch_qc_status = 'passed'
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('QC Batch Đạt'),
                'message': _('Batch đã qua kiểm tra chất lượng'),
                'type': 'success',
            }
        }

    def action_start_product_qc(self):
        self.ensure_one()
        self.product_qc_status = 'in_progress'
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('QC Hàng'),
                'message': _('Bắt đầu kiểm tra chất lượng sản phẩm'),
                'type': 'info',
            }
        }

    def action_pass_product_qc(self):
        self.ensure_one()
        self.product_qc_status = 'passed'
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('QC Hàng Đạt'),
                'message': _('Sản phẩm đã qua kiểm tra chất lượng'),
                'type': 'success',
            }
        }

    def action_approve_receiving(self):
        self.ensure_one()
        if not self.warehouse_officer_id:
            self.warehouse_officer_id = self.env.user
        self.approval_date = fields.Datetime.now()

        # Generate Odoo receipt number
        if not self.odoo_receipt_number:
            self.odoo_receipt_number = self.env['ir.sequence'].next_by_code('hdi.wms.receipt') or self.name

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Đã ký xác nhận'),
                'message': _('Phiếu nhập kho đã được ký bởi %s') % self.warehouse_officer_id.name,
                'type': 'success',
            }
        }

    def action_suggest_picking(self):
        self.ensure_one()
        if self.picking_type_id.code != 'outgoing':
            raise UserError(_('Chỉ áp dụng cho phiếu xuất kho.'))

        # Tìm form view của wizard
        view_id = self.env.ref('hdi_wms.view_picking_suggestion_wizard_form').id

        return {
            'name': _('Gợi ý lấy hàng theo FIFO'),
            'type': 'ir.actions.act_window',
            'res_model': 'hdi.picking.suggestion.wizard',
            'view_mode': 'form',
            'views': [(view_id, 'form')],
            'target': 'new',
            'context': {
                'default_picking_id': self.id,
            }
        }

    def action_view_picking_lists(self):
        """Xem tất cả bảng kê lấy hàng"""
        self.ensure_one()
        return {
            'name': _('Bảng kê lấy hàng - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'hdi.picking.list',
            'view_mode': 'kanban,tree,form',
            'domain': [('picking_id', '=', self.id)],
            'context': {
                'default_picking_id': self.id,
            }
        }

    def action_open_scanner(self):
        self.ensure_one()
        return {
            'name': _('Scanner - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'res_id': self.id,
            'view_mode': 'form',
            'views': [(self.env.ref('hdi_wms.view_picking_form_scanner').id, 'form')],
            'target': 'fullscreen',
        }

    def action_view_batches(self):
        self.ensure_one()
        return {
            'name': _('Batches - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'hdi.batch',
            'view_mode': 'list,form,kanban',
            'domain': [('picking_id', '=', self.id)],
            'context': {
                'default_picking_id': self.id,
                'default_location_id': self.location_dest_id.id,
            }
        }

    def button_validate(self):

        for picking in self:
            if picking.use_batch_management and picking.require_putaway_suggestion:
                pending_batches = picking.batch_ids.filtered(
                    lambda b: b.state not in ['stored', 'shipped', 'cancel']
                )
                if pending_batches:
                    raise UserError(_(
                        'Cannot validate picking: %d batches are not yet stored.\n'
                        'Please complete putaway for all batches first.'
                    ) % len(pending_batches))

        result = super().button_validate()

        for picking in self:
            if picking.use_batch_management and picking.state == 'done':
                picking.wms_state = 'wms_done'

        return result

    def action_assign(self):
        result = super().action_assign()

        for picking in self:
            if picking.use_batch_management and picking.state == 'assigned':
                picking.wms_state = 'picking_ready'

        return result

    def action_confirm_handover(self):
        self.ensure_one()
        self.production_handover_signed_by = self.env.user
        self.production_handover_date = fields.Datetime.now()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Handover Confirmed'),
                'message': _('Handover signed by %s') % self.env.user.name,
                'type': 'success',
                'sticky': False,
            }
        }

    def on_barcode_scanned(self, barcode):
        self.ensure_one()
        self.last_scanned_barcode = barcode

        if self.scan_mode == 'batch':
            # Find batch by barcode
            batch = self.env['hdi.batch'].search([
                ('barcode', '=', barcode),
                ('picking_id', '=', self.id),
            ], limit=1)
            if batch:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Batch Found'),
                        'message': _('Batch %s scanned') % batch.name,
                        'type': 'success',
                        'sticky': False,
                    }
                }

        elif self.scan_mode == 'product':
            product = self.env['product.product'].search([
                ('barcode', '=', barcode),
            ], limit=1)
            if product:
                move_line = self.move_line_ids.filtered(
                    lambda ml: ml.product_id == product
                )
                if move_line:
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'title': _('Product Found'),
                            'message': _('Product %s scanned') % product.name,
                            'type': 'success',
                            'sticky': False,
                        }
                    }

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Not Found'),
                'message': _('Barcode %s not recognized') % barcode,
                'type': 'warning',
                'sticky': False,
            }
        }

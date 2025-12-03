from odoo import models, fields, api


class ShippingOrderSearch(models.TransientModel):
    _name = 'shipping.order.search'
    _description = 'Tìm kiếm Phiếu Gửi Hàng'

    search_code = fields.Char(
        string='Mã phiếu gửi',
        placeholder='Nhập mã phiếu gửi hàng'
    )

    order_id = fields.Many2one(
        'shipping.order',
        string='Phiếu gửi hàng',
        readonly=True
    )

    has_results = fields.Boolean(
        string='Có kết quả',
        compute='_compute_has_results',
        store=False
    )

    @api.depends('order_id')
    def _compute_has_results(self):
        """Check if search found results"""
        for record in self:
            record.has_results = bool(record.order_id)

    # Display fields
    order_code = fields.Char(
        string='Số phiếu',
        related='order_id.code',
        readonly=True
    )
    
    sender_name = fields.Char(
        string='Người gửi',
        related='order_id.sender_name',
        readonly=True
    )
    
    receiver_name = fields.Char(
        string='Người nhận',
        related='order_id.receiver_name',
        readonly=True
    )
    
    receiver_phone = fields.Char(
        string='Số điện thoại',
        related='order_id.receiver_phone',
        readonly=True
    )
    
    receiver_address = fields.Char(
        string='Địa chỉ',
        compute='_compute_receiver_address',
        readonly=True
    )
    
    goods_description = fields.Text(
        string='Nội dung hàng',
        related='order_id.goods_description',
        readonly=True
    )
    
    total_shipping_fee = fields.Integer(
        string='Tổng cước (VND)',
        related='order_id.total_shipping_fee',
        readonly=True
    )
    
    payment_status = fields.Selection(
        [
            ('unpaid', 'Chưa trả tiền'),
            ('waiting_payment', 'Chờ trả tiền'),
            ('paid', 'Đã trả tiền'),
            ('cancelled', 'Hủy thanh toán'),
        ],
        string='Trạng thái thanh toán',
        related='order_id.payment_status',
        readonly=True
    )
    
    state = fields.Selection(
        [
            ('draft', 'Đơn nháp'),
            ('waiting_pickup', 'Chờ lấy hàng'),
            ('in_transit', 'Đang vận chuyển'),
            ('forwarded', 'Phát tiếp'),
            ('delivered', 'Phát thành công'),
            ('return_approved', 'Duyệt hoàn'),
            ('return_completed', 'Hoàn thành công'),
            ('cancelled', 'Đã hủy')
        ],
        string='Trạng thái đơn hàng',
        related='order_id.state',
        readonly=True
    )
    
    paid_amount = fields.Integer(
        string='Đã trả (VND)',
        related='order_id.paid_amount',
        readonly=True
    )
    
    payment_date = fields.Date(
        string='Ngày thanh toán',
        related='order_id.payment_date',
        readonly=True
    )

    @api.depends('order_id.receiver_house_number', 'order_id.receiver_street',
                 'order_id.receiver_ward', 'order_id.receiver_district',
                 'order_id.receiver_city')
    def _compute_receiver_address(self):
        """Compute full address from components"""
        for record in self:
            if record.order_id:
                parts = [
                    record.order_id.receiver_house_number,
                    record.order_id.receiver_street,
                    record.order_id.receiver_ward,
                    record.order_id.receiver_district,
                    record.order_id.receiver_city,
                ]
                record.receiver_address = ', '.join([p for p in parts if p])
            else:
                record.receiver_address = ''

    def action_search(self):
        """Search for shipping order by code"""
        self.ensure_one()
        
        if not self.search_code or not self.search_code.strip():
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Lỗi',
                    'message': 'Vui lòng nhập mã phiếu gửi hàng',
                    'type': 'danger',
                }
            }
        
        # Search for order by code
        order = self.env['shipping.order'].search(
            [('code', '=', self.search_code.strip())],
            limit=1
        )
        
        if not order:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Không tìm thấy',
                    'message': f'Phiếu gửi hàng với mã "{self.search_code}" không tồn tại',
                    'type': 'warning',
                }
            }
        
        # Set the found order
        self.order_id = order.id
        
        # Reload the form to show results
        return {
            'type': 'ir.actions.client',
            'tag': 'reload'
        }

    def action_view_order(self):
        """Open the found order in detail view"""
        self.ensure_one()
        
        if not self.order_id:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Lỗi',
                    'message': 'Chưa tìm thấy phiếu gửi hàng',
                    'type': 'danger',
                }
            }
        
        return {
            'name': f'Phiếu gửi hàng {self.order_id.code}',
            'type': 'ir.actions.act_window',
            'res_model': 'shipping.order',
            'res_id': self.order_id.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'current',
        }

    def action_clear(self):
        """Clear search results"""
        self.search_code = ''
        self.order_id = False
        return {
            'type': 'ir.actions.client',
            'tag': 'reload'
        }

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
        string='Tên người gửi',
        related='order_id.sender_name',
        readonly=True
    )
    
    sender_phone = fields.Char(
        string='Số điện thoại người gửi',
        related='order_id.sender_phone',
        readonly=True
    )

    sender_address = fields.Char(
        string='Địa chỉ người gửi',
        related='order_id.sender_address',
        readonly=True
    )

    receiver_name = fields.Char(
        string='Tên người nhận',
        related='order_id.receiver_name',
        readonly=True
    )
    
    receiver_phone = fields.Char(
        string='Số điện thoại người nhận',
        related='order_id.receiver_phone',
        readonly=True
    )
    
    receiver_address = fields.Char(
        string='Địa  người nhận',
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
        
        # Return the form with results
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'shipping.order.search',
            'res_id': self.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'current',
        }

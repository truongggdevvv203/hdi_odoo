from odoo import models, fields, api
from datetime import datetime


class ShippingOrder(models.Model):
    _name = 'shipping.order'
    _description = 'Shipping Order'
    _rec_name = 'order_number'

    # Order information
    order_number = fields.Char(string='Mã đơn hàng', readonly=True, copy=False)
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('submitted', 'Đã gửi'),
        ('in_transit', 'Đang vận chuyển'),
        ('delivered', 'Đã giao'),
        ('cancelled', 'Hủy'),
    ], string='Trạng thái', default='draft', tracking=True)
    
    created_date = fields.Datetime(string='Ngày tạo', readonly=True, default=fields.Datetime.now)
    user_id = fields.Many2one('res.users', string='Người tạo', readonly=True, default=lambda self: self.env.user)

    # Sender information
    sender_address_id = fields.Many2one('sender.address', string='Địa chỉ gửi', required=True)
    sender_name = fields.Char(string='Tên người gửi', related='sender_address_id.name', readonly=True)
    sender_phone = fields.Char(string='Điện thoại người gửi', related='sender_address_id.phone', readonly=True)

    # Receiver information
    receiver_name = fields.Char(string='Tên người nhận', required=True)
    receiver_phone = fields.Char(string='Điện thoại người nhận', required=True)
    receiver_street = fields.Char(string='Đường')
    receiver_city = fields.Char(string='Thành phố', required=True)
    receiver_state = fields.Char(string='Tỉnh/Thành')
    receiver_zip = fields.Char(string='Mã bưu điện')
    
    # Time slot for delivery
    time_slot = fields.Selection([
        ('morning', '6h - 12h'),
        ('afternoon', '12h - 18h'),
        ('evening', '18h - 21h'),
        ('anytime', 'Cả ngày'),
    ], string='Khung giờ nhận hàng', default='anytime')
    
    # Shipment items (one2many)
    shipment_item_ids = fields.One2many('shipment.item', 'order_id', string='Hàng hóa')
    
    # Shipment details
    total_weight = fields.Float(string='Tổng trọng lượng (kg)', compute='_compute_totals')
    total_value = fields.Float(string='Giá trị hàng hóa (VND)', compute='_compute_totals')
    item_count = fields.Integer(string='Số lượng loại hàng', compute='_compute_totals')
    
    allow_view = fields.Boolean(string='Cho phép khách xem hàng', default=True)
    reference_code = fields.Char(string='Mã tham chiếu')
    note = fields.Text(string='Ghi chú hàng hóa')
    
    # Shipping service
    shipping_service_id = fields.Many2one('shipping.service', string='Dịch vụ vận chuyển', required=True)
    shipping_cost = fields.Float(string='Cước phí (VND)', compute='_compute_shipping_cost')
    
    # Fee and payment
    is_receiver_pay = fields.Boolean(string='Người nhận trả cước', default=False)
    cod_amount = fields.Float(string='Tiền thu hộ (COD)')
    total_fee = fields.Float(string='Tổng cước phí (VND)', compute='_compute_total_fee')
    
    pickup_at_office = fields.Boolean(string='Tới văn phòng gửi', default=False)
    order_notes = fields.Text(string='Ghi chú đơn hàng')

    @api.model_create_multi
    def create(self, vals_list):
        """Auto-generate order number"""
        for vals in vals_list:
            if not vals.get('order_number'):
                vals['order_number'] = self.env['ir.sequence'].next_by_code('shipping.order') or 'NEW'
        return super().create(vals_list)

    @api.depends('shipment_item_ids')
    def _compute_totals(self):
        for order in self:
            order.total_weight = sum(item.weight for item in order.shipment_item_ids)
            order.total_value = sum(item.value for item in order.shipment_item_ids)
            order.item_count = len(order.shipment_item_ids)

    @api.depends('shipping_service_id', 'total_weight')
    def _compute_shipping_cost(self):
        for order in self:
            if order.shipping_service_id:
                # Simple calculation: base price + weight surcharge (example: 5k per kg)
                weight_surcharge = order.total_weight * 5000 if order.total_weight > 0 else 0
                order.shipping_cost = order.shipping_service_id.base_price + weight_surcharge
            else:
                order.shipping_cost = 0

    @api.depends('shipping_cost', 'cod_amount', 'is_receiver_pay')
    def _compute_total_fee(self):
        for order in self:
            fee = order.shipping_cost
            if order.is_receiver_pay:
                # If receiver pays, add any additional surcharge (e.g., collection fee)
                fee += order.cod_amount * 0.01 if order.cod_amount > 0 else 0  # 1% collection fee
            order.total_fee = fee

    def action_submit(self):
        """Submit order to shipping system"""
        self.write({'state': 'submitted'})

    def action_cancel(self):
        """Cancel shipping order"""
        self.write({'state': 'cancelled'})

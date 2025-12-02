from odoo import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    is_shipping_order = fields.Boolean(string='Là phiếu gửi hàng',
                                       default=False)

    # 3.1 Thông tin người gửi
    sender_name = fields.Char(string='Tên người gửi')
    sender_phone = fields.Char(string='Điện thoại người gửi')
    sender_street = fields.Char(string='Địa chỉ gửi')

    # 3.2 Thông tin người nhận
    receiver_name = fields.Char(string='Tên người nhận')
    receiver_phone = fields.Char(string='Điện thoại người nhận')
    receiver_street = fields.Char(string='Địa chỉ người nhận')
    receiver_city = fields.Char(string='Thành phố')
    receiver_state = fields.Char(string='Tỉnh/Thành')

    # Khung giờ nhận hàng
    delivery_time_slot = fields.Selection([
        ('morning', '6h - 12h'),
        ('afternoon', '12h - 18h'),
        ('evening', '18h - 21h'),
        ('anytime', 'Cả ngày'),
    ], string='Khung giờ nhận hàng', default='anytime')

    # 3.3 Thông tin hàng hóa
    allow_view_goods = fields.Boolean(string='Cho phép khách xem hàng',
                                      default=True)
    reference_code = fields.Char(string='Mã tham chiếu')
    goods_value = fields.Float(string='Giá trị hàng hóa (VND)')
    goods_description = fields.Text(string='Mô tả hàng hóa')

    # 3.4 Dịch vụ vận chuyển
    shipping_service_id = fields.Many2one('shipping.service',
                                          string='Dịch vụ vận chuyển')
    base_shipping_cost = fields.Float(string='Cước phí cơ bản (VND)',
                                      compute='_compute_base_shipping_cost',
                                      store=True)

    # 3.5 Thông tin cước phí
    receiver_pay_fee = fields.Boolean(string='Người nhận trả cước',
                                      default=False)
    cod_amount = fields.Float(string='Tiền thu hộ (COD)')
    pickup_at_office = fields.Boolean(string='Tới văn phòng gửi',
                                      default=False)
    shipping_notes = fields.Text(string='Ghi chú đơn hàng')

    # Tính toán tổng cước phí
    total_shipping_fee = fields.Float(string='Tổng cước phí (VND)',
                                      compute='_compute_total_shipping_fee',
                                      store=True)

    @api.depends('shipping_service_id')
    def _compute_base_shipping_cost(self):
        for order in self:
            if order.shipping_service_id:
                order.base_shipping_cost = order.shipping_service_id.base_price
            else:
                order.base_shipping_cost = 0

    @api.depends('base_shipping_cost', 'cod_amount', 'receiver_pay_fee')
    def _compute_total_shipping_fee(self):
        for order in self:
            fee = order.base_shipping_cost or 0
            if order.receiver_pay_fee and order.cod_amount > 0:
                fee += order.cod_amount * 0.01  # Thêm phí thu hộ 1%
            order.total_shipping_fee = fee

    def action_submit_shipping(self):
        """Submit as shipping order"""
        self.write({
            'is_shipping_order': True,
            'state': 'sent'
        })
        return {'type': 'ir.actions.client', 'tag': 'reload'}
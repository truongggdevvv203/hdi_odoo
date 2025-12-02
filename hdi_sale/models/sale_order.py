from odoo import models, fields, api


class SaleOrder(models.Model):
  _inherit = 'sale.order'

  is_shipping_order = fields.Boolean(string='Là phiếu gửi hàng',
                                     default=False)

  # 3.1 Thông tin người gửi
  sender_name = fields.Char(string='Tên người gửi')
  sender_phone = fields.Char(string='Điện thoại người gửi')
  sender_street = fields.Char(string='Địa chỉ gửi')

  # 3.2. Thông tin người nhận
  receiver_name = fields.Char(string="Họ tên người nhận", required=True)
  receiver_phone = fields.Char(string="Số điện thoại người nhận",
                               required=True)

  # Địa chỉ chi tiết
  receiver_city = fields.Char(string="Tỉnh/Thành phố", required=True)
  receiver_district = fields.Char(string="Quận/Huyện", required=True)
  receiver_ward = fields.Char(string="Phường/Xã", required=True)

  receiver_house_number = fields.Char(string="Số nhà", required=True)
  receiver_street = fields.Char(string="Tên đường", required=True)

  # Khung giờ nhận hàng
  delivery_time_slot = fields.Selection([
    ('morning', '6h - 12h'),
    ('afternoon', '12h - 18h'),
    ('evening', '18h - 21h'),
    ('anytime', 'Cả ngày'),
  ], string='Khung giờ nhận hàng', default='anytime')

  # 3.3 Thông tin hàng hóa
  allow_view_goods = fields.Boolean(
      string='Cho xem hàng khi nhận',
      default=True
  )

  reference_code = fields.Char(string='Mã tham chiếu')
  goods_value = fields.Integer(string='Giá trị hàng hóa (VND)')
  goods_description = fields.Text(string='Nội dung')

  quantity = fields.Integer(string='Số lượng', default=1)

  weight = fields.Integer(string='Trọng lượng (g)')
  length = fields.Integer(string='Chiều dài')
  width = fields.Integer(string='Chiều rộng')
  height = fields.Integer(string='Chiều cao')
  convert_weight = fields.Integer(
      string='Trọng lượng quy đổi')

  # 3.4 Dịch vụ vận chuyển
  shipping_service_id = fields.Many2one('shipping.service',
                                        string='Dịch vụ vận chuyển',
                                        domain=[('service_type', '=', 'main')],
                                        required=True)

  base_shipping_cost = fields.Integer(string='Cước phí (VND)',
                                      compute='_compute_base_shipping_cost',
                                      store=True)

  # Dịch vụ cộng thêm
  goods_type = fields.Selection([
    ('document', 'Thư từ'),
    ('parcel', 'Hàng hóa thường'),
  ], string='Loại bưu phẩm', default='parcel')
  additional_service_ids = fields.Many2many('shipping.service',
                                            'sale_order_additional_service',
                                            'order_id', 'service_id',
                                            string='Dịch vụ cộng thêm',
                                            domain=[('service_type', '=',
                                                     'additional')])
  additional_cost = fields.Integer(string='Phí dịch vụ cộng thêm (VND)',
                                   compute='_compute_additional_cost',
                                   store=True)

  # 3.5 Thông tin cước phí
  receiver_pay_fee = fields.Boolean(string='Người nhận trả cước',
                                    default=False)
  cod_amount = fields.Integer(string='Tiền thu hộ (COD)')
  pickup_at_office = fields.Boolean(string='Đến phòng giao dịch gửi',
                                    default=False)
  shipping_notes = fields.Text(string='Ghi chú nhận hàng')

  # Tính toán tổng cước phí
  total_shipping_fee = fields.Integer(string='Tổng cước',
                                      compute='_compute_total_shipping_fee',
                                      store=True)

  @api.depends('sender_name', 'receiver_city', 'goods_type')
  def _compute_suggested_services(self):
    """Suggest main shipping services based on sender/receiver info"""
    for order in self:
      if order.sender_name and order.receiver_city:
        # Get all active main shipping services only
        suggested = self.env['shipping.service'].search([
          ('active', '=', True),
          ('service_type', '=', 'main')
        ])
        # Return up to 3 suggested services
        order.suggested_service_ids = suggested[:3] if suggested else False
      else:
        order.suggested_service_ids = False

  @api.depends('additional_service_ids')
  def _compute_additional_cost(self):
    """Calculate additional fees from selected additional services"""
    for order in self:
      # base_price is integer (VND), sum will be integer
      order.additional_cost = int(
        sum(order.additional_service_ids.mapped('base_price') or [0]))

  @api.depends('shipping_service_id')
  def _compute_base_shipping_cost(self):
    """Compute base shipping cost from the selected main shipping service"""
    for order in self:
      order.base_shipping_cost = int(
        order.shipping_service_id.base_price) if order.shipping_service_id else 0

  @api.depends('base_shipping_cost', 'cod_amount', 'receiver_pay_fee',
               'additional_cost')
  def _compute_total_shipping_fee(self):
    """Calculate total fee = base shipping + additional services"""
    for order in self:
      fee = (int(order.base_shipping_cost or 0)) + (
        int(order.additional_cost or 0))
      order.total_shipping_fee = int(fee)

  def action_submit_shipping(self):
    """Submit as shipping order"""
    self.write({
      'is_shipping_order': True,
      'state': 'sent'
    })
    return {'type': 'ir.actions.client', 'tag': 'reload'}

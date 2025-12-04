from odoo import models, fields, api
import json


class ShippingOrder(models.Model):
  _name = 'shipping.order'
  _description = 'Phiếu Gửi Hàng'

  code = fields.Char(string='Số phiếu', readonly=True, copy=False,
                     default=lambda self: self.env['ir.sequence'].next_by_code(
                       'shipping.order'))

  state = fields.Selection([
    ('draft', 'Đơn nháp'),
    ('waiting_pickup', 'Chờ lấy hàng'),
    ('in_transit', 'Đang vận chuyển'),
    ('forwarded', 'Phát tiếp'),
    ('delivered', 'Phát thành công'),
    ('return_approved', 'Duyệt hoàn'),
    ('return_completed', 'Hoàn thành công'),
    ('cancelled', 'Đã hủy')
  ], string='Trạng thái', default='draft', readonly=True)

  is_shipping_order = fields.Boolean(string='Là phiếu gửi hàng', default=True)

  # 3.1 Thông tin người gửi
  sender_id = fields.Many2one(
      comodel_name='res.users',
      string='Người gửi',
      default=lambda self: self.env.user
  )

  sender_name = fields.Char(
      string='Tên người gửi',
      related='sender_id.name',
      store=True,
      readonly=True
  )

  sender_config_id = fields.Many2one(
      'sender.config',
      string='Địa điểm gửi',
      help='Chọn địa điểm gửi hàng từ cấu hình'
  )

  # Sử dụng full_address từ sender.config
  sender_address = fields.Char(
      string='Địa chỉ gửi',
      related='sender_config_id.full_address',
      readonly=True
  )

  sender_phone = fields.Char(
      string='Số điện thoại',
      related='sender_config_id.phone',
      readonly=True
  )

  sender_email = fields.Char(
      string='Email',
      related='sender_config_id.email',
      readonly=True
  )

  # 3.2. Thông tin người nhận
  receiver_name = fields.Char(string="Họ tên người nhận", required=True)
  receiver_phone = fields.Char(string="Số điện thoại người nhận", required=True)

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
      string='Cho xem hàng khi nhận',
      default=True
  )

  reference_code = fields.Char(string='Mã tham chiếu')
  goods_value = fields.Integer(string='Giá trị hàng hóa (VND)')
  goods_description = fields.Text(string='Nội dung')

  quantity = fields.Integer(string='Số lượng', default=1)

  weight = fields.Integer(string='Trọng lượng (g)')
  length = fields.Integer(string='Chiều dài')
  width = fields.Integer(string='Chiều rộng')
  height = fields.Integer(string='Chiều cao')
  convert_weight = fields.Integer(string='Trọng lượng quy đổi')

  # 3.4 Dịch vụ vận chuyển
  shipping_service_id = fields.Many2one('shipping.service',
                                        string='Dịch vụ vận chuyển',
                                        domain=[('service_type', '=', 'main')],
                                        required=True)

  base_shipping_cost = fields.Integer(string='Cước phí (VND)',
                                      compute='_compute_base_shipping_cost',
                                      store=True)

  shipping_service_estimated_time = fields.Char(
      string='Thời gian dự kiến',
      compute='_compute_shipping_service_estimated_time',
      readonly=True
  )

  # Dịch vụ cộng thêm
  goods_type = fields.Selection([
    ('document', 'Thư từ'),
    ('parcel', 'Hàng hóa thường'),
  ], string='Loại bưu phẩm', default='parcel')

  additional_service_ids = fields.Many2many('shipping.service',
                                            'shipping_order_additional_service',
                                            'order_id', 'service_id',
                                            string='Dịch vụ cộng thêm',
                                            domain=[('service_type', '=',
                                                     'additional')])

  additional_cost = fields.Integer(string='Phí dịch vụ cộng thêm (VND)',
                                   compute='_compute_additional_cost',
                                   store=True)

  # 3.5 Thông tin cước phí
  receiver_pay_fee = fields.Boolean(string='Người nhận trả cước', default=False)
  cod_amount = fields.Integer(string='Tiền thu hộ (COD)')
  pickup_at_office = fields.Boolean(string='Đến phòng giao dịch gửi',
                                    default=False)
  sender_pay_fee = fields.Integer(string='Tiền trả người gửi',
                                  compute='_compute_sender_pay_fee', store=True)
  shipping_notes = fields.Text(string='Ghi chú nhận hàng')

  # Tính toán tổng cước phí
  total_shipping_fee = fields.Integer(string='Tổng cước',
                                      compute='_compute_total_shipping_fee',
                                      store=True)

  suggested_service_ids = fields.Many2many('shipping.service',
                                           'shipping_order_suggested_service',
                                           'order_id', 'service_id',
                                           string='Dịch vụ được gợi ý',
                                           compute='_compute_suggested_services',
                                           store=True)

  # 3.6 Thông tin thanh toán / Đối soát công nợ
  payment_status = fields.Selection([
    ('unpaid', 'Chưa trả tiền'),
    ('waiting_payment', 'Chờ trả tiền'),
    ('paid', 'Đã trả tiền'),
    ('cancelled', 'Hủy thanh toán'),
  ], string='Trạng thái thanh toán', default='unpaid',
      help='Trạng thái thanh toán của đơn hàng')

  payment_date = fields.Date(string='Ngày thanh toán', readonly=True,
                             help='Ngày thực hiện thanh toán')

  paid_amount = fields.Integer(string='Tiền đã trả (VND)', default=0,
                               readonly=True, help='Số tiền đã thanh toán')

  payment_deadline = fields.Date(string='Hạn thanh toán',
                                 help='Hạn chót thanh toán')

  payment_note = fields.Text(string='Ghi chú thanh toán',
                             help='Ghi chú liên quan đến thanh toán')

  invoice_code = fields.Char(string='Mã hóa đơn', readonly=True,
                             help='Mã hóa đơn liên quan (nếu có)')

  @api.depends('cod_amount', 'total_shipping_fee', 'receiver_pay_fee')
  def _compute_sender_pay_fee(self):
    for rec in self:
      if rec.receiver_pay_fee:
        # Nếu người nhận trả cước thì tiền người gửi = COD - tổng cước
        rec.sender_pay_fee = (rec.cod_amount or 0) - (
              rec.total_shipping_fee or 0)
      else:
        # Nếu không, giữ nguyên hoặc bằng 0
        rec.sender_pay_fee = 0

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

  @api.depends('shipping_service_id')
  def _compute_shipping_service_estimated_time(self):
    """Get estimated time from selected shipping service"""
    for order in self:
      order.shipping_service_estimated_time = order.shipping_service_id.estimated_time if order.shipping_service_id else ''

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
    old_state = self.state
    self.write({
      'state': 'waiting_pickup'
    })
    self._send_bus_notification('Đơn hàng đã được gửi đi', old_state,
                                'waiting_pickup')
    return {'type': 'ir.actions.client', 'tag': 'reload'}

  def action_cancel(self):
    """Cancel shipping order"""
    old_state = self.state
    self.write({
      'state': 'cancelled'
    })
    self._send_bus_notification('Đơn hàng đã bị hủy', old_state, 'cancelled')
    return {'type': 'ir.actions.client', 'tag': 'reload'}

  def _send_bus_notification(self, message, old_state=None, new_state=None):
    """Send bus notification to update dashboard in real-time"""
    if self.sender_id:
      # Send notification to the sender user
      notification_data = {
        'user_id': self.sender_id.id,
        'message': message,
        'order_code': self.code,
        'old_state': old_state,
        'new_state': new_state or self.state,
        'timestamp': fields.Datetime.now().isoformat()
      }

      self.env['bus.bus']._sendone(
          f'shipping_order_update_{self.sender_id.id}',
          'shipping_order_update',
          notification_data
      )

  @api.model_create_multi
  def create(self, vals_list):
    """Override create to send bus notification for new orders"""
    records = super().create(vals_list)
    for record in records:
      record._send_bus_notification('Đơn hàng mới được tạo', None, record.state)
    return records

  def write(self, vals):
    """Override write to send bus notification on state changes"""
    # Track state changes for each record
    state_changes = {}
    if 'state' in vals:
      for record in self:
        state_changes[record.id] = record.state

    result = super().write(vals)

    # Send notifications for state changes
    if 'state' in vals:
      new_state = vals['state']
      for record in self:
        if record.id in state_changes:
          old_state = state_changes[record.id]
          if old_state != new_state:
            state_names = dict(self._fields['state'].selection)
            message = f'Trạng thái đơn hàng thay đổi: {state_names.get(old_state, old_state)} → {state_names.get(new_state, new_state)}'
            record._send_bus_notification(message, old_state, new_state)

    return result
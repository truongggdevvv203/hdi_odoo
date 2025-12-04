from odoo import models, fields, api
from datetime import datetime, time


class ShippingOrderByPaymentStatus(models.TransientModel):
  _name = 'shipping.order.by.payment.status'
  _description = 'Tìm kiếm Phiếu Gửi Hàng theo Trạng thái thanh toán'

  date_from = fields.Date(
      string='Từ ngày',
      default=lambda self: fields.Date.today().replace(day=1),
      help='Ngày bắt đầu tạo đơn',
      required=True
  )

  date_to = fields.Date(
      string='Đến ngày',
      default=lambda self: fields.Date.context_today(self),
      help='Ngày kết thúc tạo đơn',
      required=True
  )

  payment_status = fields.Selection(
      [
        ('unpaid', 'Chưa trả tiền'),
        ('waiting_payment', 'Chờ trả tiền'),
        ('paid', 'Đã trả tiền'),
        ('cancelled', 'Hủy thanh toán'),
      ],
      string='Trạng thái thanh toán',
      help='Để trống để tìm tất cả trạng thái'
  )

  order_ids = fields.Many2many(
      'shipping.order',
      string='Danh sách kết quả',
      readonly=True
  )

  def _to_datetime_string(self, date_value, end_of_day=False):
    if not date_value:
      return False
    date_obj = fields.Date.from_string(date_value)
    if not date_obj:
      return False
    time_part = time.max if end_of_day else time.min
    return fields.Datetime.to_string(datetime.combine(date_obj, time_part))

  def _validate_date_range(self):
    if self.date_from and self.date_to:
      start = fields.Date.from_string(self.date_from)
      end = fields.Date.from_string(self.date_to)
      if start > end:
        return False, 'Ngày bắt đầu không được lớn hơn ngày kết thúc.'
    return True, ''

  def action_search(self):
    self.ensure_one()

    valid, message = self._validate_date_range()
    if not valid:
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Lỗi ngày',
                'message': message,
                'type': 'danger',
            }
        }

    domain = []
    start_dt = self._to_datetime_string(self.date_from)
    if start_dt:
        domain.append(('create_date', '>=', start_dt))
    end_dt = self._to_datetime_string(self.date_to, end_of_day=True)
    if end_dt:
        domain.append(('create_date', '<=', end_dt))

    domain.append(('payment_status', '=', 'unpaid'))

    orders = self.env['shipping.order'].search(domain,
                                               order='create_date desc')

    self.order_ids = orders

    if not orders:
        if self.payment_status:
            payment_label = dict(self._fields['payment_status'].selection).get(
                self.payment_status)
            message = f'Không có đơn nào với trạng thái "{payment_label}" trong khoảng thời gian đã chọn'
        else:
            message = f'Không có đơn nào trong khoảng thời gian đã chọn'

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Không tìm thấy',
                'message': message,
                'type': 'warning',
            }
        }

    return True
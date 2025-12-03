from odoo import models, fields, api
from datetime import datetime, timedelta


class ShippingOrderReconciliation(models.TransientModel):
  _name = 'shipping.order.reconciliation'
  _description = 'Đối soát Công nợ Phiếu Gửi Hàng'

  # Date range filters
  date_from = fields.Date(
      string='Từ ngày',
      default=lambda self: datetime.now().replace(day=1).date(),
      help='Ngày bắt đầu'
  )

  date_to = fields.Date(
      string='Đến ngày',
      default=lambda self: datetime.now().date(),
      help='Ngày kết thúc'
  )

  # Payment status filter
  payment_status = fields.Selection([
    ('paid', 'Đã trả tiền'),
    ('waiting_payment', 'Chờ trả tiền'),
    ('unpaid', 'Chưa trả tiền'),
  ], string='Trạng thái thanh toán', default='paid',
      help='Lọc theo trạng thái thanh toán')

  # Current user
  user_id = fields.Many2one(
      'res.users',
      string='Người dùng',
      default=lambda self: self.env.user,
      readonly=True,
      help='Người dùng hiện tại'
  )

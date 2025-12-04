from odoo import models, fields, api
from datetime import datetime, time


class ShippingOrderSearchByDate(models.TransientModel):
    """Search shipping orders by creation date range - returns list"""
    _name = 'shipping.order.search.by.date'
    _description = 'Tìm kiếm Phiếu Gửi Hàng theo Ngày Tạo'

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
        """Search for shipping orders by date range"""
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
        
        orders = self.env['shipping.order'].search(domain, order='create_date desc')
        if not orders:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Không tìm thấy',
                    'message': 'Không có đơn nào trong khoảng thời gian đã chọn',
                    'type': 'warning',
                }
            }
        
        self.order_ids = orders
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'shipping.order.search.by.date',
            'res_id': self.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'current',
        }

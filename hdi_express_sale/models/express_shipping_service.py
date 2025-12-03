from odoo import models, fields, api

class ShippingService(models.Model):
    _name = 'shipping.service'
    _description = 'Shipping Service'

    name = fields.Char(string='Tên dịch vụ', required=True)
    code = fields.Char(string='Mã dịch vụ', required=True, unique=True)
    service_type = fields.Selection([
        ('main', 'Dịch vụ vận chuyển'),
        ('additional', 'Dịch vụ cộng thêm'),
    ], string='Loại dịch vụ', default='main', required=True)
    base_price = fields.Integer(string='Giá (VND)', required=True)
    estimated_time = fields.Char(string="Thời gian dự kiến")
    description = fields.Text(string='Mô tả')
    active = fields.Boolean(string='Kích hoạt', default=True)

    # Boolean helper để form view sử dụng
    show_estimated_time = fields.Boolean(
        string="Hiển thị Thời gian dự kiến", compute="_compute_show_estimated_time"
    )

    @api.depends('service_type')
    def _compute_show_estimated_time(self):
        for rec in self:
            rec.show_estimated_time = rec.service_type == 'main'

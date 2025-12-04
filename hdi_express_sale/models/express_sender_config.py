from odoo import models, fields, api


class SenderConfig(models.Model):
    _name = 'sender.config'
    _description = 'Cấu hình Địa chỉ Gửi Hàng'
    _order = 'sequence, name'

    name = fields.Char(
        string='Tên địa điểm gửi',
        required=True,
        help='Tên dễ nhớ của địa điểm gửi hàng'
    )

    location_id = fields.Many2one(
        'stock.location',
        string='Vị trí kho hàng',
        required=True,
        domain=[('usage', '=', 'internal')],
        help='Chọn vị trí kho hàng từ stock.location'
    )

    # Địa chỉ riêng (có thể khác với kho)
    street = fields.Char(
        string='Đường/Phố',
        help='Địa chỉ gửi hàng chi tiết'
    )

    city = fields.Char(
        string='Tỉnh/Thành phố',
        help='Tỉnh thành phố'
    )

    state_id = fields.Many2one(
        'res.country.state',
        string='Tỉnh/Bang',
        help='Chọn tỉnh thành'
    )

    zip_code = fields.Char(
        string='Mã bưu điện',
        help='Mã bưu điện'
    )

    country_id = fields.Many2one(
        'res.country',
        string='Quốc gia',
        default=lambda self: self.env.ref('base.vn'),
        help='Quốc gia'
    )

    # Địa chỉ từ kho (read-only)
    warehouse_street = fields.Char(
        string='Đường/Phố (Kho)',
        related='location_id.street',
        readonly=True,
        help='Địa chỉ từ kho hàng'
    )

    warehouse_city = fields.Char(
        string='Tỉnh/Thành phố (Kho)',
        related='location_id.city',
        readonly=True
    )

    warehouse_state_id = fields.Many2one(
        'res.country.state',
        string='Tỉnh/Bang (Kho)',
        related='location_id.state_id',
        readonly=True
    )

    warehouse_zip_code = fields.Char(
        string='Mã bưu điện (Kho)',
        related='location_id.zip',
        readonly=True
    )

    warehouse_country_id = fields.Many2one(
        'res.country',
        string='Quốc gia (Kho)',
        related='location_id.country_id',
        readonly=True
    )

    phone = fields.Char(
        string='Số điện thoại',
        help='Số điện thoại liên hệ địa điểm gửi hàng'
    )

    email = fields.Char(
        string='Email',
        help='Email liên hệ'
    )

    contact_person = fields.Char(
        string='Người liên hệ',
        help='Tên người đại diện'
    )

    sequence = fields.Integer(
        string='Thứ tự',
        default=10,
        help='Thứ tự hiển thị'
    )

    is_default = fields.Boolean(
        string='Là mặc định',
        default=False,
        help='Đặt làm địa điểm gửi mặc định'
    )

    active = fields.Boolean(
        string='Hoạt động',
        default=True,
        help='Kích hoạt/Vô hiệu hóa địa điểm này'
    )

    company_id = fields.Many2one(
        'res.company',
        string='Công ty',
        default=lambda self: self.env.company,
        required=True
    )

    @api.model
    def get_default_sender(self):
        """Get default sender location"""
        default = self.search([('is_default', '=', True)], limit=1)
        return default if default else self.search([], limit=1)

    @api.model
    def get_sender_choices(self):
        """Get all active sender locations for selection"""
        return self.search([('active', '=', True)], order='sequence')

from odoo import models, fields, api


class SenderConfig(models.Model):
    _name = 'sender.config'
    _description = 'Cấu hình Địa chỉ Gửi Hàng'
    _order = 'sequence, name'

    name = fields.Char(
        string='Tên kho hàng',
        required=True,
        help='Tên địa điểm gửi hàng'
    )

    # Thông tin liên hệ
    phone = fields.Char(
        string='Số điện thoại',
        required=True,
        help='Số điện thoại liên hệ'
    )

    email = fields.Char(
        string='Email',
        help='Email liên hệ'
    )

    # Địa chỉ chi tiết
    district_id = fields.Char(
        string='Quận/huyện',
        help='Nhập tên quận/huyện'
    )

    ward_id = fields.Char(
        string='Phường/xã',
        help='Nhập tên phường/xã'
    )

    house_number = fields.Char(
        string='Số nhà',
        help='Số nhà'
    )

    street_name = fields.Char(
        string='Tên đường',
        required=True,
        help='Tên đường'
    )

    # Cấu hình
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
        tracking=True,
        help='Kích hoạt/Vô hiệu hóa địa điểm này'
    )

    # Computed field: Địa chỉ đầy đủ
    full_address = fields.Char(
        string='Địa chỉ đầy đủ',
        compute='_compute_full_address',
        store=True
    )

    @api.depends('house_number', 'street_name', 'ward_id', 'district_id')
    def _compute_full_address(self):
        """Tính toán địa chỉ đầy đủ"""
        for record in self:
            address_parts = []
            if record.house_number:
                address_parts.append(record.house_number)
            if record.street_name:
                address_parts.append(record.street_name)
            if record.ward_id:
                address_parts.append(record.ward_id)
            if record.district_id:
                address_parts.append(record.district_id)

            record.full_address = ', '.join(address_parts) if address_parts else ''

    @api.model
    def get_default_sender(self):
        """Get default sender location"""
        default = self.search([('is_default', '=', True), ('active', '=', True)], limit=1)
        return default if default else self.search([('active', '=', True)], limit=1)

    @api.model
    def get_sender_choices(self):
        """Get all active sender locations for selection"""
        return self.search([('active', '=', True)], order='sequence')

    @api.constrains('is_default')
    def _check_single_default(self):
        """Ensure only one default sender"""
        for record in self:
            if record.is_default:
                other_defaults = self.search([
                    ('id', '!=', record.id),
                    ('is_default', '=', True)
                ])
                if other_defaults:
                    other_defaults.write({'is_default': False})
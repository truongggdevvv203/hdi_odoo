from odoo import models, fields


class ReceiverAddress(models.Model):
    _name = 'receiver.address'
    _description = 'Receiver Address'

    name = fields.Char(string='Tên người nhận', required=True)
    phone = fields.Char(string='Điện thoại', required=True)
    email = fields.Char(string='Email')
    
    # Address fields
    street = fields.Char(string='Đường')
    street2 = fields.Char(string='Đường 2')
    city = fields.Char(string='Thành phố')
    state_id = fields.Many2one('res.country.state', string='Tỉnh/Thành')
    zip = fields.Char(string='Mã bưu điện')
    country_id = fields.Many2one('res.country', string='Quốc gia', default=lambda self: self.env.ref('base.vn'))
    
    active = fields.Boolean(string='Kích hoạt', default=True)
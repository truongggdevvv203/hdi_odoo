from odoo import models, fields


class IrConfigParameter(models.Model):
    _inherit = 'ir.config_parameter'
    
    # Thêm config parameters cho API JWT
    # Các parameter sẽ được lưu trong database

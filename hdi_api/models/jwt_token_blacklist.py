from odoo import api, fields, models
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from datetime import datetime, timedelta


class JwtTokenBlacklist(models.Model):
    _name = 'jwt.token.blacklist'
    _description = 'JWT Token Blacklist'
    _order = 'create_date desc'

    token_hash = fields.Char(
        string='Token Hash',
        required=True,
        index=True,
        help='SHA256 hash của token'
    )
    user_id = fields.Integer(
        string='User ID',
        required=True,
        index=True,
        help='ID của user'
    )
    exp_time = fields.Datetime(
        string='Expiration Time',
        required=True,
        help='Thời gian hết hạn của token'
    )
    create_date = fields.Datetime(
        string='Created Date',
        default=fields.Datetime.now,
        readonly=True
    )

    _sql_constraints = [
        ('token_hash_unique', 'unique(token_hash)', 'Token hash phải là duy nhất'),
    ]

    @api.model
    def _cleanup_expired_tokens(self):
        """Xóa các token đã hết hạn khỏi blacklist"""
        expired_records = self.search([
            ('exp_time', '<', datetime.utcnow())
        ])
        expired_records.unlink()
        return True

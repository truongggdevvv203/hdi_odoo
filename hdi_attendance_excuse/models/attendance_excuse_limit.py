from odoo import models, fields, api


class AttendanceExcuseLimit(models.Model):
    _name = 'attendance.excuse.limit'
    _description = 'Giới hạn số lần giải trình trong tháng'
    _order = 'excuse_type, id'

    excuse_type = fields.Selection([
        ('late', 'Đi muộn'),
        ('early', 'Về sớm'),
        ('missing_checkout', 'Quên check-out'),
    ], string='Loại giải trình', required=True, unique=True)

    monthly_limit = fields.Integer(
        string='Số lần được giải trình/tháng',
        required=True,
        default=3,
        help='Giới hạn số lần nhân viên được phép giải trình loại này trong một tháng'
    )

    description = fields.Text(
        string='Ghi chú',
        help='Mô tả chi tiết về giới hạn này'
    )

    active = fields.Boolean(
        string='Kích hoạt',
        default=True
    )

    def name_get(self):
        """Hiển thị tên bảng ghi dưới dạng 'Loại - Giới hạn lần'"""
        result = []
        for record in self:
            excuse_label = dict(record._fields['excuse_type'].selection).get(
                record.excuse_type, record.excuse_type)
            name = f"{excuse_label} ({record.monthly_limit} lần/tháng)"
            result.append((record.id, name))
        return result

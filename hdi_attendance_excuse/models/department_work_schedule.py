from odoo import models, fields, api
from odoo.exceptions import ValidationError


class DepartmentWorkSchedule(models.Model):
    _name = 'department.work.schedule'
    _description = 'Cấu hình giờ làm việc theo phòng ban'
    _rec_name = 'department_id'
    _order = 'department_id'

    department_id = fields.Many2one(
        'hr.department',
        string='Phòng ban',
        required=True,
        ondelete='cascade',
        unique=True,
        index=True
    )

    check_in_time = fields.Float(
        string='Giờ vào (Check-in)',
        required=True,
        default=8.5,
        help='Giờ vào tiêu chuẩn (8.5 = 8:30)'
    )

    check_out_time = fields.Float(
        string='Giờ ra (Check-out)',
        required=True,
        default=18.0,
        help='Giờ ra tiêu chuẩn (18.0 = 18:00)'
    )

    late_tolerance = fields.Float(
        string='Sai số cho phép muộn (phút)',
        required=True,
        default=15,
        help='Số phút cho phép vào muộn trước khi cần giải trình'
    )

    early_tolerance = fields.Float(
        string='Sai số cho phép về sớm (phút)',
        required=True,
        default=15,
        help='Số phút cho phép về sớm trước khi cần giải trình'
    )

    active = fields.Boolean(
        string='Kích hoạt',
        default=True
    )

    notes = fields.Text(
        string='Ghi chú',
        help='Ghi chú thêm về cấu hình này'
    )

    @api.constrains('check_in_time', 'check_out_time')
    def _check_schedule_validity(self):
        """Kiểm tra check_in_time < check_out_time"""
        for record in self:
            if record.check_in_time >= record.check_out_time:
                raise ValidationError(
                    f'Giờ vào ({record.check_in_time}) phải nhỏ hơn giờ ra ({record.check_out_time})'
                )

    @api.constrains('late_tolerance', 'early_tolerance')
    def _check_tolerance_validity(self):
        """Kiểm tra tolerance > 0"""
        for record in self:
            if record.late_tolerance < 0:
                raise ValidationError('Sai số muộn phải >= 0')
            if record.early_tolerance < 0:
                raise ValidationError('Sai số sớm phải >= 0')

    def _format_time(self, hours):
        """Chuyển đổi giờ (float) thành định dạng HH:MM"""
        hour = int(hours)
        minute = int((hours - hour) * 60)
        return f"{hour:02d}:{minute:02d}"

    def name_get(self):
        """Hiển thị tên theo định dạng: Phòng ban - 08:30 to 18:00"""
        result = []
        for record in self:
            check_in_str = self._format_time(record.check_in_time)
            check_out_str = self._format_time(record.check_out_time)
            name = f"{record.department_id.name} - {check_in_str} to {check_out_str}"
            result.append((record.id, name))
        return result

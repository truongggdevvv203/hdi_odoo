from odoo import models, fields


class AttendanceExcuseApproverConfig(models.Model):
    _name = 'attendance.excuse.approver.config'
    _description = 'Cấu hình người phê duyệt giải trình chấm công'
    _order = 'department_id, id'

    department_id = fields.Many2one(
        'hr.department',
        string='Phòng ban',
        required=True,
        ondelete='cascade',
        unique=True,
        help='Phòng ban áp dụng cấu hình này'
    )

    approver_id = fields.Many2one(
        'res.users',
        string='Người phê duyệt',
        required=True,
        help='Người dùng sẽ phê duyệt giải trình từ phòng ban này'
    )

    active = fields.Boolean(
        string='Kích hoạt',
        default=True
    )

    def name_get(self):
        """Hiển thị tên bảng ghi dưới dạng 'Phòng ban - Người phê duyệt'"""
        result = []
        for record in self:
            name = f"{record.department_id.name} → {record.approver_id.name}"
            result.append((record.id, name))
        return result

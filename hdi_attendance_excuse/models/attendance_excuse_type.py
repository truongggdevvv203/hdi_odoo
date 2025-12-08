from odoo import models, fields, api


class AttendanceExcuseType(models.Model):
    """
    Loại giải trình chấm công
    Ví dụ: Đi muộn, Về sớm, Quên check-in, Sai giờ...
    """
    _name = 'attendance.excuse.type'
    _description = 'Attendance Excuse Type (Loại giải trình chấm công)'
    _order = 'sequence, id'

    name = fields.Char(
        string='Tên loại giải trình',
        required=True
    )

    code = fields.Char(
        string='Mã code',
        required=True,
        unique=True,
        help='Identifier duy nhất cho loại giải trình'
    )

    category = fields.Selection(
        [
            ('late', 'Đi muộn'),
            ('early', 'Về sớm'),
            ('missing_checkin', 'Quên check-in'),
            ('missing_checkout', 'Quên check-out'),
            ('wrong_time', 'Sai giờ check-in/out'),
            ('other', 'Khác'),
        ],
        string='Loại',
        required=True
    )

    sequence = fields.Integer(
        string='Thứ tự',
        default=1
    )

    description = fields.Text(
        string='Mô tả'
    )

    require_evidence = fields.Boolean(
        string='Yêu cầu bằng chứng',
        default=False,
        help='Có yêu cầu upload bằng chứng không'
    )

    active = fields.Boolean(
        string='Hoạt động',
        default=True
    )

    company_id = fields.Many2one(
        'res.company',
        string='Công ty',
        default=lambda self: self.env.company
    )

from odoo import models, fields, api
from datetime import datetime, timedelta


class AttendanceExcuse(models.Model):
    """
    Giải trình chấm công - Hệ thống tự động phát hiện và ghi nhận các trường hợp cần giải trình
    """
    _name = 'attendance.excuse'
    _description = 'Attendance Excuse (Giải trình chấm công)'
    _order = 'date desc, employee_id'
    _rec_name = 'display_name'

    display_name = fields.Char(
        string='Tên',
        compute='_compute_display_name',
        store=True
    )

    employee_id = fields.Many2one(
        'hr.employee',
        string='Nhân viên',
        required=True,
        ondelete='cascade'
    )

    date = fields.Date(
        string='Ngày',
        required=True
    )

    excuse_type_id = fields.Many2one(
        'attendance.excuse.type',
        string='Loại giải trình',
        required=True,
        ondelete='restrict'
    )

    # Attendance references
    attendance_id = fields.Many2one(
        'hr.attendance',
        string='Bản ghi chấm công',
        ondelete='set null'
    )

    # Details for different excuse types
    original_checkin = fields.Datetime(
        string='Check-in gốc'
    )

    original_checkout = fields.Datetime(
        string='Check-out gốc'
    )

    corrected_checkin = fields.Datetime(
        string='Check-in đã sửa'
    )

    corrected_checkout = fields.Datetime(
        string='Check-out đã sửa'
    )

    late_minutes = fields.Integer(
        string='Số phút đi muộn',
        default=0
    )

    early_minutes = fields.Integer(
        string='Số phút về sớm',
        default=0
    )

    # Request tracking
    request_id = fields.Many2one(
        'attendance.excuse.request',
        string='Yêu cầu giải trình',
        ondelete='cascade'
    )

    # Status
    status = fields.Selection(
        [
            ('pending', 'Chờ xử lý'),
            ('approved', 'Đã phê duyệt'),
            ('rejected', 'Bị từ chối'),
            ('resolved', 'Đã xử lý'),
        ],
        string='Trạng thái',
        default='pending'
    )

    notes = fields.Text(
        string='Ghi chú'
    )

    @api.depends('employee_id', 'date', 'excuse_type_id')
    def _compute_display_name(self):
        for record in self:
            if record.employee_id and record.date and record.excuse_type_id:
                record.display_name = f"{record.employee_id.name} - {record.date} - {record.excuse_type_id.name}"
            else:
                record.display_name = "Giải trình chấm công"

    @api.model
    def detect_and_create_excuses(self):
        """
        Tự động phát hiện các trường hợp cần giải trình từ chấm công
        Chạy mỗi ngày để kiểm tra dữ liệu chấm công
        """
        # Kiểm tra các trường hợp đi muộn/về sớm
        self._detect_late_arrival()
        self._detect_early_departure()
        self._detect_missing_checkout()

    def _detect_late_arrival(self):
        """Phát hiện trường hợp đi muộn"""
        # Lấy cấu hình giờ làm việc (mặc định 8:30 AM)
        late_threshold = 8.5  # 8:30 AM

        # Tìm tất cả bản ghi chấm công hôm nay
        today = datetime.now().date()
        attendances = self.env['hr.attendance'].search([
            ('check_in', '>=', datetime.combine(today, datetime.min.time())),
            ('check_in', '<', datetime.combine(today, datetime.max.time())),
        ])

        for att in attendances:
            if att.check_in:
                check_in_hour = att.check_in.hour + att.check_in.minute / 60
                if check_in_hour > late_threshold:
                    late_minutes = int((check_in_hour - late_threshold) * 60)
                    
                    # Kiểm tra xem đã có giải trình chưa
                    existing = self.search([
                        ('attendance_id', '=', att.id),
                        ('excuse_type_id.category', '=', 'late'),
                    ])
                    
                    if not existing:
                        excuse_type = self.env['attendance.excuse.type'].search(
                            [('category', '=', 'late')], limit=1
                        )
                        if excuse_type:
                            self.create({
                                'employee_id': att.employee_id.id,
                                'date': att.check_in.date(),
                                'excuse_type_id': excuse_type.id,
                                'attendance_id': att.id,
                                'original_checkin': att.check_in,
                                'late_minutes': late_minutes,
                                'status': 'pending',
                            })

    def _detect_early_departure(self):
        """Phát hiện trường hợp về sớm"""
        # Lấy cấu hình giờ tan ca (mặc định 5:00 PM = 17:00)
        early_threshold = 17.0  # 5:00 PM

        today = datetime.now().date()
        attendances = self.env['hr.attendance'].search([
            ('check_out', '>=', datetime.combine(today, datetime.min.time())),
            ('check_out', '<', datetime.combine(today, datetime.max.time())),
        ])

        for att in attendances:
            if att.check_out:
                check_out_hour = att.check_out.hour + att.check_out.minute / 60
                if check_out_hour < early_threshold:
                    early_minutes = int((early_threshold - check_out_hour) * 60)
                    
                    existing = self.search([
                        ('attendance_id', '=', att.id),
                        ('excuse_type_id.category', '=', 'early'),
                    ])
                    
                    if not existing:
                        excuse_type = self.env['attendance.excuse.type'].search(
                            [('category', '=', 'early')], limit=1
                        )
                        if excuse_type:
                            self.create({
                                'employee_id': att.employee_id.id,
                                'date': att.check_out.date(),
                                'excuse_type_id': excuse_type.id,
                                'attendance_id': att.id,
                                'original_checkout': att.check_out,
                                'early_minutes': early_minutes,
                                'status': 'pending',
                            })

    def _detect_missing_checkout(self):
        """Phát hiện trường hợp quên check-out"""
        # Lấy tất cả attendance không có check-out từ hôm qua
        yesterday = datetime.now().date() - timedelta(days=1)
        attendances = self.env['hr.attendance'].search([
            ('check_in', '>=', datetime.combine(yesterday, datetime.min.time())),
            ('check_in', '<', datetime.combine(yesterday, datetime.max.time())),
            ('check_out', '=', False),
        ])

        for att in attendances:
            existing = self.search([
                ('attendance_id', '=', att.id),
                ('excuse_type_id.category', '=', 'missing_checkout'),
            ])

            if not existing:
                excuse_type = self.env['attendance.excuse.type'].search(
                    [('category', '=', 'missing_checkout')], limit=1
                )
                if excuse_type:
                    self.create({
                        'employee_id': att.employee_id.id,
                        'date': att.check_in.date(),
                        'excuse_type_id': excuse_type.id,
                        'attendance_id': att.id,
                        'original_checkin': att.check_in,
                        'status': 'pending',
                    })

    def approve(self):
        """Phê duyệt giải trình"""
        for record in self:
            record.status = 'approved'
            # Tự động tạo yêu cầu giải trình nếu chưa có
            if not record.request_id:
                request = self.env['attendance.excuse.request'].create({
                    'excuse_id': record.id,
                    'employee_id': record.employee_id.id,
                    'date': record.date,
                    'excuse_type_id': record.excuse_type_id.id,
                    'state': 'approved',
                })
                record.request_id = request.id

    def reject(self):
        """Từ chối giải trình"""
        for record in self:
            record.status = 'rejected'

    def create_request(self):
        """Tạo yêu cầu giải trình"""
        for record in self:
            if not record.request_id:
                request = self.env['attendance.excuse.request'].create({
                    'excuse_id': record.id,
                    'employee_id': record.employee_id.id,
                    'date': record.date,
                    'excuse_type_id': record.excuse_type_id.id,
                    'state': 'draft',
                })
                record.request_id = request.id

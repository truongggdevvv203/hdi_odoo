from odoo import models, fields, api
from datetime import datetime, timedelta


class AttendanceExcuse(models.Model):
    """
    Giải trình chấm công - Hệ thống quản lý các trường hợp cần giải trình
    Hỗ trợ cả tự động phát hiện và yêu cầu giải trình từ nhân viên
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

    # Details for different excuse types - automatically pulled from hr.attendance
    original_checkin = fields.Datetime(
        string='Check-in gốc',
        compute='_compute_original_checkin',
        store=True
    )

    original_checkout = fields.Datetime(
        string='Check-out gốc',
        compute='_compute_original_checkout',
        store=True
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

    # Request details
    reason = fields.Text(
        string='Lý do',
        help='Lý do chi tiết cho yêu cầu giải trình'
    )

    evidence_attachment = fields.Many2many(
        'ir.attachment',
        string='Bằng chứng',
        help='Upload hình ảnh, tài liệu minh chứng'
    )

    # Requested corrections (if applicable)
    requested_checkin = fields.Datetime(
        string='Giờ check-in đề xuất'
    )

    requested_checkout = fields.Datetime(
        string='Giờ check-out đề xuất'
    )

    # Approval workflow
    state = fields.Selection(
        [
            ('pending', 'Chờ xử lý'),
            ('submitted', 'Đã gửi'),
            ('approved', 'Đã phê duyệt'),
            ('rejected', 'Bị từ chối'),
        ],
        string='Trạng thái',
        default='pending'
    )

    approver_id = fields.Many2one(
        'res.users',
        string='Người phê duyệt',
        readonly=True
    )

    approval_date = fields.Datetime(
        string='Ngày phê duyệt',
        readonly=True
    )

    rejection_reason = fields.Text(
        string='Lý do từ chối'
    )

    notes = fields.Text(
        string='Ghi chú'
    )

    company_id = fields.Many2one(
        'res.company',
        string='Công ty',
        default=lambda self: self.env.company
    )

    @api.depends('employee_id', 'date', 'excuse_type_id', 'state')
    def _compute_display_name(self):
        for record in self:
            if record.employee_id and record.date and record.excuse_type_id:
                state_label = dict(record._fields['state'].selection).get(record.state, record.state)
                record.display_name = f"{record.employee_id.name} - {record.date} - {record.excuse_type_id.name} ({state_label})"
            else:
                record.display_name = "Giải trình chấm công"

    @api.depends('attendance_id')
    def _compute_original_checkin(self):
        """Lấy check-in gốc từ hr.attendance"""
        for record in self:
            if record.attendance_id:
                record.original_checkin = record.attendance_id.check_in
            else:
                record.original_checkin = None

    @api.depends('attendance_id')
    def _compute_original_checkout(self):
        """Lấy check-out gốc từ hr.attendance"""
        for record in self:
            if record.attendance_id:
                record.original_checkout = record.attendance_id.check_out
            else:
                record.original_checkout = None

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

        excuse_type = self.env['attendance.excuse.type'].search(
            [('category', '=', 'late')], limit=1
        )
        
        if not excuse_type:
            return

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
                        self.create({
                            'employee_id': att.employee_id.id,
                            'date': att.check_in.date(),
                            'excuse_type_id': excuse_type.id,
                            'attendance_id': att.id,
                            'late_minutes': late_minutes,
                            'state': 'pending',
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

        excuse_type = self.env['attendance.excuse.type'].search(
            [('category', '=', 'early')], limit=1
        )
        
        if not excuse_type:
            return

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
                        self.create({
                            'employee_id': att.employee_id.id,
                            'date': att.check_out.date(),
                            'excuse_type_id': excuse_type.id,
                            'attendance_id': att.id,
                            'early_minutes': early_minutes,
                            'state': 'pending',
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

        excuse_type = self.env['attendance.excuse.type'].search(
            [('category', '=', 'missing_checkout')], limit=1
        )
        
        if not excuse_type:
            return

        for att in attendances:
            existing = self.search([
                ('attendance_id', '=', att.id),
                ('excuse_type_id.category', '=', 'missing_checkout'),
            ])

            if not existing:
                self.create({
                    'employee_id': att.employee_id.id,
                    'date': att.check_in.date(),
                    'excuse_type_id': excuse_type.id,
                    'attendance_id': att.id,
                    'state': 'pending',
                })

    def submit(self):
        """Gửi yêu cầu giải trình"""
        for record in self:
            if record.state != 'pending':
                continue
            record.state = 'submitted'

    def approve(self):
        """Phê duyệt giải trình"""
        for record in self:
            if record.state != 'submitted':
                continue
            record.state = 'approved'
            record.approver_id = self.env.user.id
            record.approval_date = fields.Datetime.now()

            # If there are corrections, apply them to attendance
            if record.requested_checkin or record.requested_checkout:
                self._apply_corrections(record)

    def reject(self):
        """Từ chối giải trình"""
        for record in self:
            if record.state != 'submitted':
                continue
            record.state = 'rejected'
            record.approver_id = self.env.user.id
            record.approval_date = fields.Datetime.now()

    def _apply_corrections(self, record):
        """Áp dụng các sửa chữa vào bản ghi chấm công"""
        if record.attendance_id:
            att = record.attendance_id
            
            if record.requested_checkin:
                att.check_in = record.requested_checkin
                record.corrected_checkin = record.requested_checkin
            
            if record.requested_checkout:
                att.check_out = record.requested_checkout
                record.corrected_checkout = record.requested_checkout

    def get_my_requests(self):
        """Lấy danh sách yêu cầu của nhân viên hiện tại"""
        return self.search([
            ('employee_id', '=', self.env.user.employee_id.id),
        ], order='date desc')

    def get_pending_approvals(self):
        """Lấy danh sách yêu cầu chờ phê duyệt"""
        return self.search([
            ('state', '=', 'submitted'),
        ], order='date desc')

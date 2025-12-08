from odoo import models, fields, api


class AttendanceExcuseRequest(models.Model):
    """
    Yêu cầu giải trình chấm công
    Nhân viên gửi yêu cầu để giải trình các trường hợp bất thường
    """
    _name = 'attendance.excuse.request'
    _description = 'Attendance Excuse Request (Yêu cầu giải trình chấm công)'
    _order = 'date desc, employee_id'
    _rec_name = 'display_name'

    display_name = fields.Char(
        string='Tên',
        compute='_compute_display_name',
        store=True
    )

    # Reference to auto-detected excuse
    excuse_id = fields.Many2one(
        'attendance.excuse',
        string='Giải trình tự động',
        ondelete='cascade'
    )

    # Manual request
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

    # Reason and evidence
    reason = fields.Text(
        string='Lý do',
        required=True,
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
            ('draft', 'Nháp'),
            ('submitted', 'Đã gửi'),
            ('approved', 'Đã phê duyệt'),
            ('rejected', 'Bị từ chối'),
        ],
        string='Trạng thái',
        default='draft'
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
                record.display_name = "Yêu cầu giải trình"

    def submit(self):
        """Gửi yêu cầu giải trình"""
        for record in self:
            if record.state != 'draft':
                continue
            record.state = 'submitted'

    def approve(self):
        """Phê duyệt yêu cầu giải trình"""
        for record in self:
            if record.state != 'submitted':
                continue
            record.state = 'approved'
            record.approver_id = self.env.user.id
            record.approval_date = fields.Datetime.now()

            # Update excuse status
            if record.excuse_id:
                record.excuse_id.status = 'approved'

            # If there are corrections, apply them to attendance
            if record.requested_checkin or record.requested_checkout:
                self._apply_corrections(record)

    def reject(self):
        """Từ chối yêu cầu giải trình"""
        for record in self:
            if record.state != 'submitted':
                continue
            record.state = 'rejected'
            record.approver_id = self.env.user.id
            record.approval_date = fields.Datetime.now()

            if record.excuse_id:
                record.excuse_id.status = 'rejected'

    def _apply_corrections(self, request):
        """Áp dụng các sửa chữa vào bản ghi chấm công"""
        if request.excuse_id and request.excuse_id.attendance_id:
            att = request.excuse_id.attendance_id
            
            if request.requested_checkin:
                att.check_in = request.requested_checkin
                request.excuse_id.corrected_checkin = request.requested_checkin
            
            if request.requested_checkout:
                att.check_out = request.requested_checkout
                request.excuse_id.corrected_checkout = request.requested_checkout

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

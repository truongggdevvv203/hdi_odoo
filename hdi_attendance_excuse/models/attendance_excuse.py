from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
import pytz


class AttendanceExcuse(models.Model):
    _name = 'attendance.excuse'
    _description = 'Attendance Excuse (Giải trình chấm công)'
    _order = 'date desc, employee_id'
    _rec_name = 'display_name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    display_name = fields.Char(
        string='Tên',
        compute='_compute_display_name',
        store=True
    )

    employee_id = fields.Many2one(
        'hr.employee',
        string='Nhân viên',
        required=True,
        ondelete='cascade',
        index=True,
        tracking=True
    )

    date = fields.Date(
        string='Ngày',
        required=True,
        index=True,
        tracking=True
    )

    @api.onchange('attendance_id')
    def _onchange_attendance_id(self):
        """Tự động điền employee_id và date từ attendance_id"""
        if self.attendance_id:
            self.employee_id = self.attendance_id.employee_id.id
            # Lấy ngày từ check_in
            if self.attendance_id.check_in:
                check_in_date = fields.Datetime.context_timestamp(self,
                                                                  self.attendance_id.check_in).date()
                self.date = check_in_date

    @api.onchange('excuse_type')
    def _onchange_excuse_type(self):
        """Tự động điền requested_checkin/checkout dựa trên excuse_type"""
        if not self.attendance_id:
            return

        # Reset các trường request
        self.requested_checkin = False
        self.requested_checkout = False

        # Nếu late: requested_checkout = original_checkout (nhân viên chỉ cần sửa check-in)
        if self.excuse_type == 'late':
            self.requested_checkin = self.original_checkin
            self.requested_checkout = self.original_checkout

        # Nếu early: requested_checkin = original_checkin (nhân viên chỉ cần sửa check-out)
        elif self.excuse_type == 'early':
            self.requested_checkin = self.original_checkin
            self.requested_checkout = self.original_checkout

        # Nếu missing_checkout: requested_checkin = original_checkin (nhân viên cần điền check-out)
        elif self.excuse_type == 'missing_checkout':
            self.requested_checkin = self.original_checkin

    excuse_type = fields.Selection([
        ('late', 'Đi muộn'),
        ('early', 'Về sớm'),
        ('missing_checkout', 'Quên check-out'),
    ], string="Loại giải trình", compute='_compute_excuse_type', store=True,
        tracking=True)

    # Attendance references
    attendance_id = fields.Many2one(
        'hr.attendance',
        string='Bản ghi chấm công',
        ondelete='set null',
        index=True
    )

    # Details for different excuse types - automatically pulled from hr.attendance
    original_checkin = fields.Datetime(
        string='Check-in gốc',
        compute='_compute_original_times',
        store=True
    )

    original_checkout = fields.Datetime(
        string='Check-out gốc',
        compute='_compute_original_times',
        store=True
    )

    corrected_checkin = fields.Datetime(
        string='Check-in đã sửa',
        tracking=True
    )

    corrected_checkout = fields.Datetime(
        string='Check-out đã sửa',
        tracking=True
    )

    late_minutes = fields.Integer(
        string='Số phút đi muộn',
        default=0,
        readonly=True
    )

    early_minutes = fields.Integer(
        string='Số phút về sớm',
        default=0,
        readonly=True
    )

    # Request details
    reason = fields.Text(
        string='Lý do',
        help='Lý do chi tiết cho yêu cầu giải trình',
        tracking=True
    )

    # Requested corrections (if applicable)
    requested_checkin = fields.Datetime(
        string='Giờ check-in yêu cầu sửa'
    )

    requested_checkout = fields.Datetime(
        string='Giờ check-out yêu cầu sửa'
    )

    # Approval workflow
    state = fields.Selection(
        [
            ('draft', 'Nháp'),
            ('pending', 'Chờ xử lý'),
            ('submitted', 'Đã gửi'),
            ('approved', 'Đã phê duyệt'),
            ('rejected', 'Bị từ chối'),
        ],
        string='Trạng thái',
        default='draft',
        tracking=True,
        index=True
    )

    approver_id = fields.Many2one(
        'res.users',
        string='Người phê duyệt',
        readonly=True,
        tracking=True
    )

    approval_date = fields.Datetime(
        string='Ngày phê duyệt',
        readonly=True
    )

    rejection_reason = fields.Text(
        string='Lý do từ chối',
        tracking=True
    )

    notes = fields.Text(
        string='Ghi chú'
    )

    can_approve = fields.Boolean(
        string='Có thể phê duyệt',
        compute='_compute_can_approve',
        store=False
    )

    can_reject = fields.Boolean(
        string='Có thể từ chối',
        compute='_compute_can_reject',
        store=False
    )

    @api.depends('approver_id', 'state')
    def _compute_can_approve(self):
        for record in self:
            if record.state != 'submitted':
                record.can_approve = False
                continue

            if not record.approver_id:
                record.can_approve = self.env.user.has_group('hr.group_hr_manager')
                continue

            if record.approver_id.id == self.env.user.id:
                record.can_approve = True
                continue

            record.can_approve = self.env.user.has_group('hr.group_hr_manager')

    @api.depends('approver_id', 'state')
    def _compute_can_reject(self):
        for record in self:
            if record.state != 'submitted':
                record.can_reject = False
                continue

            if not record.approver_id:
                record.can_reject = self.env.user.has_group('hr.group_hr_manager')
                continue

            if record.approver_id.id == self.env.user.id:
                record.can_reject = True
                continue

            record.can_reject = self.env.user.has_group('hr.group_hr_manager')

    @api.depends('employee_id', 'date', 'excuse_type', 'state')
    def _compute_display_name(self):
        for record in self:
            if record.employee_id and record.date and record.excuse_type:
                excuse_label = dict(record._fields['excuse_type'].selection).get(
                    record.excuse_type, record.excuse_type)
                state_label = dict(record._fields['state'].selection).get(record.state,
                                                                          record.state)
                record.display_name = f"{record.employee_id.name} - {record.date} - {excuse_label} ({state_label})"
            else:
                record.display_name = "Giải trình chấm công"

    @api.depends('attendance_id', 'attendance_id.check_in',
                 'attendance_id.check_out')
    def _compute_original_times(self):
        for record in self:
            if record.attendance_id:
                record.original_checkin = record.attendance_id.check_in
                record.original_checkout = record.attendance_id.check_out
            else:
                record.original_checkin = False
                record.original_checkout = False

    @api.depends('original_checkin', 'original_checkout', 'attendance_id')
    def _compute_excuse_type(self):
        for record in self:
            excuse_type = 'late'
            if not record.original_checkout:
                record.excuse_type = 'missing_checkout'
                continue

            local_checkin = self._convert_to_local_time(record.original_checkin)
            check_in_hour = local_checkin.hour + local_checkin.minute / 60.0
            schedule = self._get_work_schedule(record.employee_id)

            if check_in_hour > (schedule['start_time'] + schedule['late_tolerance']):
                record.excuse_type = 'late'
                continue

            local_checkout = self._convert_to_local_time(record.original_checkout)
            check_out_hour = local_checkout.hour + local_checkout.minute / 60.0

            if check_out_hour < schedule['end_time']:
                record.excuse_type = 'early'
                continue

            record.excuse_type = 'late'

    def _get_company_timezone(self):
        return pytz.timezone(self.env.user.tz or 'Asia/Ho_Chi_Minh')

    def _convert_to_local_time(self, dt):
        if not dt:
            return None
        if dt.tzinfo is None:
            dt = pytz.UTC.localize(dt)
        tz = self._get_company_timezone()
        return dt.astimezone(tz)

    def _get_work_schedule(self, employee):
        return {
            'start_time': 8.5,
            'end_time': 18.0,
            'late_tolerance': 0.25,
        }

    @api.model
    def detect_and_create_excuses(self, target_date=None):
        if target_date is None:
            target_date = fields.Date.context_today(self)

        self._detect_late_arrival(target_date)
        self._detect_early_departure(target_date)
        self._detect_missing_checkout(target_date)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Thành công',
                'message': f'Đã phát hiện và tạo giải trình chấm công cho ngày {target_date}',
                'type': 'success',
                'sticky': False,
            }
        }

    def _detect_late_arrival(self, target_date):
        attendances = self.env['hr.attendance'].search([
            ('check_in', '>=', datetime.combine(target_date, datetime.min.time())),
            ('check_in', '<=', datetime.combine(target_date, datetime.max.time())),
        ])

        for att in attendances:
            if not att.check_in:
                continue

            existing = self.search([
                ('attendance_id', '=', att.id),
                ('excuse_type', '=', 'late'),
            ], limit=1)

            if existing:
                continue

            local_checkin = self._convert_to_local_time(att.check_in)
            check_in_hour = local_checkin.hour + local_checkin.minute / 60.0

            schedule = self._get_work_schedule(att.employee_id)
            late_threshold = schedule['start_time'] + schedule['late_tolerance']

            if check_in_hour > late_threshold:
                late_minutes = int((check_in_hour - schedule['start_time']) * 60)

                self.create({
                    'employee_id': att.employee_id.id,
                    'date': target_date,
                    'attendance_id': att.id,
                    'late_minutes': late_minutes,
                    'state': 'pending',
                    'notes': f'Tự động phát hiện: Đi muộn {late_minutes} phút',
                })

    def _detect_early_departure(self, target_date):

        attendances = self.env['hr.attendance'].search([
            ('check_in', '>=', datetime.combine(target_date, datetime.min.time())),
            ('check_in', '<=', datetime.combine(target_date, datetime.max.time())),
            ('check_out', '!=', False),
        ])

        for att in attendances:
            if not att.check_out:
                continue

            existing = self.search([
                ('attendance_id', '=', att.id),
                ('excuse_type', '=', 'early'),
            ], limit=1)

            if existing:
                continue

            local_checkout = self._convert_to_local_time(att.check_out)
            check_out_hour = local_checkout.hour + local_checkout.minute / 60.0

            schedule = self._get_work_schedule(att.employee_id)
            early_threshold = schedule['end_time']

            if check_out_hour < early_threshold:
                early_minutes = int((early_threshold - check_out_hour) * 60)

                self.create({
                    'employee_id': att.employee_id.id,
                    'date': target_date,
                    'attendance_id': att.id,
                    'early_minutes': early_minutes,
                    'state': 'pending',
                    'notes': f'Tự động phát hiện: Về sớm {early_minutes} phút',
                })

    def _detect_missing_checkout(self, target_date):

        previous_date = target_date - timedelta(days=1)

        attendances = self.env['hr.attendance'].search([
            ('check_in', '>=', datetime.combine(previous_date, datetime.min.time())),
            ('check_in', '<=', datetime.combine(previous_date, datetime.max.time())),
            ('check_out', '=', False),
        ])

        for att in attendances:

            existing = self.search([
                ('attendance_id', '=', att.id),
                ('excuse_type', '=', 'missing_checkout'),
            ], limit=1)

            if not existing:
                self.create({
                    'employee_id': att.employee_id.id,
                    'date': previous_date,
                    'attendance_id': att.id,
                    'state': 'pending',
                    'notes': 'Tự động phát hiện: Quên check-out',
                })

    def action_submit(self):

        for record in self:
            if record.state not in ['draft', 'pending']:
                continue

            if record.employee_id and record.date and record.excuse_type:
                self._check_monthly_limit(record.employee_id, record.excuse_type,
                                          record.date)

            if not record.approver_id and record.employee_id:
                approver_config = self.env['attendance.excuse.approver.config'].search([
                    ('department_id', '=', record.employee_id.department_id.id),
                    ('active', '=', True)
                ], limit=1)

                if approver_config:
                    record.approver_id = approver_config.approver_id.id
                elif record.employee_id.parent_id and record.employee_id.parent_id.user_id:
                    record.approver_id = record.employee_id.parent_id.user_id.id

            record.state = 'submitted'
            record.message_post(body="Yêu cầu giải trình đã được gửi")

    def _check_monthly_limit(self, employee, excuse_type, date):
        limit_config = self.env['attendance.excuse.limit'].search([
            ('excuse_type', '=', excuse_type),
            ('active', '=', True)
        ], limit=1)

        if not limit_config:
            return

        month_start = date.replace(day=1)
        if date.month == 12:
            month_end = month_start.replace(year=date.year + 1, month=1) - timedelta(
                days=1)
        else:
            month_end = month_start.replace(month=date.month + 1) - timedelta(days=1)

        approved_count = self.search_count([
            ('employee_id', '=', employee.id),
            ('excuse_type', '=', excuse_type),
            ('state', '=', 'approved'),
            ('date', '>=', month_start),
            ('date', '<=', month_end)
        ])

        submitted_count = self.search_count([
            ('employee_id', '=', employee.id),
            ('excuse_type', '=', excuse_type),
            ('state', 'in', ['submitted', 'pending']),
            ('date', '>=', month_start),
            ('date', '<=', month_end)
        ])

        total_count = approved_count + submitted_count

        if total_count >= limit_config.monthly_limit:
            excuse_label = dict(self._fields['excuse_type'].selection).get(
                excuse_type, excuse_type)
            raise ValidationError(
                f"Nhân viên {employee.name} đã vượt quá giới hạn giải trình \"{excuse_label}\" "
                f"({limit_config.monthly_limit} lần/tháng) trong tháng {date.month}/{date.year}. "
                f"Hiện tại: {total_count}/{limit_config.monthly_limit}"
            )

    def action_approve(self):
        for record in self:
            if record.state != 'submitted':
                continue

            if record.approver_id and record.approver_id.id != self.env.user.id:
                if not self.env.user.has_group('hr.group_hr_manager'):
                    raise UserError(
                        'Bạn không có quyền phê duyệt đơn này. Chỉ người phê duyệt được chỉ định hoặc HR Manager mới có thể phê duyệt.')

            record.write({
                'state': 'approved',
                'approver_id': self.env.user.id,
                'approval_date': fields.Datetime.now(),
            })

            if record.attendance_id:
                att = record.attendance_id

                if record.corrected_checkin:
                    att.check_in = record.corrected_checkin
                elif record.requested_checkin:
                    att.check_in = record.requested_checkin
                    record.corrected_checkin = record.requested_checkin

                if record.corrected_checkout:
                    att.check_out = record.corrected_checkout
                elif record.requested_checkout:
                    att.check_out = record.requested_checkout
                    record.corrected_checkout = record.requested_checkout

            record.message_post(
                body=f"Yêu cầu giải trình đã được phê duyệt bởi {self.env.user.name}"
            )

    def action_reject(self):
        for record in self:
            if record.state != 'submitted':
                continue

            if record.approver_id and record.approver_id.id != self.env.user.id:
                if not self.env.user.has_group('hr.group_hr_manager'):
                    raise UserError(
                        'Bạn không có quyền từ chối đơn này. Chỉ người phê duyệt được chỉ định hoặc HR Manager mới có thể từ chối.')

            record.write({
                'state': 'rejected',
                'approver_id': self.env.user.id,
                'approval_date': fields.Datetime.now(),
            })

            record.message_post(
                body=f"Yêu cầu giải trình đã bị từ chối bởi {self.env.user.name}"
            )

    def action_reset_to_draft(self):
        for record in self:
            record.state = 'draft'

    def get_my_requests(self):
        return self.search([
            ('employee_id.user_id', '=', self.env.user.id),
        ], order='date desc')

    def get_pending_approvals(self):
        return self.search([
            ('state', '=', 'submitted'),
        ], order='date desc')

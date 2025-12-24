"""
Attendance Excuse Model
Quản lý giải trình chấm công cho nhân viên
"""
from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
import pytz


class AttendanceExcuse(models.Model):
    _name = 'attendance.excuse'
    _description = 'Giải trình chấm công'
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
        compute='_compute_employee_id',
        store=True,
        readonly=False,
        ondelete='cascade',
        index=True,
        tracking=True
    )

    date = fields.Date(
        string='Ngày',
        compute='_compute_date',
        store=True,
        readonly=False,
        index=True,
        tracking=True
    )

    attendance_id = fields.Many2one(
        'hr.attendance',
        string='Bản ghi chấm công',
        ondelete='cascade',
        index=True,
        required=True
    )

    excuse_type = fields.Selection([
        ('late_or_early', 'Đi muộn/về sớm'),
        ('missing_checkin_out', 'Thiếu chấm công'),
    ], string="Loại giải trình", compute='_compute_excuse_type', store=True, tracking=True)

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

    requested_checkin = fields.Datetime(
        string='Check-in yêu cầu sửa'
    )

    requested_checkout = fields.Datetime(
        string='Check-out yêu cầu sửa'
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

    reason = fields.Text(
        string='Lý do',
        help='Lý do chi tiết cho yêu cầu giải trình',
        tracking=True
    )

    notes = fields.Text(
        string='Ghi chú'
    )

    state = fields.Selection(
        [
            ('draft', 'Nháp'),
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

    is_approver = fields.Boolean(
        string='Là người phê duyệt',
        compute='_compute_is_approver',
        store=False
    )

    @api.depends('employee_id', 'date', 'excuse_type', 'state')
    def _compute_display_name(self):
        """Tính tên hiển thị"""
        for record in self:
            if record.employee_id and record.date and record.excuse_type:
                excuse_label = dict(record._fields['excuse_type'].selection).get(
                    record.excuse_type, record.excuse_type)
                state_label = dict(record._fields['state'].selection).get(record.state, record.state)
                record.display_name = f"{record.employee_id.name} - {record.date} - {excuse_label} ({state_label})"
            else:
                record.display_name = "Giải trình chấm công"

    @api.depends('attendance_id')
    def _compute_employee_id(self):
        """Lấy nhân viên từ attendance"""
        for record in self:
            if record.attendance_id:
                record.employee_id = record.attendance_id.employee_id

    @api.depends('attendance_id')
    def _compute_date(self):
        """Lấy ngày từ attendance"""
        for record in self:
            if record.attendance_id and record.attendance_id.check_in:
                check_in_date = fields.Datetime.context_timestamp(record, record.attendance_id.check_in).date()
                record.date = check_in_date

    @api.depends('attendance_id', 'attendance_id.check_in', 'attendance_id.check_out')
    def _compute_original_times(self):
        """Lấy thời gian gốc từ attendance"""
        for record in self:
            if record.attendance_id:
                record.original_checkin = record.attendance_id.check_in
                record.original_checkout = record.attendance_id.check_out
            else:
                record.original_checkin = False
                record.original_checkout = False

    @api.depends('original_checkin', 'original_checkout', 'attendance_id', 
                 'attendance_id.attendance_status', 'attendance_id.is_invalid_record')
    def _compute_excuse_type(self):
        """Tự động xác định loại giải trình dựa trên attendance"""
        for record in self:
            if not record.attendance_id:
                record.excuse_type = 'late_or_early'
                continue
            
            att = record.attendance_id
            # Nếu không có check-out → missing_checkin_out
            if not record.original_checkout or not att.is_invalid_record:
                record.excuse_type = 'missing_checkin_out' if att.attendance_status == 'missing_checkin_out' else 'late_or_early'
            else:
                record.excuse_type = 'late_or_early'

    @api.depends('approver_id')
    def _compute_is_approver(self):
        """Kiểm tra user hiện tại có phải là người phê duyệt"""
        for record in self:
            record.is_approver = record.approver_id and record.approver_id.id == self.env.user.id

    @api.depends('approver_id', 'state')
    def _compute_can_approve(self):
        """Kiểm tra user có quyền phê duyệt không"""
        for record in self:
            if record.state != 'submitted':
                record.can_approve = False
                continue

            if not record.approver_id:
                record.can_approve = self.env.user.has_group('hr.group_hr_manager')
            elif record.approver_id.id == self.env.user.id:
                record.can_approve = True
            else:
                record.can_approve = self.env.user.has_group('hr.group_hr_manager')

    @api.depends('approver_id', 'state')
    def _compute_can_reject(self):
        """Kiểm tra user có quyền từ chối không"""
        for record in self:
            if record.state != 'submitted':
                record.can_reject = False
                continue

            if not record.approver_id:
                record.can_reject = self.env.user.has_group('hr.group_hr_manager')
            elif record.approver_id.id == self.env.user.id:
                record.can_reject = True
            else:
                record.can_reject = self.env.user.has_group('hr.group_hr_manager')

    @api.onchange('excuse_type')
    def _onchange_excuse_type(self):
        """Tự động điền request times khi thay đổi loại giải trình"""
        if not self.attendance_id:
            return

        self.requested_checkin = False
        self.requested_checkout = False

        if self.excuse_type in ['late_or_early', 'missing_checkin_out']:
            self.requested_checkin = self.original_checkin
            self.requested_checkout = self.original_checkout

    def _get_company_timezone(self):
        """Lấy timezone của công ty"""
        return pytz.timezone(self.env.user.tz or 'Asia/Ho_Chi_Minh')

    def _convert_to_local_time(self, dt):
        """Chuyển đổi datetime sang giờ địa phương"""
        if not dt:
            return None
        if dt.tzinfo is None:
            dt = pytz.UTC.localize(dt)
        tz = self._get_company_timezone()
        return dt.astimezone(tz)

    def _get_work_schedule(self, employee):
        """Lấy lịch làm việc của nhân viên"""
        default_schedule = {
            'start_time': 8.5,  # 8:30
            'end_time': 18.0,   # 18:00
            'late_tolerance': 0.25,  # 15 phút
        }

        if not employee:
            return default_schedule

        # Lấy calendar từ employee hoặc company
        calendar = employee.resource_calendar_id or employee.company_id.resource_calendar_id
        
        if not calendar:
            return default_schedule

        # Lấy attendance của thứ 2
        attendances = calendar.attendance_ids.filtered(lambda a: a.dayofweek == '0')
        
        if not attendances:
            attendances = calendar.attendance_ids
        
        if attendances:
            attendances = attendances.sorted(key=lambda a: a.hour_from)
            first, last = attendances[0], attendances[-1]
            
            return {
                'start_time': first.hour_from,
                'end_time': last.hour_to,
                'late_tolerance': 0.25,
            }
        
        return default_schedule

    def _check_monthly_limit(self, employee, excuse_type, date):
        """Kiểm tra giới hạn giải trình hàng tháng"""
        limit_config = self.env['attendance.excuse.limit'].search([
            ('excuse_type', '=', excuse_type),
            ('active', '=', True)
        ], limit=1)

        if not limit_config:
            return

        # Tính ngày đầu và cuối tháng
        month_start = date.replace(day=1)
        if date.month == 12:
            month_end = month_start.replace(year=date.year + 1, month=1) - timedelta(days=1)
        else:
            month_end = month_start.replace(month=date.month + 1) - timedelta(days=1)

        # Đếm giải trình đã duyệt và đang chờ duyệt
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
            ('state', '=', 'submitted'),
            ('date', '>=', month_start),
            ('date', '<=', month_end)
        ])

        total_count = approved_count + submitted_count

        if total_count >= limit_config.monthly_limit:
            excuse_label = dict(self._fields['excuse_type'].selection).get(excuse_type, excuse_type)
            raise ValidationError(
                f"Nhân viên {employee.name} đã vượt quá giới hạn giải trình \"{excuse_label}\" "
                f"({limit_config.monthly_limit} lần/tháng) trong tháng {date.month}/{date.year}. "
                f"Hiện tại: {total_count}/{limit_config.monthly_limit}"
            )

    @api.model
    def detect_and_create_excuses(self, target_date=None):
        """Tự động phát hiện và tạo giải trình chấm công"""
        if target_date is None:
            target_date = fields.Date.context_today(self)

        self._detect_late_arrival(target_date)
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
        """Phát hiện và tạo giải trình cho đi muộn/về sớm"""
        attendances = self.env['hr.attendance'].search([
            ('check_in', '>=', datetime.combine(target_date, datetime.min.time())),
            ('check_in', '<=', datetime.combine(target_date, datetime.max.time())),
            ('attendance_status', '=', 'late_or_early'),
            ('is_invalid_record', '=', False),
        ])

        for att in attendances:
            if not att.check_in or not att.check_out:
                continue

            # Kiểm tra giải trình đã tồn tại
            if self.search_count([('attendance_id', '=', att.id), ('excuse_type', '=', 'late_or_early')]):
                continue

            # Tính số phút chênh lệch
            local_checkin = self._convert_to_local_time(att.check_in)
            check_in_hour = local_checkin.hour + local_checkin.minute / 60.0
            schedule = self._get_work_schedule(att.employee_id)
            late_threshold = schedule['start_time'] + schedule['late_tolerance']

            if check_in_hour > late_threshold:
                late_minutes = int((check_in_hour - schedule['start_time']) * 60)
                self.create({
                    'attendance_id': att.id,
                    'late_minutes': late_minutes,
                    'state': 'draft',
                    'notes': f'Tự động phát hiện: Đi muộn {late_minutes} phút',
                })
            else:
                # Kiểm tra về sớm
                local_checkout = self._convert_to_local_time(att.check_out)
                check_out_hour = local_checkout.hour + local_checkout.minute / 60.0
                early_threshold = schedule['end_time']
                
                if check_out_hour < early_threshold:
                    early_minutes = int((early_threshold - check_out_hour) * 60)
                    self.create({
                        'attendance_id': att.id,
                        'early_minutes': early_minutes,
                        'state': 'draft',
                        'notes': f'Tự động phát hiện: Về sớm {early_minutes} phút',
                    })

    def _detect_missing_checkout(self, target_date):
        """Phát hiện và tạo giải trình cho thiếu check-out"""
        previous_date = target_date - timedelta(days=1)

        attendances = self.env['hr.attendance'].search([
            ('check_in', '>=', datetime.combine(previous_date, datetime.min.time())),
            ('check_in', '<=', datetime.combine(previous_date, datetime.max.time())),
            ('check_out', '=', False),
            ('is_invalid_record', '=', False),
        ])

        for att in attendances:
            if not self.search_count([('attendance_id', '=', att.id), ('excuse_type', '=', 'missing_checkin_out')]):
                self.create({
                    'attendance_id': att.id,
                    'state': 'draft',
                    'notes': 'Tự động phát hiện: Thiếu chấm công',
                })

    def action_submit(self):
        """Gửi giải trình để duyệt (UI action)"""
        for record in self:
            record._submit()

    def _submit(self):
        """Internal: thực hiện submit giải trình"""
        if self.state != 'draft':
            raise UserError(f'Chỉ có thể gửi ở trạng thái draft, hiện tại là {self.state}')

        if self.employee_id and self.date and self.excuse_type:
            self._check_monthly_limit(self.employee_id, self.excuse_type, self.date)

        # Gán người phê duyệt
        if not self.approver_id and self.employee_id:
            if self.employee_id.attendance_manager_id:
                self.approver_id = self.employee_id.attendance_manager_id.user_id.id
            elif self.employee_id.parent_id and self.employee_id.parent_id.user_id:
                self.approver_id = self.employee_id.parent_id.user_id.id

        self.state = 'submitted'
        self.message_post(body="Yêu cầu giải trình đã được gửi")

    def action_approve(self):
        """Phê duyệt giải trình"""
        for record in self:
            if record.state != 'submitted':
                continue

            if record.approver_id and record.approver_id.id != self.env.user.id:
                if not self.env.user.has_group('hr.group_hr_manager'):
                    raise UserError('Bạn không có quyền phê duyệt đơn này')

            record.write({
                'state': 'approved',
                'approver_id': self.env.user.id,
                'approval_date': fields.Datetime.now(),
            })

            # Cập nhật attendance nếu có requested times
            if record.attendance_id:
                att = record.attendance_id
                if record.corrected_checkin or record.requested_checkin:
                    att.check_in = record.corrected_checkin or record.requested_checkin
                    if not record.corrected_checkin:
                        record.corrected_checkin = record.requested_checkin
                
                if record.corrected_checkout or record.requested_checkout:
                    att.check_out = record.corrected_checkout or record.requested_checkout
                    if not record.corrected_checkout:
                        record.corrected_checkout = record.requested_checkout

            record.message_post(body=f"Yêu cầu giải trình đã được phê duyệt bởi {self.env.user.name}")

    def action_reject(self):
        """Từ chối giải trình"""
        for record in self:
            if record.state != 'submitted':
                continue

            if record.approver_id and record.approver_id.id != self.env.user.id:
                if not self.env.user.has_group('hr.group_hr_manager'):
                    raise UserError('Bạn không có quyền từ chối đơn này')

            record.write({
                'state': 'rejected',
                'approver_id': self.env.user.id,
                'approval_date': fields.Datetime.now(),
            })

            record.message_post(body=f"Yêu cầu giải trình đã bị từ chối bởi {self.env.user.name}")

    def action_reset_to_draft(self):
        """Reset về trạng thái draft"""
        for record in self:
            record.state = 'draft'

    def get_my_requests(self):
        """Lấy các yêu cầu của user hiện tại"""
        return self.search([('employee_id.user_id', '=', self.env.user.id)], order='date desc')

    def get_pending_approvals(self):
        """Lấy các yêu cầu chờ duyệt"""
        return self.search([('state', '=', 'submitted')], order='date desc')

    def write(self, values):
        """Override: cho phép update chỉ khi ở draft"""
        for record in self:
            if record.state != 'draft':
                # Cho phép update state, approver_id, approval_date (từ action_approve/reject)
                allowed_fields = {'state', 'approver_id', 'approval_date', 'rejection_reason'}
                update_fields = set(values.keys())
                
                if not update_fields.issubset(allowed_fields):
                    raise UserError(f'Chỉ có thể sửa ở trạng thái draft, hiện tại là {record.state}')
        
        return super().write(values)

    def unlink(self):
        """Override: cho phép xóa chỉ khi ở draft"""
        for record in self:
            if record.state != 'draft':
                raise UserError(f'Chỉ có thể xóa ở trạng thái draft, hiện tại là {record.state}')
        
        return super().unlink()

    @api.model
    def api_create_excuse(self, data, user_id):
        """API: Tạo giải trình chấm công"""
        # Validate dữ liệu bắt buộc
        required_fields = ['attendance_id', 'excuse_type']
        for field in required_fields:
            if not data.get(field):
                raise UserError(f'{field} là bắt buộc')

        current_user = self.env['res.users'].browse(user_id)
        if not current_user.exists():
            raise UserError('User không tồn tại')

        current_employee = current_user.employee_id
        if not current_employee:
            raise UserError('User không phải là nhân viên')

        # Validate attendance
        attendance = self.env['hr.attendance'].browse(data['attendance_id'])
        if not attendance.exists():
            raise UserError('Không tìm thấy bản ghi chấm công')

        # Kiểm tra quyền
        can_create = (current_user.has_group('base.group_system') or
                     current_user.has_group('hr.group_hr_manager') or
                     current_employee.id == attendance.employee_id.id)

        if not can_create:
            raise UserError('Không có quyền tạo giải trình cho nhân viên khác')

        # Validate excuse_type
        if data['excuse_type'] not in ['late_or_early', 'missing_checkin_out']:
            raise UserError('excuse_type không hợp lệ')

        # Tạo excuse
        excuse_vals = {
            'attendance_id': data['attendance_id'],
            'excuse_type': data['excuse_type'],
            'reason': data.get('reason', ''),
            'requested_checkin': data.get('requested_checkin'),
            'requested_checkout': data.get('requested_checkout'),
        }

        excuse = self.create(excuse_vals)

        return {
            'id': excuse.id,
            'attendance_id': excuse.attendance_id.id,
            'employee_id': excuse.employee_id.id,
            'employee_name': excuse.employee_id.name,
            'excuse_type': excuse.excuse_type,
            'state': excuse.state,
            'reason': excuse.reason,
            'requested_checkin': excuse.requested_checkin.isoformat() if excuse.requested_checkin else None,
            'requested_checkout': excuse.requested_checkout.isoformat() if excuse.requested_checkout else None,
        }

    @api.model
    def api_get_my_excuse_list(self, user_id, limit=10, offset=0, state=None):
        """API: Lấy danh sách giải trình của user"""
        current_user = self.env['res.users'].browse(user_id)
        if not current_user.exists():
            raise UserError('User không tồn tại')

        current_employee = current_user.employee_id
        if not current_employee:
            raise UserError('User không phải là nhân viên')

        domain = [('employee_id', '=', current_employee.id)]
        if state:
            domain.append(('state', '=', state))

        excuses = self.search(domain, limit=limit, offset=offset, order='date desc')
        total_count = self.search_count(domain)

        excuse_data = []
        for excuse in excuses:
            excuse_data.append({
                'id': excuse.id,
                'attendance_id': excuse.attendance_id.id,
                'employee_id': excuse.employee_id.id,
                'employee_name': excuse.employee_id.name,
                'date': excuse.date.isoformat() if excuse.date else None,
                'excuse_type': excuse.excuse_type,
                'state': excuse.state,
                'reason': excuse.reason,
                'original_checkin': excuse.original_checkin.isoformat() if excuse.original_checkin else None,
                'original_checkout': excuse.original_checkout.isoformat() if excuse.original_checkout else None,
                'requested_checkin': excuse.requested_checkin.isoformat() if excuse.requested_checkin else None,
                'requested_checkout': excuse.requested_checkout.isoformat() if excuse.requested_checkout else None,
            })

        return {
            'excuses': excuse_data,
            'total_count': total_count,
            'limit': limit,
            'offset': offset,
        }

    def api_get_excuse_detail(self, user_id):
        """API: Lấy chi tiết giải trình"""
        current_user = self.env['res.users'].browse(user_id)
        if not current_user.exists():
            raise UserError('User không tồn tại')

        current_employee = current_user.employee_id

        # Kiểm tra quyền
        can_view = (current_user.has_group('base.group_system') or
                   current_user.has_group('hr.group_hr_manager') or
                   (current_employee and current_employee.id == self.employee_id.id))

        if not can_view:
            raise UserError('Không có quyền xem thông tin này')

        return {
            'id': self.id,
            'attendance_id': self.attendance_id.id,
            'employee_id': self.employee_id.id,
            'employee_name': self.employee_id.name,
            'date': self.date.isoformat() if self.date else None,
            'excuse_type': self.excuse_type,
            'state': self.state,
            'reason': self.reason,
            'original_checkin': self.original_checkin.isoformat() if self.original_checkin else None,
            'original_checkout': self.original_checkout.isoformat() if self.original_checkout else None,
            'requested_checkin': self.requested_checkin.isoformat() if self.requested_checkin else None,
            'requested_checkout': self.requested_checkout.isoformat() if self.requested_checkout else None,
        }

    def api_submit_excuse(self, user_id):
        """API: Submit giải trình để duyệt"""
        current_user = self.env['res.users'].browse(user_id)
        if not current_user.exists():
            raise UserError('User không tồn tại')

        current_employee = current_user.employee_id

        # Kiểm tra quyền
        can_submit = (current_user.has_group('base.group_system') or
                     current_user.has_group('hr.group_hr_manager') or
                     (current_employee and current_employee.id == self.employee_id.id))

        if not can_submit:
            raise UserError('Không có quyền submit giải trình này')

        self._submit()

        return {
            'id': self.id,
            'state': self.state,
        }

    def api_approve_excuse(self, user_id, corrected_checkin=None, corrected_checkout=None):
        """API: Phê duyệt giải trình"""
        current_user = self.env['res.users'].browse(user_id)
        if not current_user.exists():
            raise UserError('User không tồn tại')

        # Kiểm tra trạng thái
        if self.state != 'submitted':
            raise UserError(f'Chỉ có thể phê duyệt giải trình ở trạng thái submitted, hiện tại là {self.state}')

        # Kiểm tra quyền phê duyệt
        can_approve = (current_user.has_group('base.group_system') or
                      current_user.has_group('hr.group_hr_manager') or
                      (self.approver_id and self.approver_id.id == current_user.id))

        if not can_approve:
            raise UserError('Không có quyền phê duyệt giải trình này')

        # Cập nhật corrected times nếu được cung cấp
        update_values = {
            'state': 'approved',
            'approver_id': current_user.id,
            'approval_date': fields.Datetime.now(),
        }

        if corrected_checkin:
            update_values['corrected_checkin'] = corrected_checkin
        
        if corrected_checkout:
            update_values['corrected_checkout'] = corrected_checkout

        self.write(update_values)

        # Cập nhật attendance nếu có corrected times
        if self.attendance_id:
            att_update = {}
            if self.corrected_checkin:
                att_update['check_in'] = self.corrected_checkin
            if self.corrected_checkout:
                att_update['check_out'] = self.corrected_checkout
            
            if att_update:
                self.attendance_id.write(att_update)

        self.message_post(body=f"Yêu cầu giải trình đã được phê duyệt bởi {current_user.name}")

        return {
            'id': self.id,
            'state': self.state,
            'approver_id': self.approver_id.id,
            'approver_name': self.approver_id.name,
            'approval_date': self.approval_date.isoformat() if self.approval_date else None,
        }

    def api_reject_excuse(self, user_id, rejection_reason=''):
        """API: Từ chối giải trình"""
        current_user = self.env['res.users'].browse(user_id)
        if not current_user.exists():
            raise UserError('User không tồn tại')

        # Kiểm tra trạng thái
        if self.state != 'submitted':
            raise UserError(f'Chỉ có thể từ chối giải trình ở trạng thái submitted, hiện tại là {self.state}')

        # Kiểm tra quyền từ chối
        can_reject = (current_user.has_group('base.group_system') or
                     current_user.has_group('hr.group_hr_manager') or
                     (self.approver_id and self.approver_id.id == current_user.id))

        if not can_reject:
            raise UserError('Không có quyền từ chối giải trình này')

        update_values = {
            'state': 'rejected',
            'approver_id': current_user.id,
            'approval_date': fields.Datetime.now(),
        }

        if rejection_reason:
            update_values['rejection_reason'] = rejection_reason

        self.write(update_values)
        self.message_post(body=f"Yêu cầu giải trình đã bị từ chối bởi {current_user.name}. Lý do: {rejection_reason if rejection_reason else 'Không cung cấp'}")

        return {
            'id': self.id,
            'state': self.state,
            'approver_id': self.approver_id.id,
            'approver_name': self.approver_id.name,
            'approval_date': self.approval_date.isoformat() if self.approval_date else None,
            'rejection_reason': self.rejection_reason,
        }

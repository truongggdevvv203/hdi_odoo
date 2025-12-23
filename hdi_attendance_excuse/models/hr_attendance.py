from odoo import models, fields, api
import pytz


class HRAttendance(models.Model):
    _inherit = 'hr.attendance'

    excuse_ids = fields.One2many(
        'attendance.excuse',
        'attendance_id',
        string='Giải trình'
    )

    is_excused = fields.Boolean(
        string='Đã giải trình',
        compute='_compute_is_excused',
        store=True
    )

    has_pending_excuse = fields.Boolean(
        string='Có giải trình chờ xử lý',
        compute='_compute_has_pending_excuse',
        store=True
    )

    requires_excuse = fields.Boolean(
        string='Cần giải trình',
        compute='_compute_requires_excuse',
        store=False
    )

    is_invalid_record = fields.Boolean(
        string='Chấm công hợp lệ',
        compute='_compute_is_invalid_record',
        store=True,
        default=True
    )

    attendance_status = fields.Selection(
        [
            ('valid', 'Chấm công hợp lệ'),
            ('late_or_early', 'Đi muộn/về sớm'),
            ('excuse_rejected', 'Từ chối giải trình'),
            ('pending_excuse_approval', 'Đang chờ duyệt giải trình'),
            ('excuse_approved', 'Hoàn thành phê duyệt'),
        ],
        string='Trạng thái chấm công',
        compute='_compute_attendance_status',
        store=True,
        help='Trạng thái chi tiết của bản ghi chấm công'
    )

    @api.depends('excuse_ids', 'excuse_ids.state')
    def _compute_is_excused(self):
        for record in self:
            record.is_excused = any(e.state == 'approved' for e in record.excuse_ids)

    @api.depends('excuse_ids', 'excuse_ids.state')
    def _compute_has_pending_excuse(self):
        for record in self:
            record.has_pending_excuse = any(e.state in ['submitted', 'pending'] for e in record.excuse_ids)

    @api.depends('excuse_ids', 'excuse_ids.state', 'check_in', 'check_out', 'out_mode')
    def _compute_requires_excuse(self):
        for record in self:
            requires = False

            # Bỏ qua bản ghi của ngày hôm nay
            if record.check_in:
                check_in_local = record._convert_to_local_time(record.check_in)
                check_in_date = check_in_local.date()
                today = fields.Date.context_today(record)
                if check_in_date == today:
                    record.requires_excuse = False
                    continue

            # Check if there are any submitted excuses
            if any(e.state in ['submitted'] for e in record.excuse_ids):
                requires = True

            # Lấy cấu hình giờ làm việc theo phòng ban
            schedule = record._get_work_schedule(record.employee_id)

            # Tính toán giải trình cho tất cả các loại out_mode (manual, auto, etc.)
            if record.check_in:
                ci = record._convert_to_local_time(record.check_in)
                check_in_hour = ci.hour + ci.minute / 60.0
                late_threshold = schedule['start_time'] + schedule['late_tolerance']
                if check_in_hour > late_threshold:
                    requires = True

            if record.check_out:
                co = record._convert_to_local_time(record.check_out)
                check_out_hour = co.hour + co.minute / 60.0
                early_threshold = schedule['end_time']
                if check_out_hour < early_threshold:
                    requires = True

            if record.check_in and not record.check_out:
                requires = True

            record.requires_excuse = requires

    @api.depends('check_in', 'check_out')
    def _compute_is_invalid_record(self):
        """
        Kiểm tra bản ghi hợp lệ/không hợp lệ dựa trên check-in và check-out
        True: Hợp lệ | False: Không hợp lệ
        Bỏ qua các bản ghi của ngày hôm nay
        Tự động cập nhật khi dữ liệu trong DB thay đổi
        """
        for record in self:
            is_valid = True

            # Bỏ qua bản ghi của ngày hôm nay
            if record.check_in:
                check_in_local = record._convert_to_local_time(record.check_in)
                check_in_date = check_in_local.date()
                today = fields.Date.context_today(record)
                if check_in_date == today:
                    record.is_invalid_record = True
                    continue

            # Kiểm tra các trường hợp không hợp lệ
            if record.check_in and record.check_out:
                # Check-out phải sau check-in
                if record.check_out <= record.check_in:
                    is_valid = False

                # Kiểm tra khoảng thời gian quá dài (vượt quá 24 giờ)
                time_diff = (record.check_out - record.check_in).total_seconds() / 3600
                if time_diff > 24:
                    is_valid = False

                # Kiểm tra auto-checkout tại midnight (23:59:59)
                co = record._convert_to_local_time(record.check_out)
                if co.hour == 23 and co.minute == 59 and co.second == 59:
                    is_valid = False

            # Không có check-in (bản ghi không đầy đủ)
            elif not record.check_in:
                is_valid = False

            # Có check-in nhưng không có check-out (đối với ngày cũ)
            elif record.check_in and not record.check_out:
                is_valid = False

            record.is_invalid_record = is_valid

    def _get_company_timezone(self):
        """Lấy timezone của công ty/user"""
        return pytz.timezone(self.env.user.tz or 'Asia/Ho_Chi_Minh')

    def _convert_to_local_time(self, dt):
        """Chuyển đổi datetime sang local time"""
        if not dt:
            return None
        if dt.tzinfo is None:
            dt = pytz.UTC.localize(dt)
        tz = self._get_company_timezone()
        return dt.astimezone(tz)

    def _get_work_schedule(self, employee):
        """
        Lấy lịch làm việc từ resource.calendar của nhân viên
        Trả về start_time, end_time và late_tolerance
        """
        # Giá trị mặc định
        default_schedule = {
            'start_time': 8.5,  # 8:30
            'end_time': 18.0,   # 18:00
            'late_tolerance': 0.25,  # 15 phút
        }

        if not employee:
            return default_schedule

        # Lấy calendar từ employee
        calendar = employee.resource_calendar_id
        if not calendar:
            # Nếu không có calendar riêng, lấy calendar của company
            calendar = employee.company_id.resource_calendar_id
        
        if not calendar:
            return default_schedule

        # Lấy giờ làm việc từ calendar attendance (thường là thứ 2)
        # Tìm attendance đầu tiên (có thể có nhiều ca trong ngày)
        attendance = calendar.attendance_ids.filtered(lambda a: a.dayofweek == '0')[:1]  # 0 = Monday
        
        if not attendance:
            # Nếu không có thứ 2, lấy bất kỳ ngày nào
            attendance = calendar.attendance_ids[:1]
        
        if attendance:
            # hour_from và hour_to đã là float (8.5 = 8:30)
            return {
                'start_time': attendance.hour_from,
                'end_time': attendance.hour_to,
                'late_tolerance': 0.25,  # 15 phút - có thể config sau
            }
        
        return default_schedule

    @api.depends('check_in', 'check_out', 'excuse_ids', 'excuse_ids.state', 'is_invalid_record')
    def _compute_attendance_status(self):
        for record in self:
            status = 'valid'

            # Bỏ qua bản ghi của ngày hôm nay
            if record.check_in:
                check_in_local = record._convert_to_local_time(record.check_in)
                check_in_date = check_in_local.date()
                today = fields.Date.context_today(record)
                if check_in_date == today:
                    record.attendance_status = status
                    continue

            # 1. Kiểm tra bản ghi không hợp lệ (is_invalid_record = False)
            if not record.is_invalid_record:
                status = 'missing_checkin_out'
            # 2. Kiểm tra có giải trình bị từ chối
            elif any(e.state == 'rejected' for e in record.excuse_ids):
                status = 'excuse_rejected'
            # 3. Kiểm tra có giải trình đang chờ duyệt
            elif any(e.state in ['submitted', 'pending'] for e in record.excuse_ids):
                status = 'pending_excuse_approval'
            # 4. Kiểm tra có giải trình đã được duyệt
            elif any(e.state == 'approved' for e in record.excuse_ids):
                status = 'excuse_approved'
            # 5. Kiểm tra đi muộn/về sớm
            elif record.check_in and record.check_out:
                schedule = record._get_work_schedule(record.employee_id)
                is_late_or_early = False

                ci = record._convert_to_local_time(record.check_in)
                check_in_hour = ci.hour + ci.minute / 60.0
                late_threshold = schedule['start_time'] + schedule['late_tolerance']
                if check_in_hour > late_threshold:
                    is_late_or_early = True

                if not is_late_or_early:
                    co = record._convert_to_local_time(record.check_out)
                    check_out_hour = co.hour + co.minute / 60.0
                    early_threshold = schedule['end_time']
                    if check_out_hour < early_threshold:
                        is_late_or_early = True

                if is_late_or_early:
                    status = 'late_or_early'

            record.attendance_status = status

    @api.model
    def create_missing_checkout_excuses(self):
        AttendanceExcuse = self.env['attendance.excuse']

        attendances = self.search([
            ('check_in', '!=', False),
            ('check_out', '!=', False),
        ])

        for att in attendances:
            existing = AttendanceExcuse.search([
                ('attendance_id', '=', att.id),
                ('excuse_type', '=', 'missing_checkout'),
            ], limit=1)

            if not existing:
                co = att._convert_to_local_time(att.check_out)
                if co.hour == 23 and co.minute == 59 and co.second == 59:
                    AttendanceExcuse.create({
                        'attendance_id': att.id,
                        'state': 'draft',
                        'notes': 'Tự động phát hiện: Quên check-out (auto-checkout tại midnight)',
                    })
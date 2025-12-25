from odoo import models, fields, api
from odoo.exceptions import UserError
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
            ('missing_checkin_out', 'Thiếu chấm công'),
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

    @api.depends('excuse_ids', 'excuse_ids.state', 'check_in', 'check_out', 'out_mode', 'employee_id',
                 'employee_id.resource_calendar_id', 'employee_id.company_id.resource_calendar_id')
    def _compute_requires_excuse(self):
        for record in self:
            requires = False

            # Check if there are any submitted excuses
            if any(e.state in ['submitted'] for e in record.excuse_ids):
                requires = True

            # Kiểm tra đi muộn/về sớm → cần giải trình
            if record._is_late_or_early():
                requires = True

            record.requires_excuse = requires

    @api.depends('check_in', 'check_out', 'employee_id', 'employee_id.resource_calendar_id',
                 'employee_id.company_id.resource_calendar_id')
    def _compute_is_invalid_record(self):
        for record in self:
            # Nếu chưa check-out, coi là hợp lệ (user chưa hết ngày làm việc)
            if record.check_in and not record.check_out:
                record.is_invalid_record = True
                continue

            # 1. Check-out phải sau check-in
            if record.check_out and record.check_out <= record.check_in:
                record.is_invalid_record = False
                continue

            # 2. Kiểm tra khoảng thời gian quá dài (vượt quá 24 giờ)
            if record.check_out and (record.check_out - record.check_in).total_seconds() / 3600 > 24:
                record.is_invalid_record = False
                continue

            # 3. Kiểm tra auto-checkout tại midnight (23:59:59)
            if record.check_out:
                co = record._convert_to_local_time(record.check_out)
                if co.hour == 23 and co.minute == 59 and co.second == 59:
                    record.is_invalid_record = False
                    continue

            # 4. Kiểm tra đi muộn/về sớm quá tolerance → không hợp lệ
            if record._is_late_or_early():
                record.is_invalid_record = False
                continue

            record.is_invalid_record = True

    def _is_late_or_early(self):
        if not self.check_in or not self.check_out:
            return False

        schedule = self._get_work_schedule(self.employee_id)

        ci = self._convert_to_local_time(self.check_in)
        check_in_hour = ci.hour + ci.minute / 60.0 + ci.second / 3600.0
        late_threshold = schedule['start_time'] + schedule['late_tolerance']

        if check_in_hour > late_threshold:
            return True

        co = self._convert_to_local_time(self.check_out)
        check_out_hour = co.hour + co.minute / 60.0 + co.second / 3600.0
        early_threshold = schedule['end_time'] - schedule['early_tolerance']

        if check_out_hour < early_threshold:
            return True

        return False

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
        default_schedule = {
            'start_time': 8.5,
            'end_time': 18.0,
            'late_tolerance': 0.25,
            'early_tolerance': 0.25,
        }

        if not employee or not self.check_in:
            return default_schedule

        calendar = employee.resource_calendar_id
        if not calendar:
            calendar = employee.company_id.resource_calendar_id

        if not calendar:
            return default_schedule

        check_in_local = self._convert_to_local_time(self.check_in)
        day_of_week = str(check_in_local.weekday())

        attendance_today = calendar.attendance_ids.filtered(lambda a: a.dayofweek == day_of_week)

        if not attendance_today:
            return default_schedule

        attendance_today = attendance_today.sorted(key=lambda a: a.hour_from)

        first_attendance = attendance_today[0]
        last_attendance = attendance_today[-1]

        return {
            'start_time': first_attendance.hour_from,
            'end_time': last_attendance.hour_to,
            'late_tolerance': 0.25,
            'early_tolerance': 0.25,
        }

    @api.depends('check_in', 'check_out', 'excuse_ids', 'excuse_ids.state', 'is_invalid_record', 'employee_id',
                 'employee_id.resource_calendar_id', 'employee_id.company_id.resource_calendar_id')
    def _compute_attendance_status(self):
        for record in self:
            status = 'valid'

            if not record.is_invalid_record:
                # Bản ghi không hợp lệ - check giải trình
                if any(e.state == 'rejected' for e in record.excuse_ids):
                    status = 'excuse_rejected'
                elif any(e.state in ['submitted', 'pending'] for e in record.excuse_ids):
                    status = 'pending_excuse_approval'
                elif any(e.state == 'approved' for e in record.excuse_ids):
                    status = 'excuse_approved'
                elif record._is_late_or_early():
                    status = 'late_or_early'
                else:
                    status = 'valid'
            else:
                # Bản ghi hợp lệ
                status = 'valid'

            record.attendance_status = status

    @api.model
    def api_check_in(self, employee_id, in_latitude=None, in_longitude=None):
        """
        API method cho check-in
        Kiểm tra và tạo attendance record
        """
        # Kiểm tra xem đã check-in chưa
        last_attendance = self.search([
            ('employee_id', '=', employee_id),
            ('check_out', '=', False)
        ], limit=1)

        if last_attendance:
            raise UserError(
                'Bạn đã chấm công vào rồi. Vui lòng chấm công ra trước khi chấm công vào lại.'
            )

        # Tạo dữ liệu cho attendance record
        attendance_data = {
            'employee_id': employee_id,
            'check_in': fields.Datetime.now(),
            'in_mode': 'manual',
        }

        # Thêm GPS coordinates nếu có
        if in_latitude:
            try:
                attendance_data['in_latitude'] = float(in_latitude)
            except (ValueError, TypeError):
                pass

        if in_longitude:
            try:
                attendance_data['in_longitude'] = float(in_longitude)
            except (ValueError, TypeError):
                pass

        # Tạo bản ghi chấm công
        attendance = self.sudo().create(attendance_data)

        return {
            'id': attendance.id,
            'employee_id': attendance.employee_id.id,
            'employee_name': attendance.employee_id.name,
            'check_in': attendance.check_in.isoformat() if attendance.check_in else None,
            'in_latitude': attendance.in_latitude,
            'in_longitude': attendance.in_longitude,
        }

    @api.model
    def api_check_out(self, employee_id, out_latitude=None, out_longitude=None):
        """
        API method cho check-out
        Kiểm tra và cập nhật attendance record
        """
        import logging
        _logger = logging.getLogger(__name__)
        
        # Tìm bản ghi chấm công chưa check-out
        attendance = self.search([
            ('employee_id', '=', employee_id),
            ('check_out', '=', False)
        ], limit=1, order='check_in desc')

        if not attendance:
            raise UserError(
                'Không tìm thấy bản ghi chấm công vào. Vui lòng chấm công vào trước.'
            )

        # Kiểm tra và xóa overtime record cũ nếu tồn tại
        if attendance.check_in:
            attendance_date = attendance.check_in.date()
            old_overtime = self.env['hr.attendance.overtime'].search([
                ('employee_id', '=', employee_id),
                ('date', '=', str(attendance_date))
            ])
            if old_overtime:
                old_overtime.unlink()

        # Tạo dữ liệu cập nhật
        update_data = {
            'check_out': fields.Datetime.now(),
            'out_mode': 'manual',
        }

        # Thêm GPS coordinates nếu có
        _logger.info(f"GPS params: out_latitude={out_latitude}, out_longitude={out_longitude}")
        if out_latitude:
            try:
                update_data['out_latitude'] = float(out_latitude)
                _logger.info(f"Added out_latitude: {float(out_latitude)}")
            except (ValueError, TypeError) as e:
                _logger.error(f"Error converting out_latitude: {e}")
                pass

        if out_longitude:
            try:
                update_data['out_longitude'] = float(out_longitude)
                _logger.info(f"Added out_longitude: {float(out_longitude)}")
            except (ValueError, TypeError) as e:
                _logger.error(f"Error converting out_longitude: {e}")
                pass

        _logger.info(f"Update data before write: {update_data}")
        
        # Cập nhật check-out
        attendance.sudo().write(update_data)

        # Re-fetch record để lấy giá trị mới nhất từ database
        attendance = self.browse(attendance.id).sudo()
        
        _logger.info(f"After write - out_latitude: {attendance.out_latitude}, out_longitude: {attendance.out_longitude}")

        return {
            'id': attendance.id,
            'employee_id': attendance.employee_id.id,
            'employee_name': attendance.employee_id.name,
            'check_in': attendance.check_in.isoformat() if attendance.check_in else None,
            'check_out': attendance.check_out.isoformat() if attendance.check_out else None,
            'in_latitude': attendance.in_latitude,
            'in_longitude': attendance.in_longitude,
            'out_latitude': attendance.out_latitude,
            'out_longitude': attendance.out_longitude,
            'worked_hours': attendance.worked_hours if hasattr(attendance, 'worked_hours') else 0,
        }

    @api.model
    def auto_checkout_at_midnight(self):
        import datetime

        today = fields.Date.context_today(self)

        employees = self.env['hr.employee'].search([])

        for employee in employees:
            attendance = self.search([
                ('employee_id', '=', employee.id),
                ('check_in', '>=', datetime.datetime.combine(today, datetime.time.min)),
                ('check_in', '<=', datetime.datetime.combine(today, datetime.time.max)),
                ('check_out', '=', False),
            ], limit=1)

            if attendance:
                company = employee.company_id or self.env.company
                tz = pytz.timezone(company.partner_id.tz or 'Asia/Ho_Chi_Minh')

                local_midnight = tz.localize(datetime.datetime.combine(today, datetime.time(23, 59, 59)))

                utc_checkout = local_midnight.astimezone(pytz.UTC).replace(tzinfo=None)

                attendance.check_out = utc_checkout

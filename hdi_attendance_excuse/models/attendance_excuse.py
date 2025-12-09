from odoo import models, fields, api
from datetime import datetime, timedelta
import pytz


class AttendanceExcuse(models.Model):
  """
    Giải trình chấm công - Hệ thống quản lý các trường hợp cần giải trình
    Hỗ trợ cả tự động phát hiện và yêu cầu giải trình từ nhân viên
    """
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
        check_in_date = fields.Datetime.context_timestamp(self, self.attendance_id.check_in).date()
        self.date = check_in_date

  excuse_type = fields.Selection([
    ('late', 'Đi muộn'),
    ('early', 'Về sớm'),
    ('missing_checkin', 'Quên check-in'),
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
    """Kiểm tra xem user hiện tại có thể phê duyệt không"""
    for record in self:
      if record.state != 'submitted':
        record.can_approve = False
      elif not record.approver_id:
        record.can_approve = True  # Nếu không có approver được chỉ định, ai cũng có thể phê duyệt
      elif record.approver_id.id == self.env.user.id:
        record.can_approve = True  # Người phê duyệt được chỉ định
      else:
        # Chỉ HR Manager có thể phê duyệt nếu không phải người được chỉ định
        record.can_approve = self.env.user.has_group('hr.group_hr_manager')

  @api.depends('approver_id', 'state')
  def _compute_can_reject(self):
    """Kiểm tra xem user hiện tại có thể từ chối không"""
    for record in self:
      if record.state != 'submitted':
        record.can_reject = False
      elif not record.approver_id:
        record.can_reject = True  # Nếu không có approver được chỉ định, ai cũng có thể từ chối
      elif record.approver_id.id == self.env.user.id:
        record.can_reject = True  # Người phê duyệt được chỉ định
      else:
        # Chỉ HR Manager có thể từ chối nếu không phải người được chỉ định
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
    """Lấy check-in/check-out gốc từ hr.attendance"""
    for record in self:
      if record.attendance_id:
        record.original_checkin = record.attendance_id.check_in
        record.original_checkout = record.attendance_id.check_out
      else:
        record.original_checkin = False
        record.original_checkout = False

  @api.depends('original_checkin', 'original_checkout', 'attendance_id')
  def _compute_excuse_type(self):
    """Tự động xác định loại giải trình dựa trên thời gian gốc"""
    for record in self:
      excuse_type = 'late'  # Default fallback

      if not record.attendance_id:
        record.excuse_type = 'missing_checkin'  # Default for no attendance
        continue

      # Nếu không có check-in
      if not record.original_checkin:
        record.excuse_type = 'missing_checkin'
        continue

      # Nếu không có check-out
      if not record.original_checkout:
        record.excuse_type = 'missing_checkout'
        continue

      # Kiểm tra đi muộn
      local_checkin = self._convert_to_local_time(record.original_checkin)
      check_in_hour = local_checkin.hour + local_checkin.minute / 60.0
      schedule = self._get_work_schedule(record.employee_id)

      if check_in_hour > (schedule['start_time'] + schedule['late_tolerance']):
        record.excuse_type = 'late'
        continue

      # Kiểm tra về sớm
      local_checkout = self._convert_to_local_time(record.original_checkout)
      check_out_hour = local_checkout.hour + local_checkout.minute / 60.0

      if check_out_hour < schedule['end_time']:
        record.excuse_type = 'early'
        continue

      # Nếu không phù hợp các điều kiện trên, mặc định là late
      # (có thể là trường hợp đặc biệt cần giải trình)
      record.excuse_type = 'late'

  def _get_company_timezone(self):
    """Lấy timezone của công ty"""
    return pytz.timezone(self.env.user.tz or 'Asia/Ho_Chi_Minh')

  def _convert_to_local_time(self, dt):
    """Chuyển đổi UTC sang giờ địa phương"""
    if not dt:
      return None
    if dt.tzinfo is None:
      dt = pytz.UTC.localize(dt)
    tz = self._get_company_timezone()
    return dt.astimezone(tz)

  def _get_work_schedule(self, employee):
    """
        Lấy lịch làm việc của nhân viên
        Có thể mở rộng để lấy từ resource.calendar
        """
    # Mặc định: 8:30 AM - 5:00 PM
    return {
      'start_time': 8.5,  # 8:30 AM
      'end_time': 18.0,  # 5:00 PM
      'late_tolerance': 0.25,  # 15 phút (0.25 giờ)
    }

  @api.model
  def detect_and_create_excuses(self, target_date=None):
    """
        Tự động phát hiện các trường hợp cần giải trình từ chấm công

        Args:
            target_date: Ngày cần kiểm tra (mặc định là hôm nay)
        """
    if target_date is None:
      target_date = fields.Date.context_today(self)

    # Kiểm tra các trường hợp
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
    """Phát hiện trường hợp đi muộn"""

    # Tìm tất cả bản ghi chấm công trong ngày
    attendances = self.env['hr.attendance'].search([
      ('check_in', '>=', datetime.combine(target_date, datetime.min.time())),
      ('check_in', '<=', datetime.combine(target_date, datetime.max.time())),
    ])

    for att in attendances:
      if not att.check_in:
        continue

      # Kiểm tra xem đã có giải trình chưa
      existing = self.search([
        ('attendance_id', '=', att.id),
        ('excuse_type', '=', 'late'),
      ], limit=1)

      if existing:
        continue

      # Chuyển sang giờ địa phương
      local_checkin = self._convert_to_local_time(att.check_in)
      check_in_hour = local_checkin.hour + local_checkin.minute / 60.0

      # Lấy lịch làm việc
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
    """Phát hiện trường hợp về sớm"""

    attendances = self.env['hr.attendance'].search([
      ('check_in', '>=', datetime.combine(target_date, datetime.min.time())),
      ('check_in', '<=', datetime.combine(target_date, datetime.max.time())),
      ('check_out', '!=', False),
    ])

    for att in attendances:
      if not att.check_out:
        continue

      # Kiểm tra đã có giải trình chưa
      existing = self.search([
        ('attendance_id', '=', att.id),
        ('excuse_type', '=', 'early'),
      ], limit=1)

      if existing:
        continue

      # Chuyển sang giờ địa phương
      local_checkout = self._convert_to_local_time(att.check_out)
      check_out_hour = local_checkout.hour + local_checkout.minute / 60.0

      # Lấy lịch làm việc
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
    """
        Phát hiện trường hợp quên check-out
        Kiểm tra attendance từ ngày trước
        """
    # Kiểm tra ngày hôm trước
    previous_date = target_date - timedelta(days=1)

    attendances = self.env['hr.attendance'].search([
      ('check_in', '>=', datetime.combine(previous_date, datetime.min.time())),
      ('check_in', '<=', datetime.combine(previous_date, datetime.max.time())),
      ('check_out', '=', False),
    ])

    for att in attendances:
      # Kiểm tra đã có giải trình chưa
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
    """Gửi yêu cầu giải trình"""
    for record in self:
      if record.state not in ['draft', 'pending']:
        continue

      # If no approver set, try to assign based on config or employee's manager
      if not record.approver_id and record.employee_id:
        # Priority 1: Lookup from attendance.excuse.approver.config
        approver_config = self.env['attendance.excuse.approver.config'].search([
          ('department_id', '=', record.employee_id.department_id.id),
          ('active', '=', True)
        ], limit=1)

        if approver_config:
          record.approver_id = approver_config.approver_id.id
        # Priority 2: Fallback to employee's manager
        elif record.employee_id.parent_id and record.employee_id.parent_id.user_id:
          record.approver_id = record.employee_id.parent_id.user_id.id

      record.state = 'submitted'
      record.message_post(body="Yêu cầu giải trình đã được gửi")

  def action_approve(self):
    """Phê duyệt giải trình"""
    for record in self:
      if record.state != 'submitted':
        continue

      # Permission check: only assigned approver or HR managers can approve
      if record.approver_id and record.approver_id.id != self.env.user.id:
        if not self.env.user.has_group('hr.group_hr_manager'):
          raise UserError(
            'Bạn không có quyền phê duyệt đơn này. Chỉ người phê duyệt được chỉ định hoặc HR Manager mới có thể phê duyệt.')

      record.write({
        'state': 'approved',
        'approver_id': self.env.user.id,
        'approval_date': fields.Datetime.now(),
      })

      # Auto-update original attendance record with corrected times
      if record.attendance_id:
        att = record.attendance_id

        # Priority: corrected > requested > keep original
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
    """Từ chối giải trình"""
    for record in self:
      if record.state != 'submitted':
        continue

      # Permission check: only assigned approver or HR managers can reject
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
    """Đặt lại về trạng thái nháp"""
    for record in self:
      record.state = 'draft'

  def get_my_requests(self):
    """Lấy danh sách yêu cầu của nhân viên hiện tại"""
    return self.search([
      ('employee_id.user_id', '=', self.env.user.id),
    ], order='date desc')

  def get_pending_approvals(self):
    """Lấy danh sách yêu cầu chờ phê duyệt"""
    return self.search([
      ('state', '=', 'submitted'),
    ], order='date desc')

from odoo import models, fields, api


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
        store=True
    )

    @api.depends('excuse_ids', 'excuse_ids.state')
    def _compute_is_excused(self):
        for record in self:
            record.is_excused = any(e.state == 'approved' for e in record.excuse_ids)

    @api.depends('excuse_ids', 'excuse_ids.state')
    def _compute_has_pending_excuse(self):
        for record in self:
            record.has_pending_excuse = any(e.state in ['submitted', 'pending'] for e in record.excuse_ids)

    @api.depends('excuse_ids', 'excuse_ids.state', 'check_in', 'check_out')
    def _compute_requires_excuse(self):
        for record in self:
            requires = False

            # Bỏ qua bản ghi của ngày hôm nay
            if record.check_in:
                check_in_date = fields.Datetime.context_timestamp(record, record.check_in).date()
                today = fields.Date.context_today(record)
                if check_in_date == today:
                    record.requires_excuse = False
                    continue

            # Check if there are any submitted excuses
            if any(e.state in ['submitted'] for e in record.excuse_ids):
                requires = True

            if record.check_in:
                ci = fields.Datetime.context_timestamp(record, record.check_in)
                check_in_hour = ci.hour + ci.minute / 60
                if check_in_hour > 8.75:
                    requires = True

            if record.check_out:
                co = fields.Datetime.context_timestamp(record, record.check_out)
                check_out_hour = co.hour + co.minute / 60
                if check_out_hour < 17.75:
                    requires = True

            if record.check_in and not record.check_out:
                requires = True

            record.requires_excuse = requires

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
                co = fields.Datetime.context_timestamp(self, att.check_out)
                if co.hour == 23 and co.minute == 59 and co.second == 59:
                    AttendanceExcuse.create({
                        'attendance_id': att.id,
                        'state': 'draft',
                        'notes': 'Tự động phát hiện: Quên check-out (auto-checkout tại midnight)',
                    })


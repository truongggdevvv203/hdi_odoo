from odoo import models, fields, api


class HRAttendance(models.Model):
    """Extend hr.attendance to track excuse-related changes"""
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
            record.has_pending_excuse = any(e.state == 'pending' for e in record.excuse_ids)

    @api.depends('excuse_ids', 'excuse_ids.state', 'check_in', 'check_out')
    def _compute_requires_excuse(self):
        for record in self:
            requires = False

            # Check if there are any pending or awaiting excuses
            if any(e.state in ['pending', 'submitted'] for e in record.excuse_ids):
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

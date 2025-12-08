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

    @api.depends('excuse_ids', 'excuse_ids.status')
    def _compute_is_excused(self):
        for record in self:
            record.is_excused = any(e.status == 'approved' for e in record.excuse_ids)

    @api.depends('excuse_ids', 'excuse_ids.status')
    def _compute_has_pending_excuse(self):
        for record in self:
            record.has_pending_excuse = any(e.status == 'pending' for e in record.excuse_ids)

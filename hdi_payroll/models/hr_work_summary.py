from odoo import models, fields, api
from datetime import datetime, timedelta


class HRWorkSummary(models.Model):
    """
    Bảng công - Attendance Summary
    Tóm tắt số ngày công, giờ làm, ngày nghỉ, đi muộn/về sớm của nhân viên
    """
    _name = 'hr.work.summary'
    _description = 'Attendance Summary (Bảng công)'
    _order = 'date desc, employee_id'
    _rec_name = 'display_name'

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

    # Work data
    work_hours = fields.Float(
        string='Số giờ làm việc',
        default=0.0,
        help='Tổng số giờ làm việc trong ngày'
    )

    work_day = fields.Float(
        string='Ngày công',
        default=0.0,
        help='0.5 = nửa ngày, 1 = cả ngày'
    )

    late_minutes = fields.Integer(
        string='Phút đi muộn',
        default=0
    )

    early_minutes = fields.Integer(
        string='Phút về sớm',
        default=0
    )

    # Leave data
    paid_leave = fields.Float(
        string='Ngày nghỉ có lương',
        default=0.0,
        help='Ngày nghỉ phép được trả lương'
    )

    unpaid_leave = fields.Float(
        string='Ngày nghỉ không lương',
        default=0.0,
        help='Ngày nghỉ không được trả lương'
    )

    # Additional info
    notes = fields.Text(
        string='Ghi chú'
    )

    # Computed fields
    @property
    def display_name(self):
        return f"{self.employee_id.name} - {self.date}"

    @api.model_create_multi
    def create(self, vals_list):
        """Auto-calculate work summary when created"""
        for vals in vals_list:
            if 'employee_id' in vals and 'date' in vals:
                # Could auto-calculate from attendance here
                pass
        return super().create(vals_list)

    def action_generate_from_attendance(self):
        """Generate work summary from attendance records"""
        for record in self:
            attendances = self.env['hr.attendance'].search([
                ('employee_id', '=', record.employee_id.id),
                ('check_in', '>=', f"{record.date} 00:00:00"),
                ('check_in', '<', f"{record.date + timedelta(days=1)} 00:00:00"),
            ])

            total_hours = 0
            for att in attendances:
                if att.check_in and att.check_out:
                    delta = att.check_out - att.check_in
                    hours = delta.total_seconds() / 3600.0
                    total_hours += hours

            record.work_hours = total_hours
            # Calculate work_day based on hours
            if total_hours >= 7:
                record.work_day = 1.0
            elif total_hours >= 4:
                record.work_day = 0.5
            else:
                record.work_day = 0.0

    def action_generate_from_leaves(self):
        """Generate leave data from holiday records"""
        for record in self:
            holidays = self.env['hr.holiday'].search([
                ('employee_id', '=', record.employee_id.id),
                ('state', '=', 'validate'),
                ('date_from', '<=', f"{record.date} 23:59:59"),
                ('date_to', '>=', f"{record.date} 00:00:00"),
            ])

            paid_days = 0
            unpaid_days = 0
            for holiday in holidays:
                if holiday.unpaid:
                    unpaid_days += 1
                else:
                    paid_days += 1

            record.paid_leave = paid_days
            record.unpaid_leave = unpaid_days

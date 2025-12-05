from odoo import models, fields, api
from datetime import datetime, timedelta


class HRWorkSummary(models.Model):
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
    display_name = fields.Char(
        string='Tên hiển thị',
        compute='_compute_display_name',
        store=True
    )

    @api.depends('employee_id', 'date')
    def _compute_display_name(self):
        for record in self:
            if record.employee_id and record.date:
                record.display_name = f"{record.employee_id.name} - {record.date}"
            else:
                record.display_name = "Bảng công"

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

    def action_update_from_attendance(self):
        """Update work summary data from hr.attendance records"""
        for record in self:
            self.action_generate_from_attendance()
            self.action_generate_from_leaves()

    @api.model
    def action_sync_all_attendance(self):
        """Sync all attendance data for all employees"""
        from datetime import datetime, timedelta
        
        # Get all employees
        employees = self.env['hr.employee'].search([])
        
        # Get all attendance records
        attendances = self.env['hr.attendance'].search([])
        
        if not attendances:
            return
        
        # Get date range from attendance
        min_date = min([att.check_in.date() for att in attendances if att.check_in])
        max_date = max([att.check_in.date() for att in attendances if att.check_in])
        
        current_date = min_date
        while current_date <= max_date:
            for employee in employees:
                # Check if record exists
                existing = self.search([
                    ('employee_id', '=', employee.id),
                    ('date', '=', current_date)
                ])
                
                if not existing:
                    # Create new record
                    new_record = self.create({
                        'employee_id': employee.id,
                        'date': current_date,
                    })
                    # Generate data from attendance
                    new_record.action_generate_from_attendance()
                    new_record.action_generate_from_leaves()
                else:
                    # Update existing record
                    existing.action_update_from_attendance()
            
            current_date += timedelta(days=1)

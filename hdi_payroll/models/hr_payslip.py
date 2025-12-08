from odoo import models, fields, api
from datetime import datetime, timedelta


class HRPayslip(models.Model):
  _name = 'hr.payslip'
  _description = 'Payslip (Phiếu lương)'
  _order = 'date_from desc, employee_id'

  name = fields.Char(
      string='Số phiếu lương',
      readonly=True,
      copy=False,
      default='/'
  )

  employee_id = fields.Many2one(
      'hr.employee',
      string='Nhân viên',
      required=True,
      ondelete='cascade'
  )

  date_from = fields.Date(
      string='Từ ngày',
      required=True
  )

  date_to = fields.Date(
      string='Đến ngày',
      required=True
  )

  company_id = fields.Many2one(
      'res.company',
      string='Công ty',
      default=lambda self: self.env.company
  )

  salary_structure_id = fields.Many2one(
      'hr.salary.structure',
      string='Cấu trúc lương',
      required=True
  )

  # Work data
  worked_days = fields.Float(
      string='Ngày công',
      default=0.0,
      compute='_compute_attendance_data',
      store=True
  )

  paid_leave = fields.Float(
      string='Ngày nghỉ có lương',
      default=0.0,
      compute='_compute_attendance_data',
      store=True
  )

  unpaid_leave = fields.Float(
      string='Ngày nghỉ không lương',
      default=0.0,
      compute='_compute_attendance_data',
      store=True
  )

  # Salary data from grade
  base_salary = fields.Monetary(
      string='Lương cơ bản',
      compute='_compute_salary_data',
      store=True,
      currency_field='currency_id'
  )

  coefficient = fields.Float(
      string='Hệ số lương',
      compute='_compute_salary_data',
      store=True
  )

  # Results
  line_ids = fields.One2many(
      'hr.payslip.line',
      'payslip_id',
      string='Các dòng lương'
  )

  gross_salary = fields.Monetary(
      string='Lương gross',
      compute='_compute_totals',
      store=True,
      currency_field='currency_id'
  )

  deduction_total = fields.Monetary(
      string='Tổng khoản trừ',
      compute='_compute_totals',
      store=True,
      currency_field='currency_id'
  )

  net_salary = fields.Monetary(
      string='Lương net',
      compute='_compute_totals',
      store=True,
      currency_field='currency_id'
  )

  # Status
  state = fields.Selection(
      [
        ('draft', 'Nháp'),
        ('compute', 'Tính toán'),
        ('done', 'Hoàn thành'),
        ('cancel', 'Hủy'),
      ],
      string='Trạng thái',
      default='draft'
  )

  notes = fields.Text(
      string='Ghi chú'
  )

  currency_id = fields.Many2one(
      'res.currency',
      string='Tiền tệ',
      default=lambda self: self.env.company.currency_id
  )

  @api.depends('date_from', 'date_to', 'employee_id')
  def _compute_attendance_data(self):
    """Compute worked days and leaves from hr.attendance records"""
    for payslip in self:
      # Skip if required data is missing
      if not payslip.employee_id or not payslip.date_from or not payslip.date_to:
        payslip.worked_days = 0
        payslip.paid_leave = 0
        payslip.unpaid_leave = 0
        continue

      total_worked = 0.0
      total_paid_leave = 0.0
      total_unpaid_leave = 0.0

      # Get all attendance records for this period
      attendances = self.env['hr.attendance'].search([
        ('employee_id', '=', payslip.employee_id.id),
        ('check_in', '>=', datetime.combine(payslip.date_from, datetime.min.time())),
        ('check_in', '<=', datetime.combine(payslip.date_to, datetime.max.time())),
      ])

      # Calculate worked days from attendance
      for att in attendances:
        if att.check_in and att.check_out:
          delta = att.check_out - att.check_in
          hours = delta.total_seconds() / 3600.0
          # Standard workday is 8 hours
          if hours >= 8:
            total_worked += 1.0
          elif hours >= 4:
            total_worked += 0.5

      # Get all leave records for this period
      leaves = self.env['hr.leave'].search([
        ('employee_id', '=', payslip.employee_id.id),
        ('date_from', '<=', datetime.combine(payslip.date_to, datetime.max.time())),
        ('date_to', '>=', datetime.combine(payslip.date_from, datetime.min.time())),
        ('state', '=', 'validate'),
      ])

      for leave in leaves:
        leave_days = (leave.date_to.date() - leave.date_from.date()).days + 1
        if leave.holiday_status_id.unpaid:
          total_unpaid_leave += leave_days
        else:
          total_paid_leave += leave_days

      payslip.worked_days = total_worked
      payslip.paid_leave = total_paid_leave
      payslip.unpaid_leave = total_unpaid_leave

  @api.depends('employee_id')
  def _compute_salary_data(self):
    """Get salary grade data for employee"""
    for payslip in self:
      grade = self.env['hr.salary.grade'].get_grade_for_employee(
        payslip.employee_id)
      if grade:
        payslip.base_salary = grade.base_salary
        payslip.coefficient = grade.coefficient
      else:
        payslip.base_salary = 0
        payslip.coefficient = 1.0

  @api.depends('line_ids', 'line_ids.amount')
  def _compute_totals(self):
    """Compute gross, deductions, and net salary"""
    for payslip in self:
      gross = 0
      deductions = 0

      for line in payslip.line_ids:
        if line.category in ['basic', 'allowance']:
          gross += line.amount
        elif line.category in ['deduction', 'insurance', 'tax']:
          deductions += line.amount

      payslip.gross_salary = gross
      payslip.deduction_total = deductions
      payslip.net_salary = gross - deductions

  @api.model_create_multi
  def create(self, vals_list):
    """Create payslip and generate sequence"""
    for vals in vals_list:
      vals['name'] = self.env['ir.sequence'].next_by_code('hr.payslip') or '/'
    return super().create(vals_list)

  def action_update_work_data(self):
    """Update work data from attendance records"""
    for payslip in self:
      if payslip.state != 'draft' or not payslip.employee_id or not payslip.date_from or not payslip.date_to:
        continue

      # Force recompute of attendance data
      payslip._compute_attendance_data()

  def action_compute(self):
    """Compute payslip - calculate all salary rules"""
    for payslip in self:
      if payslip.state != 'draft':
        continue

      # Clear existing lines
      payslip.line_ids.unlink()

      # Build local dictionary for computation
      localdict = {
        'employee': payslip.employee_id,
        'worked_days': payslip.worked_days,
        'paid_leave': payslip.paid_leave,
        'unpaid_leave': payslip.unpaid_leave,
        'base_salary': payslip.base_salary,
        'coefficient': payslip.coefficient,
        'allowance': self.env['hr.salary.grade'].get_grade_for_employee(payslip.employee_id).allowance or 0,
      }

      # Get all rules from structure and compute
      rules = payslip.salary_structure_id.rule_ids.sorted('sequence')
      line_vals_list = []

      for rule in rules:
        try:
          amount = rule.compute(payslip, localdict.copy())
          # Store the amount in localdict for next rules to use
          localdict[rule.code] = amount

          line_vals = {
            'payslip_id': payslip.id,
            'rule_id': rule.id,
            'name': rule.name,
            'code': rule.code,
            'category': rule.category,
            'amount': amount,
          }
          line_vals_list.append(line_vals)
        except Exception as e:
          import logging
          _logger = logging.getLogger(__name__)
          _logger.error(f"Error computing rule {rule.code}: {str(e)}")

      self.env['hr.payslip.line'].create(line_vals_list)
      payslip.state = 'compute'

  def action_validate(self):
    """Validate and finalize payslip"""
    for payslip in self:
      if payslip.state not in ['draft', 'compute']:
        continue
      payslip.state = 'done'

  def action_cancel(self):
    """Cancel payslip"""
    for payslip in self:
      payslip.state = 'cancel'

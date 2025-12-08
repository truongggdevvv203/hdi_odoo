from odoo import models, fields, api
from datetime import datetime


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
    """Compute worked days and leaves from attendance records"""
    for payslip in self:
      total_worked = 0
      total_paid_leave = 0
      total_unpaid_leave = 0

      # Get all work summaries for this period
      summaries = self.env['hr.work.summary'].search([
        ('employee_id', '=', payslip.employee_id.id),
        ('date', '>=', payslip.date_from),
        ('date', '<=', payslip.date_to),
      ])

      for summary in summaries:
        total_worked += summary.work_day
        total_paid_leave += summary.paid_leave
        total_unpaid_leave += summary.unpaid_leave

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

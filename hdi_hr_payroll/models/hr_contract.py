# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class HrContract(models.Model):
    _inherit = 'hr.contract'

    # ==================== LƯƠNG CƠ BẢN ====================
    # wage đã có sẵn từ core
    # Lương năng suất được nhập trực tiếp vào phiếu lương (input_line_ids)

    # Lương thử việc
    is_probation = fields.Boolean('Đang thử việc', tracking=True)
    probation_wage_rate = fields.Float(
        'Tỷ lệ lương thử việc (%)',
        default=85.0,
        help='Phần trăm lương được hưởng trong thời gian thử việc'
    )
    probation_wage = fields.Monetary('Lương thử việc', compute='_compute_probation_wage', store=True)

    # ==================== PHỤ CẤP CỐ ĐỊNH ====================
    meal_allowance = fields.Monetary('Phụ cấp ăn trưa', default=0, tracking=True)
    transport_allowance = fields.Monetary('Phụ cấp xăng xe', default=0, tracking=True)
    phone_allowance = fields.Monetary('Phụ cấp điện thoại', default=0, tracking=True)
    housing_allowance = fields.Monetary('Phụ cấp nhà ở', default=0, tracking=True)
    onsite_allowance = fields.Monetary('Phụ cấp onsite', default=0, tracking=True)
    uniform_allowance = fields.Monetary('Phụ cấp đồng phục', default=0, tracking=True)
    position_allowance = fields.Monetary('Phụ cấp chức vụ', default=0, tracking=True)
    responsibility_allowance = fields.Monetary('Phụ cấp trách nhiệm', default=0, tracking=True)
    other_allowance = fields.Monetary('Phụ cấp khác', default=0, tracking=True)

    total_allowance = fields.Monetary('Tổng phụ cấp', compute='_compute_total_allowance', store=True)

    # ==================== BẢO HIỂM XÃ HỘI ====================
    # Mức lương đóng bảo hiểm
    insurance_salary = fields.Monetary(
        'Mức lương đóng BHXH',
        compute='_compute_insurance_salary',
        store=True,
        tracking=True,
        help='Mức lương làm căn cứ đóng BHXH, BHYT, BHTN'
    )

    # Tỷ lệ đóng BHXH - Công ty
    si_company_rate = fields.Float('BHXH - Công ty (%)', default=17.5)
    hi_company_rate = fields.Float('BHYT - Công ty (%)', default=3.0)
    ui_company_rate = fields.Float('BHTN - Công ty (%)', default=1.0)

    # Tỷ lệ đóng BHXH - Nhân viên
    si_employee_rate = fields.Float('BHXH - Nhân viên (%)', default=8.0)
    hi_employee_rate = fields.Float('BHYT - Nhân viên (%)', default=1.5)
    ui_employee_rate = fields.Float('BHTN - Nhân viên (%)', default=1.0)

    # Tổng BH
    total_insurance_company = fields.Monetary('Tổng BH - Công ty', compute='_compute_insurance_amounts')
    total_insurance_employee = fields.Monetary('Tổng BH - NV', compute='_compute_insurance_amounts')

    # ==================== KPI & THƯỞNG ====================
    has_kpi = fields.Boolean('Có KPI', default=False)
    kpi_target = fields.Monetary('Chỉ tiêu KPI')
    kpi_rate = fields.Float('Tỷ lệ thưởng KPI (%)', default=0)

    @api.depends('wage', 'probation_wage_rate')
    def _compute_probation_wage(self):
        for contract in self:
            contract.probation_wage = contract.wage * (contract.probation_wage_rate / 100)

    @api.depends(
        'meal_allowance', 'transport_allowance', 'phone_allowance',
        'housing_allowance', 'onsite_allowance', 'uniform_allowance',
        'position_allowance', 'responsibility_allowance', 'other_allowance'
    )
    def _compute_total_allowance(self):
        for contract in self:
            contract.total_allowance = (
                    contract.meal_allowance +
                    contract.transport_allowance +
                    contract.phone_allowance +
                    contract.housing_allowance +
                    contract.onsite_allowance +
                    contract.uniform_allowance +
                    contract.position_allowance +
                    contract.responsibility_allowance +
                    contract.other_allowance
            )

    @api.depends('wage')
    def _compute_insurance_salary(self):
        """Mức đóng BH = Chỉ lương cơ bản (theo ví dụ)"""
        for contract in self:
            contract.insurance_salary = contract.wage

    @api.onchange('wage')
    def _onchange_wage(self):
        """Trigger recalculation when wage changes"""
        self.insurance_salary = self.wage

    @api.depends('insurance_salary', 'si_company_rate', 'hi_company_rate', 'ui_company_rate',
                 'si_employee_rate', 'hi_employee_rate', 'ui_employee_rate')
    def _compute_insurance_amounts(self):
        for contract in self:
            # Công ty đóng
            si_company = contract.insurance_salary * (contract.si_company_rate / 100)
            hi_company = contract.insurance_salary * (contract.hi_company_rate / 100)
            ui_company = contract.insurance_salary * (contract.ui_company_rate / 100)
            contract.total_insurance_company = si_company + hi_company + ui_company

            # Nhân viên đóng
            si_employee = contract.insurance_salary * (contract.si_employee_rate / 100)
            hi_employee = contract.insurance_salary * (contract.hi_employee_rate / 100)
            ui_employee = contract.insurance_salary * (contract.ui_employee_rate / 100)
            contract.total_insurance_employee = si_employee + hi_employee + ui_employee

    @api.constrains('probation_wage_rate')
    def _check_probation_rate(self):
        for contract in self:
            if contract.probation_wage_rate < 0 or contract.probation_wage_rate > 100:
                raise ValidationError(_('Tỷ lệ lương thử việc phải từ 0% đến 100%'))

    def get_active_allowances(self, date_from, date_to):
        """Lấy các phụ cấp đang active trong khoảng thời gian"""
        self.ensure_one()
        return self.allowance_assignment_ids.filtered(
            lambda a: a.is_active and
                      (not a.date_from or a.date_from <= date_to) and
                      (not a.date_to or a.date_to >= date_from)
        )

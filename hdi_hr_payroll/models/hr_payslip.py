# -*- coding: utf-8 -*-

from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_round


class HrPayslip(models.Model):
    _name = 'hr.payslip'
    _description = 'Phiếu lương'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_from desc, id desc'

    name = fields.Char('Tên phiếu lương', required=True, readonly=True, states={'draft': [('readonly', False)]})
    number = fields.Char('Số phiếu', readonly=True, copy=False, help='Mã tham chiếu phiếu lương')

    # ==================== THÔNG TIN CHUNG ====================
    employee_id = fields.Many2one(
        'hr.employee', 'Nhân viên',
        required=True, readonly=True,
        states={'draft': [('readonly', False)]},
        tracking=True
    )

    contract_id = fields.Many2one(
        'hr.contract', 'Hợp đồng',
        readonly=True, states={'draft': [('readonly', False)]},
        domain="[('employee_id', '=', employee_id), ('state', 'in', ['open', 'close'])]"
    )

    struct_id = fields.Many2one(
        'hr.payroll.structure', 'Cấu trúc lương',
        readonly=True, states={'draft': [('readonly', False)]},
        help='Quyết định các rule nào được áp dụng'
    )

    # Trạng thái thử việc (từ contract)
    is_probation = fields.Boolean(
        'Đang thử việc',
        related='contract_id.is_probation',
        store=True,
        help='Trạng thái thử việc từ hợp đồng'
    )

    # ==================== THỜI GIAN ====================
    date_from = fields.Date(
        'Từ ngày', required=True,
        readonly=True, states={'draft': [('readonly', False)]},
        default=lambda self: fields.Date.today().replace(day=1)
    )
    date_to = fields.Date(
        'Đến ngày', required=True,
        readonly=True, states={'draft': [('readonly', False)]},
        default=lambda self: (fields.Date.today().replace(day=1) + relativedelta(months=1, days=-1))
    )

    # ==================== CÔNG CHUẨN ====================
    standard_days = fields.Float(
        'Công chuẩn trong tháng',
        default=22.5,
        readonly=True, states={'draft': [('readonly', False)]},
        help='Số ngày công chuẩn trong tháng (VD: 22.5, 26...)'
    )

    # ==================== TRẠNG THÁI ====================
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('verify', 'Chờ duyệt'),
        ('done', 'Đã duyệt'),
        ('cancel', 'Đã hủy'),
        ('paid', 'Đã thanh toán')
    ], 'Trạng thái', default='draft', tracking=True, copy=False)

    # ==================== CHI TIẾT TÍNH LƯƠNG ====================
    line_ids = fields.One2many(
        'hr.payslip.line', 'slip_id',
        'Chi tiết lương',
        readonly=True, states={'draft': [('readonly', False)]}
    )

    worked_days_line_ids = fields.One2many(
        'hr.payslip.worked.days', 'slip_id',
        'Ngày công',
        readonly=True, states={'draft': [('readonly', False)]}
    )

    input_line_ids = fields.One2many(
        'hr.payslip.input', 'slip_id',
        'Dữ liệu nhập thêm',
        readonly=True, states={'draft': [('readonly', False)]},
        help='Các khoản khác như thưởng, phạt, tạm ứng...'
    )

    # ==================== KẾT QUẢ ====================
    basic_wage = fields.Monetary('Lương cơ bản', compute='_compute_summary', store=True)
    gross_wage = fields.Monetary('Tổng thu nhập', compute='_compute_summary', store=True)
    net_wage = fields.Monetary('Thực lĩnh', compute='_compute_summary', store=True, tracking=True)
    total_deduction = fields.Monetary('Tổng khấu trừ', compute='_compute_summary', store=True)

    # ==================== LƯƠNG NĂNG SUẤT ====================
    performance_wage_total = fields.Monetary(
        'Tổng lương năng suất',
        help='Nhập tổng lương năng suất trong tháng. Hệ thống sẽ tự động tính theo công thực tế.'
    )

    # ==================== KHÁC ====================
    company_id = fields.Many2one('res.company', 'Công ty', default=lambda self: self.env.company, required=True)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')

    note = fields.Text('Ghi chú nội bộ')
    payslip_note = fields.Html('Ghi chú trên phiếu lương', help='Hiển thị khi in phiếu lương')

    # Payment
    paid_date = fields.Date('Ngày thanh toán', readonly=True, copy=False)

    _sql_constraints = [
        ('payslip_employee_unique', 'unique(employee_id, date_from, date_to, company_id)',
         'Mỗi nhân viên chỉ có 1 phiếu lương trong 1 kỳ!')
    ]

    @api.depends('line_ids.total')
    def _compute_summary(self):
        """Tính tổng các khoản từ salary rule lines"""
        for payslip in self:
            lines = payslip.line_ids

            # Lương cơ bản
            basic_line = lines.filtered(lambda l: l.code == 'BASIC')
            payslip.basic_wage = sum(basic_line.mapped('total'))

            # Tổng thu nhập (GROSS)
            gross_lines = lines.filtered(lambda l: l.category_id.code == 'GROSS')
            payslip.gross_wage = sum(gross_lines.mapped('total'))

            # Tổng khấu trừ (số âm)
            deduction_lines = lines.filtered(lambda l: l.category_id.code in ['DED', 'INSURANCE'])
            payslip.total_deduction = sum(deduction_lines.mapped('total'))

            # Thực lĩnh
            net_line = lines.filtered(lambda l: l.code == 'NET')
            payslip.net_wage = sum(net_line.mapped('total'))

    @api.onchange('employee_id', 'date_from', 'date_to')
    def _onchange_employee(self):
        """Tự động điền contract khi chọn nhân viên"""
        if self.employee_id:
            # Tìm contract đang active
            contract = self.env['hr.contract'].search([
                ('employee_id', '=', self.employee_id.id),
                ('state', '=', 'open'),
                ('date_start', '<=', self.date_to or fields.Date.today()),
                '|',
                ('date_end', '=', False),
                ('date_end', '>=', self.date_from or fields.Date.today())
            ], limit=1)

            if contract:
                self.contract_id = contract
                # Tự động chọn cấu trúc lương dựa trên trạng thái thử việc
                self._auto_select_structure()
                self.company_id = contract.company_id

            # Tự động tạo tên
            if self.date_from:
                self.name = f"Lương {self.employee_id.name} - {self.date_from.strftime('%m/%Y')}"

    @api.onchange('contract_id')
    def _onchange_contract(self):
        """Tự động chọn cấu trúc lương khi thay đổi contract"""
        if self.contract_id:
            self._auto_select_structure()

    def _auto_select_structure(self):
        """Tự động chọn cấu trúc lương dựa trên trạng thái thử việc trong contract"""
        if not self.contract_id:
            return

        # Kiểm tra trạng thái thử việc
        if self.contract_id.is_probation:
            # Nếu đang thử việc → Chọn cấu trúc "Thử việc Việt Nam"
            probation_struct = self.env.ref('hdi_hr_payroll.payroll_structure_vn_probation', raise_if_not_found=False)
            if probation_struct:
                self.struct_id = probation_struct
        else:
            # Nếu chính thức → Chọn cấu trúc "Nhân viên Việt Nam"
            employee_struct = self.env.ref('hdi_hr_payroll.payroll_structure_vn_employee', raise_if_not_found=False)
            if employee_struct:
                self.struct_id = employee_struct

    def action_payslip_draft(self):
        """Chuyển về nháp"""
        return self.write({'state': 'draft'})

    def action_payslip_verify(self):
        """Gửi duyệt"""
        self._validate_payslip()
        return self.write({'state': 'verify'})

    def action_payslip_done(self):
        """Duyệt phiếu lương"""
        for payslip in self:
            if not payslip.number:
                payslip.number = self.env['ir.sequence'].next_by_code('hr.payslip') or _('New')
        return self.write({'state': 'done'})

    def action_payslip_cancel(self):
        """Hủy phiếu lương"""
        return self.write({'state': 'cancel'})

    def action_payslip_paid(self):
        """Đánh dấu đã thanh toán"""
        return self.write({
            'state': 'paid',
            'paid_date': fields.Date.today()
        })

    def _validate_payslip(self):
        """Kiểm tra tính hợp lệ trước khi duyệt"""
        for payslip in self:
            if not payslip.contract_id:
                raise ValidationError(_('Vui lòng chọn hợp đồng cho %s') % payslip.employee_id.name)
            if not payslip.line_ids:
                raise ValidationError(_('Phiếu lương chưa có dữ liệu. Vui lòng Tính lương trước.'))

    def compute_sheet(self):
        """Tính toán phiếu lương - CORE FUNCTION"""
        for payslip in self:
            # Validate dữ liệu bắt buộc
            if not payslip.employee_id:
                raise UserError(_('Vui lòng chọn Nhân viên trước khi tính lương!'))
            if not payslip.contract_id:
                raise UserError(_('Vui lòng chọn Hợp đồng trước khi tính lương!'))

            # Tự động chọn cấu trúc lương nếu chưa có
            if not payslip.struct_id:
                payslip._auto_select_structure()

            # Kiểm tra lại sau khi tự động chọn
            if not payslip.struct_id:
                raise UserError(_('Không tìm thấy Cấu trúc lương phù hợp. Vui lòng kiểm tra hợp đồng!'))

            # Xóa dữ liệu cũ
            payslip.line_ids.unlink()
            payslip.worked_days_line_ids.unlink()

            # Tạo/cập nhật input cho lương năng suất
            if payslip.performance_wage_total > 0:
                # Xóa input PERFORMANCE cũ (nếu có)
                payslip.input_line_ids.filtered(lambda x: x.code == 'PERFORMANCE').unlink()

                # Tạo input mới
                self.env['hr.payslip.input'].create({
                    'slip_id': payslip.id,
                    'name': 'Lương năng suất',
                    'code': 'PERFORMANCE',
                    'amount': payslip.performance_wage_total,
                    'sequence': 1,
                })

            # --- Bổ sung tự động tạo input tạm ứng, vay, kỷ luật, khen thưởng ---
            # 1. Tạm ứng/vay: lấy các khoản trả góp kỳ này
            loan_domain = [
                ('employee_id', '=', payslip.employee_id.id),
                ('state', '=', 'approved'),
                ('installment_method', '=', 'auto'),
                ('balance', '>', 0),
            ]
            loan_lines = payslip.env['hr.loan.line'].search([
                ('loan_id', 'in', payslip.env['hr.loan'].search(loan_domain).ids),
                ('installment_date', '>=', payslip.date_from),
                ('installment_date', '<=', payslip.date_to),
                ('paid', '=', False),
            ])
            advance_total = sum(l.amount for l in loan_lines.filtered(lambda l: l.loan_id.loan_type == 'advance'))
            loan_total = sum(l.amount for l in loan_lines.filtered(lambda l: l.loan_id.loan_type == 'loan'))
            # Xóa input cũ
            payslip.input_line_ids.filtered(lambda x: x.code in ['ADVANCE', 'LOAN']).unlink()
            if advance_total > 0:
                self.env['hr.payslip.input'].create({
                    'slip_id': payslip.id,
                    'name': 'Tạm ứng',
                    'code': 'ADVANCE',
                    'amount': advance_total,
                    'sequence': 2,
                })
            if loan_total > 0:
                self.env['hr.payslip.input'].create({
                    'slip_id': payslip.id,
                    'name': 'Khoản vay',
                    'code': 'LOAN',
                    'amount': loan_total,
                    'sequence': 3,
                })

            # 2. Kỷ luật: lấy các quyết định phạt tiền chưa trừ vào lương
            discipline_domain = [
                ('employee_id', '=', payslip.employee_id.id),
                ('state', '=', 'approved'),
                ('deduct_from_payslip', '=', True),
                ('is_deducted', '=', False),
                ('fine_amount', '>', 0),
                ('date', '>=', payslip.date_from),
                ('date', '<=', payslip.date_to),
            ]
            # Lấy các quyết định kỷ luật cần trừ
            discipline_records = payslip.env['hr.discipline'].search(discipline_domain)
            discipline_total = sum(p.fine_amount for p in discipline_records)
            payslip.input_line_ids.filtered(lambda x: x.code == 'DEDUCTION').unlink()
            if discipline_total > 0:
                self.env['hr.payslip.input'].create({
                    'slip_id': payslip.id,
                    'name': 'Phạt/Kỷ luật',
                    'code': 'DEDUCTION',
                    'amount': discipline_total,
                    'sequence': 4,
                })
                # Đánh dấu đã trừ vào lương
                discipline_records.write({'payslip_id': payslip.id})

            # 3. Khen thưởng: lấy các quyết định thưởng chưa cộng vào lương
            reward_domain = [
                ('employee_id', '=', payslip.employee_id.id),
                ('state', '=', 'approved'),
                ('add_to_payslip', '=', True),
                ('is_paid', '=', False),
                ('amount', '>', 0),
                ('date', '>=', payslip.date_from),
                ('date', '<=', payslip.date_to),
            ]
            reward_total = sum(r.amount for r in payslip.env['hr.reward'].search(reward_domain))
            payslip.input_line_ids.filtered(lambda x: x.code == 'BONUS').unlink()
            if reward_total > 0:
                self.env['hr.payslip.input'].create({
                    'slip_id': payslip.id,
                    'name': 'Khen thưởng',
                    'code': 'BONUS',
                    'amount': reward_total,
                    'sequence': 5,
                })

            # 1. Lấy worked days từ work entries
            payslip._get_worked_days_lines()

            # 2. Tính toán các rule
            payslip._compute_salary_rules()

        return True

    def _get_worked_days_lines(self):
        """
        Lấy số ngày công từ hr.work.entry và hr.attendance

        Các loại ngày công:
        - WORK100: Ngày công thực tế (từ attendance/work entry)
        - LEAVE: Nghỉ phép hưởng lương
        - UNPAID: Nghỉ không lương
        - PENALTY: Đi muộn/về sớm (nếu có)
        """
        self.ensure_one()

        res = []

        # 1. Lấy từ Work Entries (nếu có)
        work_entries = self.env['hr.work.entry'].search([
            ('employee_id', '=', self.employee_id.id),
            ('date_start', '>=', self.date_from),
            ('date_stop', '<=', self.date_to),
            ('state', '=', 'validated')
        ])

        if work_entries:
            # Group theo loại work entry
            work_entry_types = work_entries.mapped('work_entry_type_id')

            for wet in work_entry_types:
                entries = work_entries.filtered(lambda e: e.work_entry_type_id == wet)

                # Tính tổng giờ
                total_hours = sum(entries.mapped('duration'))

                # Quy đổi ra ngày (8 giờ = 1 ngày)
                number_of_days = total_hours / 8.0

                res.append({
                    'slip_id': self.id,
                    'work_entry_type_id': wet.id,
                    'name': wet.name,
                    'code': wet.code,
                    'number_of_days': number_of_days,
                    'number_of_hours': total_hours,
                    'sequence': 1 if wet.code == 'WORK100' else 10,
                })

        else:
            # 2. Nếu không có work entry, tính từ Attendance
            attendances = self.env['hr.attendance'].search([
                ('employee_id', '=', self.employee_id.id),
                ('check_in', '>=', self.date_from),
                ('check_in', '<=', self.date_to),
            ])

            # Đếm số ngày có chấm công (unique dates)
            attendance_dates = set()
            for att in attendances:
                if att.check_in:
                    attendance_dates.add(att.check_in.date())

            attendance_days = len(attendance_dates)

            # Tổng giờ làm việc
            total_hours = sum(attendances.mapped('worked_hours'))

            # Thêm WORK100 - Ngày công thực tế
            if attendance_days > 0:
                res.append({
                    'slip_id': self.id,
                    'work_entry_type_id': False,
                    'name': 'Ngày công thực tế',
                    'code': 'WORK100',
                    'number_of_days': attendance_days,
                    'number_of_hours': total_hours,
                    'sequence': 1,
                })

            # 3. Nghỉ phép hưởng lương (từ hr.leave)
            leaves = self.env['hr.leave'].search([
                ('employee_id', '=', self.employee_id.id),
                ('date_from', '>=', self.date_from),
                ('date_to', '<=', self.date_to),
                ('state', '=', 'validate'),
                ('holiday_status_id.unpaid', '=', False),  # Phép có lương
            ])

            if leaves:
                leave_days = sum(leaves.mapped('number_of_days'))
                res.append({
                    'slip_id': self.id,
                    'work_entry_type_id': False,
                    'name': 'Nghỉ phép hưởng lương',
                    'code': 'LEAVE',
                    'number_of_days': leave_days,
                    'number_of_hours': leave_days * 8,
                    'sequence': 2,
                })

            # 4. Nghỉ không lương
            unpaid_leaves = self.env['hr.leave'].search([
                ('employee_id', '=', self.employee_id.id),
                ('date_from', '>=', self.date_from),
                ('date_to', '<=', self.date_to),
                ('state', '=', 'validate'),
                ('holiday_status_id.unpaid', '=', True),  # Phép không lương
            ])

            if unpaid_leaves:
                unpaid_days = sum(unpaid_leaves.mapped('number_of_days'))
                res.append({
                    'slip_id': self.id,
                    'work_entry_type_id': False,
                    'name': 'Nghỉ không lương',
                    'code': 'UNPAID',
                    'number_of_days': unpaid_days,
                    'number_of_hours': unpaid_days * 8,
                    'sequence': 3,
                })

        # Tạo worked days lines
        if res:
            self.env['hr.payslip.worked.days'].create(res)
        else:
            # Nếu không có dữ liệu nào, tạo mặc định với công chuẩn
            self.env['hr.payslip.worked.days'].create({
                'slip_id': self.id,
                'name': 'Ngày công (mặc định)',
                'code': 'WORK100',
                'number_of_days': self.standard_days,
                'number_of_hours': self.standard_days * 8,
                'sequence': 1,
            })

        return res

    def _compute_salary_rules(self):
        """Tính toán tất cả salary rules"""
        self.ensure_one()

        if not self.struct_id:
            raise UserError(_('Vui lòng chọn Cấu trúc lương'))

        # Lấy tất cả rules từ structure, sắp xếp theo sequence
        rules = self.struct_id.rule_ids.sorted(key=lambda r: r.sequence)

        if not rules:
            raise UserError(
                _('Cấu trúc lương "%s" chưa có quy tắc tính lương nào!\n\nVui lòng kiểm tra: Payroll → Cấu hình → Cấu trúc lương') % self.struct_id.name)

        # Chuẩn bị context để tính toán
        localdict = self._get_localdict()

        # BrowsableObject class
        class BrowsableObject(object):
            def __init__(self, data_dict):
                self.__dict__.update(data_dict)

            def __getattr__(self, attr):
                return self.__dict__.get(attr, 0)  # Return 0 nếu không tồn tại

        # Dictionary lưu kết quả các rule đã tính
        rule_results = {}
        category_totals = {}

        result_lines = []

        for rule in rules:
            # Kiểm tra điều kiện
            if not rule._satisfy_condition(localdict):
                continue

            # Tính toán
            amount, qty, rate = rule._compute_rule(localdict)

            # Làm tròn
            amount = float_round(amount, precision_digits=0)

            # Lưu vào dict để rules sau có thể dùng
            rule_results[rule.code] = amount
            localdict['rules'] = BrowsableObject(rule_results)

            # Cộng vào category
            cat_code = rule.category_id.code
            category_totals[cat_code] = category_totals.get(cat_code, 0) + amount
            localdict['categories'] = BrowsableObject(category_totals)

            # Tạo line
            result_lines.append({
                'slip_id': self.id,
                'salary_rule_id': rule.id,
                'name': rule.name,
                'code': rule.code,
                'category_id': rule.category_id.id,
                'sequence': rule.sequence,
                'appears_on_payslip': rule.appears_on_payslip,
                'quantity': qty,
                'rate': rate,
                'amount': amount / qty if qty else amount,
                'total': amount,
            })

        # Tạo payslip lines
        if result_lines:
            self.env['hr.payslip.line'].create(result_lines)

        return True

    def _get_localdict(self):
        """Tạo dictionary cho Python expression trong rules"""
        self.ensure_one()

        # Worked days - BrowsableObject để dùng worked_days.WORK100
        class BrowsableObject(object):
            def __init__(self, data_dict):
                self.__dict__.update(data_dict)

            def __getattr__(self, attr):
                return self.__dict__.get(attr, 0)  # Return 0 nếu không tồn tại

        worked_days_dict = {}
        for wd in self.worked_days_line_ids:
            worked_days_dict[wd.code] = wd

        # Inputs
        inputs_dict = {}
        for inp in self.input_line_ids:
            inputs_dict[inp.code] = inp

        return {
            'payslip': self,
            'employee': self.employee_id,
            'contract': self.contract_id,
            'worked_days': BrowsableObject(worked_days_dict),
            'inputs': BrowsableObject(inputs_dict),
            'rules': BrowsableObject({}),  # Sẽ được fill dần khi tính
            'categories': BrowsableObject({}),  # Tổng theo category
            # Built-in functions cần thiết cho Python code trong rules
            'hasattr': hasattr,
            'len': len,
            'sum': sum,
            'abs': abs,
            'min': min,
            'max': max,
            'round': round,
            'float': float,
            'int': int,
            'str': str,
            'bool': bool,
        }

    def action_print_payslip(self):
        """In phiếu lương"""
        return self.env.ref('hdi_payroll.action_report_payslip').report_action(self)

    def unlink(self):
        """Chỉ xóa được nếu đang ở trạng thái draft hoặc cancel"""
        if any(slip.state not in ['draft', 'cancel'] for slip in self):
            raise UserError(_('Bạn chỉ có thể xóa phiếu lương ở trạng thái Nháp hoặc Đã hủy!'))
        return super(HrPayslip, self).unlink()


class HrPayslipLine(models.Model):
    _name = 'hr.payslip.line'
    _description = 'Chi tiết phiếu lương'
    _order = 'slip_id, sequence, id'

    slip_id = fields.Many2one('hr.payslip', 'Phiếu lương', required=True, ondelete='cascade')
    salary_rule_id = fields.Many2one('hr.salary.rule', 'Quy tắc', required=True)

    name = fields.Char('Tên', required=True)
    code = fields.Char('Mã', required=True)

    category_id = fields.Many2one('hr.salary.rule.category', 'Nhóm', required=True)
    sequence = fields.Integer('Thứ tự', default=10)

    # Tính toán
    quantity = fields.Float('Số lượng', default=1.0)
    rate = fields.Float('Tỷ lệ (%)', default=100.0)
    amount = fields.Monetary('Đơn giá')
    total = fields.Monetary('Thành tiền', required=True)

    # Hiển thị
    appears_on_payslip = fields.Boolean('Hiển thị trên phiếu', default=True)

    # Company & Currency
    company_id = fields.Many2one(related='slip_id.company_id', store=True)
    currency_id = fields.Many2one(related='slip_id.currency_id')

    note = fields.Text('Ghi chú')


class HrPayslipWorkedDays(models.Model):
    _name = 'hr.payslip.worked.days'
    _description = 'Ngày công trong phiếu lương'
    _order = 'slip_id, sequence'

    slip_id = fields.Many2one('hr.payslip', 'Phiếu lương', required=True, ondelete='cascade')

    work_entry_type_id = fields.Many2one('hr.work.entry.type', 'Loại')
    name = fields.Char('Mô tả', required=True)
    code = fields.Char('Mã', required=True)

    number_of_days = fields.Float('Số ngày', default=0.0)
    number_of_hours = fields.Float('Số giờ', default=0.0)

    sequence = fields.Integer('Thứ tự', default=10)


class HrPayslipInput(models.Model):
    _name = 'hr.payslip.input'
    _description = 'Dữ liệu nhập thêm vào phiếu lương'
    _order = 'slip_id, sequence'

    slip_id = fields.Many2one('hr.payslip', 'Phiếu lương', required=True, ondelete='cascade')

    name = fields.Char('Tên', required=True)
    code = fields.Char('Mã', required=True, help='Dùng trong Python expression')

    amount = fields.Monetary('Số tiền', required=True)

    company_id = fields.Many2one(related='slip_id.company_id', store=True)
    currency_id = fields.Many2one(related='slip_id.currency_id')

    sequence = fields.Integer('Thứ tự', default=10)

    contract_id = fields.Many2one(related='slip_id.contract_id', store=True)

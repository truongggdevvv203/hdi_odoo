from odoo import models, fields, api


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    start_work_date = fields.Date(
        string='Ngày bắt đầu làm việc',
        tracking=True
    )

    seniority_text = fields.Char(
        string='Thâm niên',
        compute='_compute_seniority',
        store=True
    )

    @api.depends('start_work_date')
    def _compute_seniority(self):
        """Tính thâm niên hiển thị theo dạng: X năm Y tháng"""
        for rec in self:
            if rec.start_work_date:
                today = date.today()
                start = rec.start_work_date

                years = today.year - start.year
                months = today.month - start.month

                # Nếu chưa tới ngày làm trong tháng ⇒ trừ 1 tháng
                if today.day < start.day:
                    months -= 1

                # Nếu tháng âm ⇒ giảm 1 năm và cộng 12 tháng
                if months < 0:
                    years -= 1
                    months += 12

                # Xuất dạng "X năm Y tháng"
                rec.seniority_text = f"{years} năm {months} tháng"
            else:
                rec.seniority_text = "0 năm 0 tháng"


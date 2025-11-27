from odoo import models, fields, api

class CrmLeadEnhanced(models.Model):
    _inherit = 'crm.lead'

    # Trường custom ví dụ
    customer_priority = fields.Selection([
        ('low', 'Thấp'),
        ('medium', 'Trung bình'),
        ('high', 'Cao'),
    ], string='Ưu tiên khách hàng', default='medium')

    lead_source_detail = fields.Char(string='Nguồn chi tiết')

    lead_score = fields.Integer(string='Điểm tiềm năng', default=0)

    # Tính điểm tự động dựa trên điều kiện
    @api.onchange('customer_priority', 'expected_revenue')
    def _compute_lead_score(self):
        for record in self:
            score = 0
            if record.customer_priority == 'high':
                score += 50
            elif record.customer_priority == 'medium':
                score += 30
            else:
                score += 10

            if record.expected_revenue:
                if record.expected_revenue > 100000:
                    score += 50
                elif record.expected_revenue > 50000:
                    score += 30
                else:
                    score += 10

            record.lead_score = score

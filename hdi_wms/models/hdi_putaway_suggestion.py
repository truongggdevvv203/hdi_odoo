# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class HdiPutawaySuggestion(models.Model):
    _name = 'hdi.putaway.suggestion'
    _description = 'Putaway Location Suggestion'
    _order = 'priority, score desc'

    # ===== REFERENCE =====
    batch_id = fields.Many2one(
        'hdi.batch',
        string='Lô hàng',
        required=True,
        ondelete='cascade',
    )

    product_id = fields.Many2one(
        'product.product',
        string='Sản phẩm',
        required=True,
    )

    quantity = fields.Float(
        string='Số lượng',
        required=True,
    )

    # ===== SUGGESTED LOCATION =====
    location_id = fields.Many2one(
        'stock.location',
        string='Vị trí đề xuất',
        required=True,
        domain="[('usage', '=', 'internal'), ('is_putable', '=', True)]"
    )

    location_display = fields.Char(
        related='location_id.complete_name',
        string='Vị trí',
    )

    coordinates = fields.Char(
        related='location_id.coordinate_display',
        string='Tọa độ',
    )

    # ===== SCORING =====
    score = fields.Float(
        string='Điểm',
        help="Điểm gợi ý (cao hơn = phù hợp hơn)",
        digits=(16, 2),
    )

    priority = fields.Integer(
        related='location_id.location_priority',
        string='Ưu tiên',
        store=True,
    )

    # ===== CAPACITY CHECK =====
    available_capacity = fields.Float(
        compute='_compute_capacity_info',
        string='Dung lượng còn lại',
    )

    capacity_sufficient = fields.Boolean(
        compute='_compute_capacity_info',
        string='Dung lượng đủ',
    )

    # ===== REASONS =====
    match_reasons = fields.Text(
        string='Lý do phù hợp',
        help="Lý do hệ thống đề xuất vị trí này"
    )

    warning_messages = fields.Text(
        string='Cảnh báo',
        help="Các vấn đề có thể có với vị trí này"
    )

    # ===== STATUS =====
    state = fields.Selection([
        ('suggested', 'Được đề xuất'),
        ('selected', 'Đã chọn'),
        ('rejected', 'Bị loại'),
    ], string='State', default='suggested')

    @api.depends('location_id', 'product_id', 'quantity')
    def _compute_capacity_info(self):
        """Check if location has sufficient capacity"""
        for suggestion in self:
            if suggestion.location_id and suggestion.product_id:
                suggestion.capacity_sufficient = suggestion.location_id.get_available_capacity_for_product(
                    suggestion.product_id,
                    suggestion.quantity
                )
                suggestion.available_capacity = suggestion.location_id.available_volume
            else:
                suggestion.capacity_sufficient = False
                suggestion.available_capacity = 0.0

    @api.model
    def generate_suggestions(self, batch, max_suggestions=5):

        if not batch.product_id:
            raise UserError(_('Lô phải có sản phẩm để hệ thống gợi ý vị trí.'))

        product = batch.product_id
        # Use actual quantity from quants if available, otherwise use planned quantity
        quantity = batch.total_quantity or batch.planned_quantity or 0

        if quantity <= 0:
            raise UserError(_('Lô phải có số lượng (dự kiến hoặc thực tế) để gợi ý vị trí.'))

        # Find suitable locations
        candidate_locations = self.env['stock.location'].search([
            ('usage', '=', 'internal'),
            ('is_putable', '=', True),
            ('company_id', '=', batch.company_id.id),
        ])

        suggestions = []
        for location in candidate_locations:
            # Skip if no capacity
            if not location.get_available_capacity_for_product(product, quantity):
                continue

            # Calculate score
            score = 0
            reasons = []
            warnings = []

            # 1. Same product exists (consolidation bonus)
            existing_quants = location.quant_ids.filtered(
                lambda q: q.product_id == product
            )
            if existing_quants:
                score += 50
                reasons.append('Có cùng sản phẩm đang lưu tại đây (hợp nhất)')

            # 2. Moving class match
            if location.moving_class and hasattr(product, 'abc_classification'):
                if product.abc_classification == location.moving_class:
                    score += 30
                    reasons.append('Nhóm di chuyển phù hợp')
                else:
                    score -= 10
                    warnings.append('Nhóm di chuyển không phù hợp')

            # 3. Priority
            score += (100 - location.location_priority)

            # 4. Empty location bonus
            if not location.quant_ids:
                score += 20
                reasons.append('Vị trí trống')

            # 5. Temperature zone match
            if hasattr(product, 'storage_temperature') and product.storage_temperature == location.temperature_zone:
                score += 15
                reasons.append('Vùng nhiệt độ phù hợp')

            # 6. Capacity usage (prefer locations with good fit)
            if location.max_volume:
                required_volume = product.volume * quantity
                fit_ratio = required_volume / location.max_volume
                if 0.3 <= fit_ratio <= 0.8:  # Good fit
                    score += 10
                    reasons.append('Kích thước phù hợp với dung lượng')

            suggestions.append({
                'batch_id': batch.id,
                'product_id': product.id,
                'quantity': quantity,
                'location_id': location.id,
                'score': score,
                'match_reasons': '\n'.join(reasons),
                'warning_messages': '\n'.join(warnings) if warnings else False,
                'state': 'suggested',
            })

        # Sort by score and limit
        suggestions = sorted(suggestions, key=lambda s: (-s['score'], s['location_id']))
        suggestions = suggestions[:max_suggestions]

        # Create suggestion records
        suggestion_records = self.env['hdi.putaway.suggestion'].create(suggestions)

        return suggestion_records

    def action_select(self):
        """
        Select this location for putaway
        ✅ Update batch.location_dest_id (which will update stock.location)
        """
        self.ensure_one()

        if not self.capacity_sufficient:
            raise UserError(_('Vị trí được chọn không có đủ dung lượng.'))

        # Update batch destination
        self.batch_id.write({
            'location_dest_id': self.location_id.id,
        })

        # Mark this as selected, others as rejected
        self.state = 'selected'
        self.search([
            ('batch_id', '=', self.batch_id.id),
            ('id', '!=', self.id),
        ]).write({'state': 'rejected'})

        return {
            'type': 'ir.actions.act_window_close',
            'infos': {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Đã chọn vị trí'),
                    'message': _('Vị trí lưu kho đã được đặt là %s') % self.location_id.complete_name,
                    'type': 'success',
                    'sticky': False,
                }
            }
        }

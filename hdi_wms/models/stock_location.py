# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class StockLocation(models.Model):
    _inherit = 'stock.location'

    # ===== WAREHOUSE COORDINATES =====
    coordinate_x = fields.Integer(
        string='Coordinate X',
        help="X coordinate in warehouse grid (aisle/row)"
    )

    coordinate_y = fields.Integer(
        string='Coordinate Y',
        help="Y coordinate in warehouse grid (column)"
    )

    coordinate_z = fields.Integer(
        string='Coordinate Z',
        help="Z coordinate (height level/shelf)"
    )

    coordinate_display = fields.Char(
        compute='_compute_coordinate_display',
        string='Coordinates',
        store=True,
        help="Display format: X-Y-Z"
    )

    # ===== PHYSICAL ATTRIBUTES =====
    max_weight = fields.Float(
        string='Max Weight (kg)',
        digits='Stock Weight',
        help="Maximum weight capacity"
    )

    max_volume = fields.Float(
        string='Max Volume (m³)',
        digits=(16, 4),
        help="Maximum volume capacity"
    )

    current_weight = fields.Float(
        compute='_compute_current_capacity',
        string='Current Weight (kg)',
        digits='Stock Weight',
        store=True,
    )

    current_volume = fields.Float(
        compute='_compute_current_capacity',
        string='Current Volume (m³)',
        digits=(16, 4),
        store=True,
    )

    available_weight = fields.Float(
        compute='_compute_available_capacity',
        string='Available Weight (kg)',
        store=True,
    )

    available_volume = fields.Float(
        compute='_compute_available_capacity',
        string='Available Volume (m³)',
        store=True,
    )

    capacity_percentage = fields.Float(
        compute='_compute_capacity_percentage',
        string='Capacity Used (%)',
        store=True,
    )

    # ===== WMS CLASSIFICATION =====
    moving_class = fields.Selection([
        ('a', 'Class A - Fast Moving'),
        ('b', 'Class B - Medium Moving'),
        ('c', 'Class C - Slow Moving'),
        ('d', 'Class D - Very Slow/Obsolete'),
    ], string='Moving Class',
        help="ABC analysis classification for optimal placement")

    location_priority = fields.Integer(
        string='Priority',
        default=10,
        help="Priority for putaway suggestion (1=highest, 99=lowest)"
    )

    # ===== WMS ATTRIBUTES =====
    is_pickable = fields.Boolean(
        string='Pickable',
        default=True,
        help="Can pick items from this location"
    )

    is_putable = fields.Boolean(
        string='Putable',
        default=True,
        help="Can put items into this location"
    )

    is_counted = fields.Boolean(
        string='Counted in Inventory',
        default=True,
        help="Include in inventory count"
    )

    is_mixed_product = fields.Boolean(
        string='Allow Mixed Products',
        default=True,
        help="Can store multiple products in same location"
    )

    is_mixed_batch = fields.Boolean(
        string='Allow Mixed Batches',
        default=True,
        help="Can store multiple batches in same location"
    )

    temperature_zone = fields.Selection([
        ('ambient', 'Ambient'),
        ('cool', 'Cool (2-8°C)'),
        ('frozen', 'Frozen (-18°C)'),
        ('cold', 'Cold Room (0-4°C)'),
    ], string='Temperature Zone')

    storage_type = fields.Selection([
        ('floor', 'Floor Storage'),
        ('rack', 'Rack/Shelf'),
        ('pallet', 'Pallet Rack'),
        ('bin', 'Bin Location'),
        ('bulk', 'Bulk Storage'),
    ], string='Storage Type')

    # ===== BATCHES IN LOCATION =====
    batch_ids = fields.One2many(
        'hdi.batch',
        'location_id',
        string='Batches',
        help="All batches currently in this location"
    )

    batch_count = fields.Integer(
        compute='_compute_batch_count',
        string='Batch Count',
    )

    # ===== PUTAWAY RULES =====
    putaway_sequence = fields.Integer(
        string='Putaway Sequence',
        default=10,
        help="Sequence for putaway suggestion (lower = higher priority)"
    )

    @api.depends('coordinate_x', 'coordinate_y', 'coordinate_z')
    def _compute_coordinate_display(self):
        """Format coordinates as X-Y-Z"""
        for location in self:
            if location.coordinate_x or location.coordinate_y or location.coordinate_z:
                location.coordinate_display = '%s-%s-%s' % (
                    location.coordinate_x or '0',
                    location.coordinate_y or '0',
                    location.coordinate_z or '0',
                )
            else:
                location.coordinate_display = False

    @api.depends('batch_ids', 'batch_ids.weight', 'batch_ids.volume')
    def _compute_current_capacity(self):
        for location in self:
            location.current_weight = sum(location.batch_ids.mapped('weight'))
            location.current_volume = sum(location.batch_ids.mapped('volume'))

    @api.depends('max_weight', 'current_weight', 'max_volume', 'current_volume')
    def _compute_available_capacity(self):
        """Calculate available capacity"""
        for location in self:
            location.available_weight = (location.max_weight or 0) - location.current_weight
            location.available_volume = (location.max_volume or 0) - location.current_volume

    @api.depends('max_volume', 'current_volume')
    def _compute_capacity_percentage(self):
        """Calculate capacity usage percentage"""
        for location in self:
            if location.max_volume:
                location.capacity_percentage = (
                        location.current_volume / location.max_volume * 100
                )
            else:
                location.capacity_percentage = 0.0

    @api.depends('batch_ids')
    def _compute_batch_count(self):
        """Count batches in location"""
        for location in self:
            location.batch_count = len(location.batch_ids)

    def action_view_batches(self):
        """View all batches in this location"""
        self.ensure_one()
        return {
            'name': _('Batches in %s') % self.complete_name,
            'type': 'ir.actions.act_window',
            'res_model': 'hdi.batch',
            'view_mode': 'list,form,kanban',
            'domain': [('location_id', '=', self.id)],
            'context': {'default_location_id': self.id},
        }

    def get_available_capacity_for_product(self, product, quantity):
        self.ensure_one()

        if not self.is_putable:
            return False

        # Check volume capacity if defined
        if self.max_volume and product.volume:
            required_volume = product.volume * quantity
            if self.available_volume < required_volume:
                return False

        # Check weight capacity if defined
        if self.max_weight and product.weight:
            required_weight = product.weight * quantity
            if self.available_weight < required_weight:
                return False

        # Check mixed product rule
        if not self.is_mixed_product:
            existing_products = self.quant_ids.mapped('product_id')
            if existing_products and product not in existing_products:
                return False

        return True

    @api.constrains('coordinate_x', 'coordinate_y', 'coordinate_z')
    def _check_coordinates_unique(self):
        for location in self:
            if location.coordinate_x or location.coordinate_y or location.coordinate_z:
                duplicate = self.search([
                    ('id', '!=', location.id),
                    ('coordinate_x', '=', location.coordinate_x),
                    ('coordinate_y', '=', location.coordinate_y),
                    ('coordinate_z', '=', location.coordinate_z),
                    ('location_id', '=', location.location_id.id),  # Same parent
                    ('usage', '=', 'internal'),
                ], limit=1)
                if duplicate:
                    raise ValidationError(_(
                        'Coordinates %s are already used by location %s'
                    ) % (location.coordinate_display, duplicate.complete_name))

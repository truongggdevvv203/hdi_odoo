# -*- coding: utf-8 -*-

from odoo import models, fields


class ProductProduct(models.Model):

    _inherit = 'product.product'
    
    abc_classification = fields.Selection([
        ('a', 'Class A - Fast Moving'),
        ('b', 'Class B - Medium Moving'),
        ('c', 'Class C - Slow Moving'),
        ('d', 'Class D - Very Slow/Obsolete'),
    ], string='ABC Classification', 
       help="Moving class for WMS putaway strategy")
    
    storage_temperature = fields.Selection([
        ('ambient', 'Ambient'),
        ('cool', 'Cool (2-8°C)'),
        ('frozen', 'Frozen (-18°C)'),
        ('cold', 'Cold Room (0-4°C)'),
    ], string='Storage Temperature', 
       help="Required storage temperature")
    
    batch_count = fields.Integer(
        compute='_compute_batch_count',
        string='Batches',
        help="Number of batches containing this product"
    )
    
    def _compute_batch_count(self):
        for product in self:
            product.batch_count = self.env['hdi.batch'].search_count([
                ('product_id', '=', product.id),
                ('state', '!=', 'cancel'),
            ])

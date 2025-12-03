# -*- coding: utf-8 -*-
from odoo import models, api

class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model
    def get_current_user_id(self):
        """Helper method to get current user ID for JavaScript"""
        return self.env.uid
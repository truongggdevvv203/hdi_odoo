from odoo import models, fields


class HrDepartment(models.Model):
    _inherit = 'hr.department'

    # Department Extensions
    department_code = fields.Char(
        string='Mã phòng ban',
        unique=True,
        help='Mã định danh duy nhất cho phòng ban'
    )

    head_id = fields.Many2one(
        'hr.employee',
        string='Trưởng phòng',
        domain="[('company_id', '=', company_id)]"
    )

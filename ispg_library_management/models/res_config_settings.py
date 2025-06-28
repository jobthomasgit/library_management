from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    library_default_return_days = fields.Integer(
        string="Default Return Days",
        help="Default number of days to return a book",
        related='company_id.library_default_return_days', readonly=False
    )
    library_penalty_per_day = fields.Float(
        string="Penalty per Day",
        help="Penalty amount per day when book is returned late",
        related='company_id.library_penalty_per_day', readonly=False
    )

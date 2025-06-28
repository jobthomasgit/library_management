from odoo import models, fields, api


class ResCompany(models.Model):
    _inherit = "res.company"

    library_default_return_days = fields.Integer(
        string="Default Return Days",
        help="Default number of days to return a book",
    )
    library_penalty_per_day = fields.Float(
        string="Penalty per Day",
        help="Penalty amount per day when book is returned late",
    )

    @api.model_create_multi
    def create(self, vals_list):
        companies = super().create(vals_list)
        for company in companies:
            # Create library member sequence
            self.env['ir.sequence'].sudo().create(
                {
                    'name': 'Library Member',
                    'code': 'library.member.seq',
                    'prefix': 'MEM',
                    'padding': 5,
                    'company_id': company.id,
                }
            )
            # Create book move sequence
            self.env['ir.sequence'].sudo().create(
                {
                    'name': 'Book Move',
                    'code': 'book.move.seq',
                    'prefix': 'BM',
                    'padding': 5,
                    'company_id': company.id,
                }
            )
        return companies

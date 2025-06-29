from odoo import models, fields, api

class AccountMove(models.Model):
    _inherit = 'account.move'

    is_membership_renewal = fields.Boolean(string='Is Membership Renewal', copy=False)
    is_penalty = fields.Boolean(string='Is Penalty', copy=False)
    book_move_id = fields.Many2one('book.move', string='Book Move Reference', copy=False)
    recurring_invoice_id = fields.Many2one('recurring.invoice', string='Recurring Invoice', copy=False)
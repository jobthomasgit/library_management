from odoo import models, fields, api
from datetime import datetime, timedelta

from odoo.api import ondelete


class BookMove(models.Model):
    _name = "book.move"
    _description = "Book Borrow"
    _order = "create_date desc"

    name = fields.Char(string="Reference", readonly=True, copy=False)
    book_id = fields.Many2one("library.book", string="Book", required=True, ondelete='restrict',
                              domain=[("availability_status", "=", "available")])
    member_id = fields.Many2one("res.partner", string="Member", required=True, ondelete='restrict',
                                domain=[("is_library_member", "=", True)])
    issue_date = fields.Date(string="Issue Date", required=True, default=fields.Date.today)
    return_date = fields.Date(string="Return Date", required=True)
    actual_return_date = fields.Date(string="Actual Return Date", readonly=True)
    state = fields.Selection([
        ("draft", "Draft"),
        ("borrowed", "Borrowed"),
        ("expired", "Expired"),
        ("returned", "Returned")
    ], string="Status", default="draft", required=True)
    return_days = fields.Integer(string="Return Days")
    penalty_per_day = fields.Float(string="Penalty per Day")
    late_returns = fields.Boolean()
    late_return_penalty = fields.Float()
    penalty_paid = fields.Boolean(compute="_compute_penalty_paid")
    notes = fields.Text(string="Notes")
    company_id = fields.Many2one("res.company", default=lambda self: self.env.company)

    @api.model
    def create(self, vals):
        if not vals.get("name"):
            vals["name"] = self.env["ir.sequence"].next_by_code("book.move.seq")
        return super().create(vals)

    def _compute_penalty_paid(self):
        for record in self:
            move_ids = self.env["account.move"].search([('book_move_id', '=', record.id)])
            record.penalty_paid = True if move_ids else False

    @api.onchange("book_id")
    def _onchange_book_id(self):
        self.return_days = self.book_id.default_return_days
        self.penalty_per_day = self.book_id.penalty_per_day

    @api.onchange("book_id", "issue_date")
    def _get_return_date(self):
        if self.book_id and self.issue_date:
            self.return_date = self.issue_date + timedelta(days=self.return_days or 14)

    def action_borrow(self):
        if self.book_id.available_copies > 0:
            self.book_id.available_copies -= 1
            self.state = "borrowed"
        else:
            raise models.ValidationError("No copies available for borrowing.")

    def action_return(self):
        self.book_id.available_copies += 1
        self.actual_return_date = fields.Date.today()
        self.state = "returned"
        if self.actual_return_date > self.return_date:
            self.late_returns = True
            self.calculate_late_penalty()

    def action_expire(self):
        self.state = "expired"
        self.late_returns = True

    def calculate_late_penalty(self):
        if self.late_returns:
            late_date = self.actual_return_date - self.return_date
            late_days = late_date.days
            self.late_return_penalty = self.penalty_per_day * late_days

    def action_pay_penalty(self):
        """Create penalty invoice and payment"""
        self.ensure_one()
        
        if not self.late_return_penalty or self.late_return_penalty <= 0:
            raise models.ValidationError("No penalty amount to pay.")
        
        # Create penalty invoice
        invoice_vals = {
            'partner_id': self.member_id.id,
            'move_type': 'out_invoice',
            'state': 'draft',
            'invoice_date': fields.Date.today(),
            'is_penalty': True,  # Mark as penalty invoice
            'book_move_id': self.id,  # Reference to this book move
            'invoice_line_ids': [(0, 0, {
                'name': f'Late Return Penalty - {self.book_id.name}',
                'quantity': 1,
                'price_unit': self.late_return_penalty,
                'account_id': self.env['account.account'].search([('account_type', '=', 'income')], limit=1).id,
            })],
        }
        
        invoice = self.env['account.move'].create(invoice_vals)
        invoice.action_post()
        
        # Create payment
        payment_vals = {
            'partner_id': self.member_id.id,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'amount': self.late_return_penalty,
            'currency_id': self.env.company.currency_id.id,
            'payment_method_id': self.env['account.payment.method'].search([('payment_type', '=', 'inbound')], limit=1).id,
            'journal_id': self.env['account.journal'].search([('type', '=', 'bank')], limit=1).id,
            'date': fields.Date.today(),
        }
        
        payment = self.env['account.payment'].create(payment_vals)
        
        # Post the payment
        payment.action_post()
        
        # Reconcile payment with invoice
        lines_to_reconcile = invoice.line_ids.filtered(lambda line: line.account_id.account_type in ('asset_receivable', 'liability_payable'))
        payment_lines = payment.move_id.line_ids.filtered(lambda line: line.account_id.account_type in ('asset_receivable', 'liability_payable'))
        
        if lines_to_reconcile and payment_lines:
            (lines_to_reconcile + payment_lines).reconcile()
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Penalty Invoice',
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
            'target': 'current',
        }

    @api.model
    def _check_expired_books_issue(self):
        """Cron job to check and mark expired books issue"""
        today = fields.Date.today()
        expired_moves = self.search([
            ("state", "=", "borrowed"),
            ("return_date", "<", today)
        ])
        expired_moves.write(
            {
                "state": "expired",
                "late_returns": True
            }
        )

from odoo import models, fields, api
from datetime import datetime, timedelta

class LibraryBook(models.Model):
    _name = "library.book"
    _description = "Library Book"

    def _get_default_return_days(self):
        return int(self.env['ir.config_parameter'].sudo().get_param('ispg_library_management.default_return_days', 14))

    def _get_default_penalty_per_day(self):
        return float(self.env['ir.config_parameter'].sudo().get_param('ispg_library_management.penalty_per_day', 1.0))

    name = fields.Char(string="Title", required=True)
    author_id = fields.Many2one("book.author", string="Author", required=True)
    isbn = fields.Char(string="ISBN", required=True)
    total_copies = fields.Integer(string="Total Copies", default=1)
    available_copies = fields.Integer(string="Available Copies", default=1)
    availability_status = fields.Selection([
        ("available", "Available"),
        ("unavailable", "Unavailable")
    ], string="Availability Status", compute="_compute_availability_status", store=True)
    image = fields.Image(string="Book Cover")
    area = fields.Char(string="Area", help="Define the area where the book is available in the library")
    company_id = fields.Many2one("res.company",default=lambda self: self.env.company)
    default_return_days = fields.Integer(string="Default Return Days", default=lambda self: self.env.company.library_default_return_days)
    penalty_per_day = fields.Float(string="Penalty per Day", default=lambda self: self.env.company.library_penalty_per_day)
    book_move_counts = fields.Integer(compute="_compute_book_move_counts")
    book_move_ids = fields.One2many("book.move", "book_id")

    _sql_constraints = [
        ('isbn_uniq', 'unique (company_id, isbn)', 'The isbn must be unique!')
    ]

    @api.depends("available_copies")
    def _compute_availability_status(self):
        for record in self:
            record.availability_status = "available" if record.available_copies > 0 else "unavailable"

    @api.onchange("total_copies")
    def set_available_copies(self):
        borrowed_book_move_ids = self.book_move_ids.filtered(lambda s: s.state not in ['draft', 'expired'])
        self.available_copies = self.total_copies - len(borrowed_book_move_ids)

    def _compute_book_move_counts(self):
        for record in self:
            record.book_move_counts = len(record.book_move_ids)

    def action_create_borrow(self):
        """Create a book borrow record from the book form"""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Borrow Book",
            "res_model": "book.move",
            "view_mode": "form",
            "target": "current",
            "context": {
                "default_book_id": self.id,
                "default_issue_date": fields.Date.today(),
            }
        }

    def action_view_book_moves(self):
        """Show all book moves related to this book"""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": f"Book Moves - {self.name}",
            "res_model": "book.move",
            "view_mode": "list,form",
            "domain": [("book_id", "=", self.id)],
            "context": {
                "default_book_id": self.id,
            }
        }

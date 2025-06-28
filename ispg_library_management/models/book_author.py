from odoo import models, fields

class BookAuthor(models.Model):
    _name = "book.author"
    _description = "Book Author"

    name = fields.Char(string="Name", required=True) 
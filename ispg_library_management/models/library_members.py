from odoo import models, fields, api
from datetime import date, timedelta

class ResPartner(models.Model):
    _inherit = "res.partner"

    is_library_member = fields.Boolean(string="Is Library Member")
    contact = fields.Char(string="Contact")
    membership_id = fields.Char(string="Membership ID", readonly=True, copy=False)
    membership_start_date = fields.Date(string="Membership Start Date")
    membership_end_date = fields.Date(string="Membership End Date")
    membership_status = fields.Selection([
        ('active', 'Active'),
        ('expired', 'Expired'),
    ], string="Membership Status", default='active')
    book_move_counts = fields.Integer(compute="_compute_book_move_counts")
    book_move_ids = fields.One2many("book.move", "member_id")
    membership_invoice_count = fields.Integer(compute="_compute_invoice_counts")
    penalty_invoice_count = fields.Integer(compute="_compute_invoice_counts")

    def _compute_book_move_counts(self):
        for record in self:
            record.book_move_counts = len(record.book_move_ids)

    def _compute_invoice_counts(self):
        for record in self:
            # Count membership renewal invoices
            membership_invoices = self.env['account.move'].search([
                ('partner_id', '=', record.id),
                ('is_membership_renewal', '=', True),
                ('move_type', '=', 'out_invoice')
            ])
            record.membership_invoice_count = len(membership_invoices)
            
            # Count penalty invoices
            penalty_invoices = self.env['account.move'].search([
                ('partner_id', '=', record.id),
                ('is_penalty', '=', True),
                ('move_type', '=', 'out_invoice')
            ])
            record.penalty_invoice_count = len(penalty_invoices)

    def action_view_book_moves(self):
        """Show all book moves related to this member"""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": f"Book Borrow History - {self.name}",
            "res_model": "book.move",
            "view_mode": "list,form",
            "domain": [("member_id", "=", self.id)],
            "context": {
                "default_member_id": self.id,
            }
        }

    def action_renew_membership(self):
        """Open membership renewal wizard"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Renew Membership',
            'res_model': 'membership.renew.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_partner_id': self.id,
            }
        }

    def action_view_membership_invoices(self):
        """Show all membership renewal invoices for this member"""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": f"Membership Renewal Invoices - {self.name}",
            "res_model": "account.move",
            "view_mode": "list,form",
            "domain": [
                ("partner_id", "=", self.id),
                ("is_membership_renewal", "=", True),
                ("move_type", "=", "out_invoice")
            ],
            "context": {
                "default_partner_id": self.id,
                "default_is_membership_renewal": True,
                "default_move_type": "out_invoice",
            }
        }

    def action_view_penalty_invoices(self):
        """Show all penalty invoices for this member"""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": f"Penalty Invoices - {self.name}",
            "res_model": "account.move",
            "view_mode": "list,form",
            "domain": [
                ("partner_id", "=", self.id),
                ("is_penalty", "=", True),
                ("move_type", "=", "out_invoice")
            ],
            "context": {
                "default_partner_id": self.id,
                "default_is_penalty": True,
                "default_move_type": "out_invoice",
            }
        }

    @api.model
    def _check_membership_expiry(self):
        """Cron job to check and update expired memberships and send notifications"""
        today = date.today()
        expired_members = self.search([
            ('is_library_member', '=', True),
            ('membership_end_date', '<', today),
            ('membership_status', '!=', 'expired')
        ])

        if expired_members:
            expired_members.write({'membership_status': 'expired'})
            
            # Send notifications to library managers
            managers = self.env['res.users'].search([
                ('groups_id', 'in', [self.env.ref('ispg_library_management.group_library_manager').id])
            ])
            
            for member in expired_members:
                for manager in managers:
                    self._send_expired_member_notification(member, manager)

    def _send_expired_member_notification(self, member, user):
        """Send notification for expired member"""
        # Get or create activity type
        activity_type = self.env.ref('mail.mail_activity_data_todo')
        if not activity_type:
            activity_type = self.env['mail.activity.type'].search([], limit=1)
        
        if activity_type:
            # Create an activity for the notification
            activity_vals = {
                'activity_type_id': activity_type.id,
                'res_model_id': self.env['ir.model']._get('res.partner').id,
                'res_id': member.id,
                'user_id': user.id,
                'summary': 'Member Expired',
                'note': f'Member "{member.name}" membership has expired on {member.membership_end_date}',
                'date_deadline': fields.Date.today(),
            }
            
            self.env['mail.activity'].create(activity_vals)

    @api.model
    def create(self, vals):
        res = super().create(vals)
        if not res.membership_id and res.is_library_member:
            res.membership_id = self.env["ir.sequence"].next_by_code("library.member.seq")
        return res

    def write(self, vals):
        res = super().write(vals)
        if not self.membership_id and self.is_library_member:
            self.membership_id = self.env["ir.sequence"].next_by_code("library.member.seq")
        return res
from odoo import models, fields, api
from datetime import datetime, timedelta

class RecurringInvoice(models.Model):
    _name = "recurring.invoice"
    _description = "Recurring Invoice Configuration"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "create_date desc"

    name = fields.Char(string="Name", required=True, copy=False, readonly=True, default="New")
    member_id = fields.Many2one("res.partner", string="Member", required=True, 
                                domain=[("is_library_member", "=", True)])
    start_date = fields.Date(string="Start Date", required=True)
    end_date = fields.Date(string="End Date", required=True)
    validity_days = fields.Integer(string="Validity Days", required=True, default=365,
                                  help="Number of days for the next membership period")
    membership_fee = fields.Float(string="Membership Fee", required=True, default=50.0,
                                 help="Fee amount for membership renewal")
    active = fields.Boolean(string="Active", default=True)
    company_id = fields.Many2one("res.company", default=lambda self: self.env.company)
    notes = fields.Text(string="Notes")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('expired', 'Expired')
    ], string="Status", default='draft', tracking=True)

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('recurring.invoice.seq') or 'New'
        return super().create(vals)

    @api.onchange('member_id')
    def _onchange_member_id(self):
        """Update start and end dates when member is selected"""
        if self.member_id:
            self.start_date = self.member_id.membership_start_date
            self.end_date = self.member_id.membership_end_date

    def action_activate(self):
        """Activate the recurring invoice"""
        self.ensure_one()
        self.state = 'active'

    def action_expire(self):
        """Mark as expired"""
        self.ensure_one()
        self.state = 'expired'

    @api.model
    def _process_recurring_renewals(self):
        """Cron job to process recurring renewals"""
        today = fields.Date.today()
        
        # Find active recurring records where member end date is approaching or passed
        recurring_records = self.search([
            ('state', '=', 'active'),
            ('member_id.membership_end_date', '<=', today),
            ('member_id.is_library_member', '=', True)
        ])
        
        for record in recurring_records:
            # Calculate new dates
            new_start_date = today
            new_end_date = today + timedelta(days=record.validity_days)

            # Update member membership
            record.member_id.write({
                'membership_start_date': new_start_date,
                'membership_end_date': new_end_date,
                'membership_status': 'active'
            })

            # Update recurring record dates
            record.write({
                'start_date': new_start_date,
                'end_date': new_end_date
            })

            # Create renewal invoice
            self._create_renewal_invoice(record)

            # Log the renewal
            record.message_post(
                body=f"Automatic renewal processed. New membership period: {new_start_date} to {new_end_date}"
            )

    def _create_renewal_invoice(self, recurring_record):
        """Create renewal invoice for the member"""
        invoice_vals = {
            'partner_id': recurring_record.member_id.id,
            'move_type': 'out_invoice',
            'state': 'draft',
            'invoice_date': fields.Date.today(),
            'is_membership_renewal': True,
            'recurring_invoice_id': recurring_record.id,
            'invoice_line_ids': [(0, 0, {
                'name': f'Membership Renewal - {recurring_record.member_id.name}',
                'quantity': 1,
                'price_unit': recurring_record.membership_fee,
                'account_id': self.env['account.account'].search([('account_type', '=', 'income')], limit=1).id,
            })],
        }
        
        invoice = self.env['account.move'].create(invoice_vals)
        return invoice
from odoo import models, fields, api
from datetime import date, timedelta

class MembershipRenewWizard(models.TransientModel):
    _name = 'membership.renew.wizard'
    _description = 'Membership Renewal Wizard'

    partner_id = fields.Many2one('res.partner', string='Member', required=True)
    membership_start_date = fields.Date(string='Membership Start Date', required=True, default=fields.Date.today)
    membership_end_date = fields.Date(string='Membership End Date', required=True)
    create_invoice = fields.Boolean(string='Create Invoice', default=False)
    invoice_amount = fields.Float(string='Invoice Amount', default=100.0)

    @api.model
    def default_get(self, fields_list):
        """Set default values when wizard opens"""
        res = super().default_get(fields_list)
        if self.env.context.get('active_id'):
            partner = self.env['res.partner'].browse(self.env.context.get('active_id'))
            res.update({
                'partner_id': partner.id,
                'membership_start_date': date.today(),
                'membership_end_date': date.today() + timedelta(days=365),  # Default 1 year
            })
        return res

    def action_renew_without_invoice(self):
        """Renew membership without creating invoice"""
        self.ensure_one()
        
        # Update partner membership dates
        self.partner_id.write({
            'membership_start_date': self.membership_start_date,
            'membership_end_date': self.membership_end_date,
            'membership_status': 'active',
        })
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success',
                'message': f'Membership renewed successfully for {self.partner_id.name}',
                'type': 'success',
            }
        }

    def action_renew_with_invoice(self):
        """Renew membership and create draft invoice"""
        self.ensure_one()
        
        # Create draft invoice
        invoice_vals = {
            'partner_id': self.partner_id.id,
            'move_type': 'out_invoice',
            'state': 'draft',
            'invoice_date': date.today(),
            'is_membership_renewal': True,  # Mark as membership renewal
            'invoice_line_ids': [(0, 0, {
                'name': f'Library Membership Renewal - {self.partner_id.name}',
                'quantity': 1,
                'price_unit': self.invoice_amount,
                'account_id': self.env['account.account'].search([('account_type', '=', 'income')], limit=1).id,
            })],
        }
        
        invoice = self.env['account.move'].create(invoice_vals)
        
        # Update partner membership dates
        self.partner_id.write({
            'membership_start_date': self.membership_start_date,
            'membership_end_date': self.membership_end_date,
            'membership_status': 'active',
        })

        return {
            'type': 'ir.actions.act_window',
            'name': 'Membership Invoice',
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
            'target': 'current',
        } 
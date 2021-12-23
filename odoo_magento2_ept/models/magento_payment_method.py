# -*- coding: utf-8 -*-
"""
Describes Magento Payment Methods
"""
from odoo import models, api, fields


class MagentoPaymentMethod(models.Model):
    """
    Describes Magento Payment Methods
    """
    _name = 'magento.payment.method'
    _description = 'Magento Payment Method'
    _rec_name = 'payment_method_name'

    @api.model
    @api.returns('res.company')
    def _default_company_id(self):
        """
        Returns Default Company Id
        :return: Default company id
        """
        # return self.env['res.company']._company_default_get('magento.payment.method')
        return self.env.company

    magento_instance_id = fields.Many2one(
        'magento.instance',
        'Instance',
        ondelete='cascade',
        help="This field relocates magento instance"
    )
    payment_method_code = fields.Char(string='Payments Method Code', help='Payment Method Code')
    payment_method_name = fields.Char(string='Payments Method Name', help='Payment Method Name')
    payment_term_id = fields.Many2one(
        'account.payment.term',
        string='Payment Term',
        help="Default payment term of a sale order using this method.",
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=_default_company_id,
        help="Magento Company Id.",
    )
    magento_workflow_process_id = fields.Many2one(
        'sale.workflow.process.ept',
        string='Automatic Workflow',
        help="Workflow for Order"
    )
    create_invoice_on = fields.Selection(
        [
            ('open', 'Validate'),
            ('paid', 'Paid'),
            ('na', 'N/A')
        ],
        string='Create Invoice on action',
        default="na",
        help="Should the invoice be created in Magento "
             "when it is validated or when it is paid in odoo?\n",
    )

    days_before_cancel = fields.Integer(
        string='Import Past Orders Of X Days',
        default=30,
        help="After 'n' days, if the 'Import Rule' is not fulfilled, the "
             "import of the sales order will be canceled.",
    )
    import_rule = fields.Selection(
        [
            ('always', 'Always'),
            ('never', 'Never'),
            ('paid', 'Paid')
        ],
        string="Import Rules",
        default='always',
        required=True,
        help="Import Rule for Sale Order.\n \n "
             "[Always] : This Payment Method's Order will always import\n "
             "[Paid]:If Order is Paid On Magento then and then import \n "
             "[Never] : This Payment Method Order will never imported \n "
    )

    register_payment = fields.Selection(
        [
            ('advance_payment', 'Advance Payment'),
            ('invoice_payment', 'Payment Against Invoice')
        ],
        string="Register Payment As",
        default='invoice_payment',
        help="Register Payment either Advance Payment or Payment Against Invoice"
    )
    active = fields.Boolean(string="Status", default=True)

    _sql_constraints = [
        ('unique_payment_method_code', 'unique(magento_instance_id,payment_method_code)',
         'This payment method code is already exist')]

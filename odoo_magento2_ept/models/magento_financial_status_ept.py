# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class MagentoFinancialStatusEpt(models.Model):
    _name = "magento.financial.status.ept"
    _description = 'Magento Financial Status'

    def _default_payment_term(self):
        payment_term = self.env.ref("account.account_payment_term_immediate")
        return payment_term.id if payment_term else False

    financial_status = fields.Selection([('not_paid', 'Pending Orders'),
                                         ('processing_paid', 'Processing orders with Invoice'),
                                         ('processing_unpaid', 'Processing orders with Shipping'),
                                         ('paid', 'Completed orders'),
                                         ], default="not_paid")
    auto_workflow_id = fields.Many2one("sale.workflow.process.ept", "Auto Workflow")
    payment_method_id = fields.Many2one("magento.payment.method", "Payment Gateway", ondelete="restrict")
    payment_term_id = fields.Many2one('account.payment.term', string='Payment Term', default=_default_payment_term)
    magento_instance_id = fields.Many2one(
        "magento.instance", string="Instance", ondelete="cascade", help="This field relocates magento instance")
    active = fields.Boolean("Active Financial Status", default=True)

    _sql_constraints = [('_magento_workflow_unique_constraint',
                         'unique(financial_status,magento_instance_id,payment_method_id)',
                         "Financial status must be unique in the list")]

    def create_financial_status(self, magento_instance, financial_status):
        """
        Creates Financial Status for the payment methods of the Instance.
        :param magento_instance: Magento Instance
        :param financial_status: Financial Status can be pending, processing_paid, processing_unpaid or paid.
        :return: True
        """
        payment_methods = magento_instance.payment_method_ids
        for payment_method in payment_methods:
            existing_financial_status = self.search_or_create_financial_status(
                magento_instance, payment_method, financial_status)
            if existing_financial_status:
                continue
        return True

    @api.model
    def auto_create_financial_statuses(self):
        magento_instances = self.env['magento.instance'].search([])
        if magento_instances:
            for magento_instance in magento_instances:
                payment_methods = magento_instance.payment_method_ids
                for payment_method in payment_methods:
                    if payment_method.magento_workflow_process_id:
                        order_statuses = magento_instance.import_magento_order_status_ids.mapped('status')
                        financial_statuses = self.get_order_financial_status(order_statuses)
                        for financial_status in financial_statuses:
                            existing_financial_status = self.search_or_create_financial_status(
                                magento_instance, payment_method, financial_status)
                            if existing_financial_status:
                                continue
                    else:
                        existing_financial_status = self.search_or_create_financial_status(
                            magento_instance, payment_method, 'not_paid')
                        if existing_financial_status:
                            continue
        return True

    @staticmethod
    def get_order_financial_status(order_status):
        """
        Get Financial Status Dictionary.
        :param order_status: Order status received from Magento.
        :return: Financial Status dictionary
        """
        financial_status_code = []
        if "new" in order_status:
            financial_status_code.append('not_paid')
        if "processing" in order_status:
            financial_status_code.append('processing_paid')
            financial_status_code.append('processing_unpaid')
        if "complete" in order_status:
            financial_status_code.append('paid')
        return financial_status_code

    def search_or_create_financial_status(self, magento_instance, payment_method, financial_status):
        domain = [('magento_instance_id', '=', magento_instance.id),
                  ('payment_method_id', '=', payment_method.id),
                  ('financial_status', '=', financial_status)]

        existing_financial_status = self.search(domain).ids
        if existing_financial_status:
            return True

        if payment_method.magento_workflow_process_id:
            auto_workflow_record = payment_method.magento_workflow_process_id
        else:
            auto_workflow_record = self.env.ref("auto_invoice_workflow_ept.automatic_validation_ept")
        if payment_method.payment_term_id:
            payment_term_id = payment_method.payment_term_id
        else:
            payment_term_id = self.env.ref("account.account_payment_term_immediate")
        self.create({
            'magento_instance_id': magento_instance.id,
            'auto_workflow_id': auto_workflow_record.id,
            'payment_method_id': payment_method.id,
            'financial_status': financial_status,
            'payment_term_id': payment_term_id.id
        })
        return False

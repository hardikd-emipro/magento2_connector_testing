# -*- coding: utf-8 -*-
"""
Describes fields and methods for create/ update sale order
"""
import json
import pytz
import time
from datetime import datetime, timedelta
from odoo import models, fields, api, _
from odoo.exceptions import Warning
from .api_request import req, create_search_criteria
from ..python_library.php import Php
from dateutil import parser
utc = pytz.utc

MAGENTO_DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'


class SaleOrder(models.Model):
    """
    Describes fields and methods for create/ update sale order
    """
    _inherit = 'sale.order'
    _description = 'Sale Order'

    magento_instance_id = fields.Many2one(
        'magento.instance',
        string="Instance",
        help="This field relocates Magento Instance"
    )
    magento_order_id = fields.Char(string="Magento order Ids", help="Magento Order Id")
    magento_website_id = fields.Many2one(
        "magento.website",
        string="Magento Website",
        help="Magento Website"
    )
    magento_order_reference = fields.Char(
        string="Magento Orders Reference",
        help="Magento Order Reference"
    )
    store_id = fields.Many2one(
        'magento.storeview',
        string="Magento_store_view",
        help="Magento_store_view"
    )
    is_exported_to_magento_shipment_status = fields.Boolean(
        string="Is Order exported to Shipment Status",
        help="Is exported to Shipment Status"
    )
    magento_payment_method_id = fields.Many2one(
        'magento.payment.method',
        string="Magento Payment Method",
        help="Magento Payment Method"
    )
    magento_shipping_method_id = fields.Many2one(
        'magento.delivery.carrier',
        string="Magento Shipping Method",
        help="Magento Shipping Method"
    )

    def _cancel_order_exportable(self):
        if (self.invoice_ids and True in self.invoice_ids.mapped('is_exported_to_magento')) or \
                (self.picking_ids and self.picking_ids.filtered(lambda x:x.state=='done' and x.is_exported_to_magento).ids):
            self.is_cancel_order_exportable = True
        else:
            self.is_cancel_order_exportable = False
    is_cancel_order_exportable = fields.Boolean(string="Is Invoice exportable", compute='_cancel_order_exportable',
                                                store=False)
    @api.model
    def check_price_list_for_order_exit(
            self,
            magento_instance,
            order_response,
            order_data_queue_line_id
    ):
        """
        This method is used to check price list is exist or not in odoo.
        When import order from Magento to Odoo.
        :param magento_instance: Instance of Magento
        :param order_response: Order Response received from Magento
        :param order_data_queue_line_id: Order Data Queue line id
        :return: Pricelist
        """
        currency_obj = self.env['res.currency']
        pricelist_obj = self.env['product.pricelist']
        order_currency = order_response.get('order_currency_code')
        order_ref = order_response.get('increment_id')
        currency_id = currency_obj.search([('name', '=', order_currency),
            '|', ('active', '=', False), ('active', '=', True)], limit=1)
        if not currency_id.active:
            currency_id.write({'active': True})
        price_list = pricelist_obj.search([('currency_id', '=', currency_id.id)])
        if price_list:
            price_list = magento_instance.pricelist_id if magento_instance.pricelist_id in price_list else price_list[0]
        elif not price_list or price_list.currency_id != currency_id:
            message = "Order %s skiped due to pricelist not found for currency please synchronize metadata again." % order_ref
            self.create_common_log_error(
                magento_instance.id,
                message,
                order_ref,
                order_data_queue_line_id
            )
        return price_list

    def get_magento_shipping_method(self, magento_instance, order_response, job, order_data_queue_line_id):
        """
        This method is used to get shipping method.
        if shipping method not found it will create(base on carrier_code) new shipping method.
        :param magento_instance: Instance of Magento
        :param order_response: Order Response received from Magento
        :return:
        """
        magento_delivery_carrier_obj = self.env['magento.delivery.carrier']
        delivery_carrier_obj = self.env["delivery.carrier"]
        order_reference = order_response.get('increment_id')
        skip_order = False
        magento_carrier = False
        shipping = order_response.get('extension_attributes').get('shipping_assignments')
        shipping_method = shipping[0].get('shipping').get('method') or False
        if shipping_method:
            magento_carrier = magento_delivery_carrier_obj.search([
                ('carrier_code', '=', shipping_method),
                ('magento_instance_id', '=', magento_instance.id)
            ], limit=1)
            if not magento_carrier:
                magento_instance.import_delivery_method()
                magento_carrier = magento_delivery_carrier_obj.search([
                    ('carrier_code', '=', shipping_method),
                    ('magento_instance_id', '=', magento_instance.id)
                ], limit=1)
                if not magento_carrier:
                    skip_order = True
                    message = _("Order {} was skipped because when importing order the delivery "
                                "method {} could not find in the Magento.".format(order_reference, shipping_method))
        if skip_order:
            job = self.create_common_log_error(
                magento_instance.id,
                message,
                order_reference,
                order_data_queue_line_id
            )
            return skip_order, job
        if magento_carrier:
            delivery_carrier = delivery_carrier_obj.search([
                ('magento_carrier', '=', magento_carrier.id)], limit=1)
            if not delivery_carrier:
                product = self.env.ref('odoo_magento2_ept.product_product_shipping')
                carrier_label = magento_carrier.carrier_label if magento_carrier.carrier_label else magento_carrier.carrier_code
                delivery_carrier_obj.create({
                    'name': carrier_label,
                    'product_id': product.id,
                    'magento_carrier': magento_carrier.id
                })
        return skip_order, job

    def cancel_order_in_magento(self,webhook=False):
        """
        This method use for cancel order in magento.
        @author: Haresh Mori on date 10-Dec_2018
        @return: result
        """
        result = super(SaleOrder, self).action_cancel()
        magento_order_id = self.magento_order_id
        if magento_order_id and webhook == False:
            magento_instance = self.magento_instance_id
            try:
                api_url = '/V1/orders/%s/cancel' % magento_order_id
                result = req(magento_instance, api_url, 'POST')
            except Exception as error:
                raise Warning("Error while requesting cancel order")
        return result

    def _prepare_invoice(self):
        """
        This method is used for set necessary value(is_magento_invoice,
        is_exported_to_magento,magento_instance_id) in invoice.
        :return:
        """
        invoice_vals = super(SaleOrder, self)._prepare_invoice()
        if self.magento_payment_method_id:
            invoice_vals['magento_payment_method_id'] = self.magento_payment_method_id.id
        if self.magento_instance_id:
            invoice_vals.update({
                'magento_instance_id': self.magento_instance_id.id,
                'is_magento_invoice': True,
                'is_exported_to_magento': False
            })
        return invoice_vals

    def create_common_log_error(
            self,
            instance_id,
            message,
            order_ref,
            order_data_queue_line_id,
            model_name='sale.order',
            res_id=False
    ):
        """
        Create common log and log line for particular order
        :param instance_id: instance of Magento
        :param message: Message to be written into log line
        :param order_ref: order reference
        :param order_data_queue_line_id: order data queue line id
        :param model_name: name of model
        :param res_id: record id
        :return: common log book object
        """
        common_log_line_obj = self.env['common.log.lines.ept']
        return common_log_line_obj.create({
            'message': message,
            'order_ref': order_ref,
            'magento_order_data_queue_line_id': order_data_queue_line_id
        })

    def mgento_order_convert_date(self, order_response):
        """ This method is used to convert the order date in UTC and formate("%Y-%m-%d %H:%M:%S").
            :param order_response: Order response
        """
        if order_response.get("created_at", False):
            order_date = order_response.get("created_at", False)
            date_order = parser.parse(order_date).astimezone(utc).strftime("%Y-%m-%d %H:%M:%S")
        else:
            date_order = time.strftime("%Y-%m-%d %H:%M:%S")
            date_order = str(date_order)
        return date_order

    def create_magento_sales_order_ept(self, magento_instance_id, orders, magento_product_sku, magento_invoice_customer,
                                       magento_delivery_customer, order_count, order_total_queue):
        """
        This method create orders into Odoo.
        :param magento_instance_id: instance of Magento
        :param orders: orders dictionary received from Magento API
        :param magento_product_sku: Dictionary of Magento products
        :param magento_invoice_customer: Dictionary of Magento invoice customer
        :param magento_delivery_customer: Dictionary of Magento delivery customer
        :param order_count: Magento order count
        :return: Inserted orders dictionary
        """
        auto_work_flow_obj = self.env['sale.workflow.process.ept']
        job = False
        country_dict = {}
        state_dict = {}
        partner_obj = self.env['res.partner']

        for order_queue_line in orders:
            order_response = json.loads(order_queue_line.order_data)
            order_ref = order_response['increment_id']
            if not order_ref:
                continue
            existing_order = self.search([('magento_instance_id', '=', magento_instance_id.id),
                                          ('magento_order_reference', '=', order_ref)])
            if existing_order:
                order_queue_line.write({
                    'state': 'done',
                    'processed_at': datetime.now(),
                    'sale_order_id': existing_order.id
                })
                order_total_queue -= 1
                if 0 < order_count <= 10 and order_total_queue == 0:
                    self._cr.commit()
                    order_count = 1
                continue
            if magento_instance_id:
                date_order = self.mgento_order_convert_date(order_response)
                if str(magento_instance_id.import_order_after_date) > date_order:
                    message = "Order %s is not imported in Odoo due to configuration mismatch." \
                              "\n Received order date is " \
                              "%s. \n Please check the order after date in Magento configuration." % (order_ref,
                                                                                                      date_order)
                    job = self.create_common_log_error(
                        magento_instance_id.id, message, order_ref, order_queue_line.id)
                    order_queue_line.write({'state': 'failed', 'processed_at': datetime.now()})
                    continue
                if 'is_invoice' not in order_response.get('extension_attributes'):
                    message = "Please check Apichange extention is installed in Magento store."
                    job = self.create_common_log_error(
                        magento_instance_id.id, message, order_ref, order_queue_line.id)
                    order_queue_line.write({'state': 'failed', 'processed_at': datetime.now()})
                    continue
                skip_order, job = self.check_validation_of_order(order_queue_line.id, order_response,
                                                                 magento_instance_id, job,magento_product_sku)
                if skip_order:
                    order_queue_line.write({'state': 'failed', 'processed_at': datetime.now()})
                    continue
                skip_order, partner_dict = partner_obj.create_or_update_magento_customer_ept(
                    magento_instance_id, order_response, magento_invoice_customer,
                    magento_delivery_customer, state_dict, country_dict,
                    skip_order, job, order_queue_line.id
                )
                if skip_order:
                    order_queue_line.write({'state': 'failed', 'processed_at': datetime.now()})
                    continue
                # Create Sale Order
                order_vals = self.create_magento_sales_order_vals(partner_dict, order_response, magento_instance_id,
                                                                  order_queue_line.id)
                magento_order = self.create(order_vals)
                if magento_order:
                    skip_order = self.create_magento_sale_order_line(order_response, magento_instance_id, magento_order,
                                                                     job, order_queue_line)
                    if skip_order:
                        order_queue_line.sudo().write({'state': 'failed', 'processed_at': datetime.now()})
                        magento_order.unlink()
                        continue
                    if order_response.get('status') == 'complete' or \
                            (order_response.get('status') == 'processing' and
                             order_response.get('extension_attributes').get('is_shipment')):
                        customer_loc = self.env['stock.location'].search([('usage', '=', 'customer')], limit=1)
                        magento_order.auto_workflow_process_id.shipped_order_workflow(magento_order, customer_loc)
                    else:
                        auto_work_flow_obj.auto_workflow_process(
                            magento_order.auto_workflow_process_id.id, [magento_order.id])
                    if order_response.get('status') == 'complete' or \
                            (order_response.get('status') == 'processing' and
                             order_response.get('extension_attributes').get('is_invoice')):
                        if magento_order.invoice_ids:
                            # Here the magento order is complete state or
                            # processing state with invoice so invoice is already created
                            # So Make the Export invoice as true to hide Export invoice button from invoice.
                            magento_order.invoice_ids.write({'is_exported_to_magento': True})
                order_count += 1
                order_total_queue -= 1
                if order_count > 10 or (0 < order_count <= 10 and order_total_queue == 0):
                    self._cr.commit()
                    order_count = 1
                order_queue_line.write({
                    'state': 'done', 'processed_at': datetime.now(),
                    'magento_order_id': magento_order.magento_order_reference,
                    'sale_order_id': magento_order.id  # save sale_order_id for new order.
                })
        return magento_product_sku, magento_invoice_customer, magento_delivery_customer, order_count, order_total_queue

    def check_validation_of_order(
            self, order_data_queue_line_id, order_response, magento_instance_id, job, magento_product_sku):
        """
        Check Payment method, payment term, shipping method and create/ update product
        :param order_data_queue_line_id: order data queue line id
        :param order_response: order dictionary received from Magento API
        :param magento_instance_id: Instance of Magento
        :param job: common log book object or False
        :param magento_product_sku: Magento product dictionary
        :return: skip order and job
        """
        magento_product = self.env['magento.product.product']
        order_ref = order_response['increment_id']
        payment_method = order_response['payment'].get('method')
        skip_order, message = self.check_magento_payment_method_configuration(
            magento_instance_id, order_response, payment_method)
        if skip_order:
            job = self.create_common_log_error(
                magento_instance_id.id, message, order_ref, order_data_queue_line_id)
            return skip_order, job
        skip_order, job = self.get_magento_shipping_method(
            magento_instance_id, order_response, job, order_data_queue_line_id)
        if skip_order:
            return skip_order, job
        order_lines = order_response['items']
        skip_order, job = magento_product.create_or_update_product_in_magento(
            order_lines, magento_instance_id, magento_product_sku, order_ref, order_data_queue_line_id)
        return skip_order, job

    @staticmethod
    def get_financial_status(order_status, is_invoice, is_shipment):
        """
        Get Financial Status Dictionary.
        :param order_status: Order status received from Magento.
        :param is_invoice: Order is invoiced.
        :param is_shipment: Order is Shipped.
        :return: Financial Status dictionary
        """
        financial_status_code = financial_status_name = ''
        if order_status == "pending":
            financial_status_code = 'not_paid'
            financial_status_name = 'Pending Orders'
        elif order_status == "processing" and is_invoice and not is_shipment:
            financial_status_code = 'processing_paid'
            financial_status_name = 'Processing orders with Invoice'
        elif order_status == "processing" and is_shipment and not is_invoice:
            financial_status_code = 'processing_unpaid'
            financial_status_name = 'Processing orders with Shipping'
        elif order_status == "complete":
            financial_status_code = 'paid'
            financial_status_name = 'Completed Orders'
        return financial_status_code, financial_status_name

    def search_order_financial_status(self, order_response, magento_instance, payment_option):
        """
        Search order Financial status.
        :param order_response: Response received from Magento.
        :param magento_instance: Magento Instance.
        :param payment_option: Magento Order Payment Method
        :return: Financial Status object, Financial Status Name
        """
        is_invoice = order_response.get('extension_attributes').get('is_invoice')
        is_shipment = order_response.get('extension_attributes').get('is_shipment')
        financial_status_code, financial_status_name = self.get_financial_status(
            order_response.get('status'), is_invoice, is_shipment)
        workflow_config = self.env['magento.financial.status.ept'].search(
            [('magento_instance_id', '=', magento_instance.id),
             ('payment_method_id', '=', payment_option.id),
             ('financial_status', '=', financial_status_code)])
        return workflow_config, financial_status_name

    def check_magento_payment_method_configuration(
            self, magento_instance, order_response, payment_method):
        """
        Check Configuration All Configuration of Payment Methods
        :param magento_instance: Magento Instance Object
        :param order_response: Order Response received from Magento.
        :param payment_method: Order Payment Method.
        :return: skip_order (boolean)
        """
        skip_order = False
        payment_option = magento_instance.payment_method_ids.filtered(
            lambda x: x.payment_method_code == payment_method)
        order_ref = order_response['increment_id']
        message = ''
        import_rule = payment_option.import_rule
        max_days = payment_option.days_before_cancel
        amount_paid = order_response.get('payment').get('amount_paid') or False

        workflow_config, financial_status_name = self.search_order_financial_status(
            order_response, magento_instance, payment_option)
        if not workflow_config and financial_status_name == "":
            is_invoice = order_response.get('extension_attributes').get('is_invoice')
            is_shipment = order_response.get('extension_attributes').get('is_shipment')
            skip_order = True
            if not is_invoice and not is_shipment and order_response.get('status') == 'processing':
                message = "Order %s skipped, Order status is processing, but the order is neither " \
                          "invoice nor shipped." % order_response.get('increment_id')
            else:
                message = "Order %s skipped due to Partial Invoice and Shipment are not Supported." % order_response.get(
                    'increment_id')
        elif not workflow_config and financial_status_name != "":
            skip_order = True
            message = "- Automatic order process workflow configuration not found for this order " \
                      "%s. \n - System tries to find the workflow based on combination of Payment " \
                      "Gateway(such as Bank Transfer etc.) and Financial Status(such as Pending Orders," \
                      "Completed Orders etc.).\n - In this order, Payment Gateway is %s and Financial Status is %s." \
                      " \n - You can configure the Automatic order process workflow " \
                      "under the menu Magento > Configuration > Financial Status." % \
                      (order_response.get('increment_id'), payment_method, financial_status_name)
        elif not workflow_config.auto_workflow_id and financial_status_name != "":
            skip_order = True
            message = "Order %s skipped due to auto workflow configuration not found" \
                      " for payment method - %s and financial status - %s" % \
                      (order_ref, payment_method, financial_status_name)
        elif not workflow_config.payment_term_id and financial_status_name != "":
            skip_order = True
            message = "Order %s skipped due to Payment Term not found in payment method - %s and financial status - %s" % (
                order_ref, payment_method, financial_status_name)
        elif max_days:
            order_date = datetime.strptime(order_response.get('created_at'), '%Y-%m-%d %H:%M:%S')
            if order_date + timedelta(days=max_days) < datetime.now():
                skip_order = True
                message = '%s has not been imported because it is %d before.' % (
                    order_ref, max_days)
        elif import_rule == 'never':
            skip_order = True
            message = "Orders with payment method %s are never imported." % payment_method
        elif not amount_paid and import_rule == 'paid':
            skip_order = True
            message = "Order '%s' has not been paid yet,So order will be imported later" % order_ref
        return skip_order, message

    def create_magento_sales_order_vals(
            self,
            partner_dict,
            order_response,
            magento_instance_id,
            order_dict_id
    ):
        """
        Prepare dictionary for Magento sale order
        :param partner_dict: partner invoice address and delivery address dictionary
        :param order_response: order dictionary received from Magento API
        :param magento_instance_id: instance of Magento
        :param order_dict_id: Order queue data line object
        :return: Dictionary of sale order values
        """
        sale_order_obj = self.env['sale.order']
        shipping = order_response.get('extension_attributes').get('shipping_assignments')
        shipping_method = shipping[0].get('shipping').get('method') or False
        shipping_carrier = magento_instance_id.shipping_method_ids.filtered(
            lambda x: x.carrier_code == shipping_method
        )
        delivery_method = shipping_carrier.delivery_carrier_ids.filtered(
            lambda x: x.magento_carrier_code == shipping_method
        )
        payment_method = order_response['payment'].get('method')
        payment_option = magento_instance_id.payment_method_ids.filtered(
            lambda x: x.payment_method_code == payment_method)
        financial_status, financial_status_name = self.search_order_financial_status(
            order_response, magento_instance_id, payment_option)
        workflow_process_id = False
        payment_term_id = False
        if financial_status and financial_status.auto_workflow_id:
            workflow_process_id = financial_status.auto_workflow_id
            payment_term_id = financial_status.payment_term_id
        magento_payment_method_id = False
        if payment_option and payment_option.id:
            magento_payment_method_id = payment_option.id
        price_list = self.check_price_list_for_order_exit(
            magento_instance_id,
            order_response,
            order_dict_id
        )
        ## Add change for get store_id from response and based on that get the warehouse and website.
        store_id = order_response.get('store_id')
        store_view = self.env['magento.storeview'].search([('magento_instance_id','=',magento_instance_id.id),
                                                           ('magento_storeview__id','=',str(store_id))])
        order_ref = order_response.get('increment_id')
        ordervals = {
            'company_id': magento_instance_id.company_id.id,
            'partner_id': partner_dict.get('invoice_partner'),
            'partner_invoice_id': partner_dict.get('invoice_partner'),
            'partner_shipping_id': partner_dict.get('shipping_partner'),
            'warehouse_id': store_view.magento_website_id.warehouse_id.id,
            'picking_policy': workflow_process_id and workflow_process_id.picking_policy or False,
            'date_order': order_response.get('created_at', False),
            'pricelist_id': price_list.id if price_list else False,
            'team_id': store_view.team_id.id if store_view.team_id else False,
            #'payment_term_id': payment_option.payment_term_id.id  if payment_option.payment_term_id else False,
            'payment_term_id': payment_term_id and payment_term_id.id or False,
            'carrier_id': delivery_method.id if delivery_method else False,
            'client_order_ref': order_ref
        }
        ordervals = sale_order_obj.create_sales_order_vals_ept(ordervals)
        ordervals.update({
            'name': "%s%s" % (store_view and store_view.sale_prefix or '', order_ref),
            'magento_instance_id': magento_instance_id and magento_instance_id.id or False,
            'magento_website_id': store_view and store_view.magento_website_id.id or False,
            'store_id': store_view and store_view.id or False,
            'auto_workflow_process_id': workflow_process_id.id,
            'magento_payment_method_id': magento_payment_method_id,
            'magento_shipping_method_id': shipping_carrier.id,
            'is_exported_to_magento_shipment_status': False,
            'magento_order_id': order_response.get('items')[0].get('order_id'),
            'magento_order_reference': order_ref
        })
        return ordervals

    def create_magento_sale_order_line(self, order_response, instance, magento_order, job, order_queue_line):
        """
        Create shipping order line and order discount line and sale order line.
        :param order_response: order dictionary received from Magento API
        :param instance: instance of Magento
        :param magento_order: sale order object
        """
        sale_order_line_obj = self.env['sale.order.line']
        skip_order, sale_order_lines = sale_order_line_obj.magento_create_sale_order_line(instance, order_response,
                                                                                          magento_order, job,
                                                                                          order_queue_line)
        if not skip_order:
            skip_order = self.create_shipping_order_line(
                order_response, magento_order, job, order_queue_line)
            if not skip_order:
                skip_order = self.create_gift_card_cod_order_line(order_response, magento_order)
            if not skip_order:
                skip_order = self.create_discount_order_line(
                    order_response, magento_order, job, order_queue_line)
        return skip_order

    def create_shipping_order_line(self, order_response, magento_order, log_book_id, order_dict):
        """
        Create Shipping order line.
        :param order_response: Response received from Magento.
        :param magento_order: Sale order object
        :return:
        """
        sale_order_line_obj = self.env['sale.order.line']
        shipping_amount_incl = float(order_response.get('shipping_incl_tax') or 0.0)
        shipping_amount_excl = float(order_response.get('shipping_amount') or 0.0)
        if shipping_amount_incl or shipping_amount_excl:
            account_tax_obj = self.env['account.tax']
            shipping_product = self.env.ref('odoo_magento2_ept.product_product_shipping')
            ship_tax_id = []
            # price = shipping_amount_excl
            extension_attributes = order_response.get('extension_attributes')
            is_tax_included = self.get_is_tax_included(extension_attributes, "apply_shipping_on_prices")
            price = shipping_amount_incl if is_tax_included else shipping_amount_excl
            shipping_line = sale_order_line_obj.create_sale_order_line_vals(
                order_response, price, shipping_product, magento_order)
            shipping_line.update({'is_delivery': True})
            shipping_taxes = self.check_shipping_has_tax_included_and_percent(extension_attributes)
            if shipping_taxes:
                for shipping_tax in shipping_taxes:
                    tax_name = shipping_tax['tax_title']
                    tax_percent = shipping_tax['tax_percent']
                    tax_id = account_tax_obj.get_tax_from_rate(
                        rate=float(tax_percent), name=tax_name, is_tax_included=is_tax_included)
                    if tax_id and not tax_id.active:
                        skip_order = True
                        message = _("Order {} was skipped because the shipping tax {}% was not found. "
                                    "The connector is unable to create new tax {}%, kindly check the tax {}% has been "
                                    "archived?".format(order_response['increment_id'], tax_id.name, tax_id.name,
                                                       tax_id.name))
                        log_book_id.add_log_line(message, order_response['increment_id'],
                                                 order_dict.id, "magento_order_data_queue_line_id")
                        return skip_order
                    if not tax_id:
                        tax_id = account_tax_obj.sudo().create({
                            'name': tax_name,
                            'description': tax_name,
                            'amount_type': 'percent',
                            'price_include': is_tax_included,
                            'amount': float(tax_percent),
                            'type_tax_use': 'sale',
                        })
                    ship_tax_id.append(tax_id.id)

            if ship_tax_id:
                shipping_line.update({
                    'tax_id': [(6, 0, ship_tax_id)]
                })
            sale_order_line_obj.create(shipping_line)

    @staticmethod
    def check_shipping_has_tax_included_and_percent(extension_attributes):
        """
        Check order tax applied is including/ excluding and tax percent.
        :param extension_attributes: extension attributes received from order.
        :return: True/False
        """
        tax_details = []
        if "item_applied_taxes" in extension_attributes:
            for order_res in extension_attributes.get("item_applied_taxes"):
                if order_res.get('type') == "shipping" and order_res.get('applied_taxes'):
                    # shipping_tax_dict = order_res.get('applied_taxes')[0]
                    # if shipping_tax_dict:
                    #     tax_percent = shipping_tax_dict.get('percent')
                    for tax in order_res.get('applied_taxes', list()):
                        tax_details.append({'tax_title':tax.get('title'), 'tax_percent': tax.get('percent', 0)})
        return tax_details

    def create_gift_card_cod_order_line(self, order_response, magento_order):
        sale_order_line_obj = self.env['sale.order.line']
        gift_card_amount = float(order_response.get('gift_cert_amount') or 0.0) or False
        if gift_card_amount:
            gift_product = self.env.ref('odoo_magento2_ept.magento_Magneot_product_product_gift')
            gift_card_line = sale_order_line_obj.create_sale_order_line_vals(
                order_response, gift_card_amount, gift_product, magento_order)
            sale_order_line_obj.create(gift_card_line)
        cash_on_delivery_amount_excl = float(order_response.get('cod_fee') or 0.0)
        cash_on_delivery_amount_incl = float(order_response.get('cod_tax_amount') or 0.0)
        if cash_on_delivery_amount_excl or cash_on_delivery_amount_incl:
            cash_on_delivery_product = self.env.ref('odoo_magento2_ept.Magento_product_product_cash_on_delivery')
            price = cash_on_delivery_amount_excl
            cod_line = sale_order_line_obj.create_sale_order_line_vals(
                order_response, price, cash_on_delivery_product, magento_order)
            sale_order_line_obj.create(cod_line)
        return False

    def create_discount_order_line(self, order_response, magento_order, log_book_id, order_dict):
        """
        Create discount order line.
        :param order_response: Response received from Magento.
        :param magento_order: Sale order object
        :return:
        """
        sale_order_line_obj = self.env['sale.order.line']
        account_tax_obj = self.env['account.tax']
        discount_amount = float(order_response.get('discount_amount') or 0.0) or False
        if discount_amount:
            tax_id = False
            discount_product = self.env.ref('odoo_magento2_ept.magento_product_product_discount')
            discount_line = sale_order_line_obj.create_sale_order_line_vals(
                order_response,
                discount_amount,
                discount_product,
                magento_order
            )
            is_tax_included = self.get_is_tax_included(
                order_response.get('extension_attributes'), "apply_discount_on_prices")
            tax_percent = False
            tax_name = False
            for order_items in order_response.get('items'):
                tax_percent = order_items.get('tax_percent') if 'tax_percent' in order_items.keys() else False
                break
            if tax_percent:
                name = '%s %% ' % (tax_percent)
                tax_id = account_tax_obj.get_tax_from_rate(rate=float(tax_percent), name=name, is_tax_included='True')
                if tax_id and not tax_id.active:
                    skip_order = True
                    message = _("Order {} was skipped because the discount tax {}% was not found. "
                                "The connector is unable to create new tax {}%, kindly check the tax {}% has been "
                                "archived?".format(order_response['increment_id'], tax_id.name, tax_id.name,
                                                   tax_id.name))
                    log_book_id.add_log_line(message, order_response['increment_id'],
                                             order_dict.id, "magento_order_data_queue_line_id")
                    return skip_order
                if not tax_id:
                    tax_id = account_tax_obj.sudo().create({
                        'name': name,
                        'description': name,
                        'amount_type': 'percent',
                        'price_include': is_tax_included,
                        'amount': float(tax_percent),
                        'type_tax_use': 'sale',
                    })
            if tax_id:
                discount_line.update({
                    'tax_id': [(6, 0, tax_id.ids)]
                })
            sale_order_line_obj.create(discount_line)

    @staticmethod
    def get_is_tax_included(extension_attributes, tax_prices):
        """
        Get shipping/ discount tax is included or excluded.
        :param extension_attributes: extension attributes dictionary returns from order response
        :param tax_prices: type of tax
        :return: True/ False
        """
        is_tax_included = True
        if extension_attributes and tax_prices in extension_attributes:
            apply_tax_on_prices = extension_attributes.get(
                tax_prices) if extension_attributes.get(tax_prices) else False
            if apply_tax_on_prices and apply_tax_on_prices == 'excluding_tax':
                is_tax_included = False
        return is_tax_included

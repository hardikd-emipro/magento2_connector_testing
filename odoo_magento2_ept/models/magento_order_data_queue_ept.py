#!/usr/bin/python3
"""
Describes methods for Magento import order data queue.
"""
from datetime import datetime
from odoo import models, fields, _
from odoo.exceptions import Warning, UserError
from odoo.addons.odoo_magento2_ept.models.api_request import req, create_search_criteria, create_filter
from odoo.addons.odoo_magento2_ept.python_library.php import Php

MAGENTO_DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'


class MagentoOrderDataQueueEpt(models.Model):
    """
    Describes Magento Order Data Queue
    """
    _name = "magento.order.data.queue.ept"
    _description = "Magento Order Data Queue EPT"
    name = fields.Char(help="Sequential name of imported order.", copy=False)
    magento_instance_id = fields.Many2one(
        'magento.instance',
        string='Magento Instance',
        help="Order imported from this Magento Instance."
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('partially_completed', 'Partially Completed'),
        ('completed', 'Completed')
    ], default='draft', copy=False, help="Status of Order Data Queue")
    order_common_log_book_id = fields.Many2one(
        "common.log.book.ept",
        help="Related Log book which has all logs for current queue."
    )
    magento_order_common_log_lines_ids = fields.One2many(
        related="order_common_log_book_id.log_lines",
        help="Log lines of Common log book for particular order queue"
    )
    order_data_queue_line_ids = fields.One2many(
        "magento.order.data.queue.line.ept",
        "magento_order_data_queue_id",
        help="Order data queue line ids"
    )
    order_queue_line_total_record = fields.Integer(
        string='Total Records',
        compute='_compute_order_queue_line_record',
        help="Returns total number of order data queue lines"
    )
    order_queue_line_draft_record = fields.Integer(
        string='Draft Records',
        compute='_compute_order_queue_line_record',
        help="Returns total number of draft order data queue lines"
    )
    order_queue_line_fail_record = fields.Integer(
        string='Fail Records',
        compute='_compute_order_queue_line_record',
        help="Returns total number of Failed order data queue lines"
    )
    order_queue_line_done_record = fields.Integer(
        string='Done Records',
        compute='_compute_order_queue_line_record',
        help="Returns total number of done order data queue lines"
    )

    def magento_create_order_data_queues(
            self,
            magento_instance,
            start_date,
            end_date
    ):
        """
        Import magento orders and stores them as a bunch of 50 orders queue.
        :param magento_instance: Instance of Magento
        :param start_date: Import Order Start Date
        :param end_date: Import Order End Date
        """
        order_data_queue_line = self.env["magento.order.data.queue.line.ept"]
        order_queue_data = {
            'order_queue': False,
            'count': 0
        }
        response = self.get_orders_api_response_from_magento(magento_instance, end_date, start_date)
        if response.get('messages', False) and response.get('messages', False).get('error'):
            raise UserError(_('We are getting internal server errors while receiving the response from Magento.'
                              ' This can be due to the following reasons.\n'
                              '1. Permission issues\n'
                              '2. Memory Limitation\n'
                              '3. Third Party Plugin issue.\n %s',
                              (response.get('messages').get('error')[0].get('message'),)))
        if response.get('total_count') == 0:
            magento_instance.magento_import_order_page_count = 1
        if response.get('items'):
            order_queue_data = order_data_queue_line.create_import_order_queue_line(
                response.get('items'), magento_instance, order_queue_data
            )
            total_imported_orders = magento_instance.magento_import_order_page_count * 50
            magento_instance.magento_import_order_page_count += 1
            while total_imported_orders <= response.get('total_count'):
                response = self.get_orders_api_response_from_magento(magento_instance, end_date, start_date)
                if response.get('items'):
                    order_queue_data = order_data_queue_line.create_import_order_queue_line(
                        response.get('items'), magento_instance, order_queue_data
                    )
                    total_imported_orders = magento_instance.magento_import_order_page_count * 50
                    magento_instance.magento_import_order_page_count += 1
                    self._cr.commit()
            # magento_instance.last_order_import_date = datetime.now()
            magento_instance.magento_import_order_page_count = 1
        return order_queue_data

    def get_orders_api_response_from_magento(self, instance, end_date, start_date):
        filters = {}
        filters.update({'from_date': start_date, 'to_date': end_date})
        search_criteria = self.create_search_criteria_for_import_order(
            filters, instance.import_magento_order_status_ids.mapped('status'))
        search_criteria['searchCriteria']['pageSize'] = 50
        search_criteria['searchCriteria']['currentPage'] = instance.magento_import_order_page_count
        query_string = Php.http_build_query(search_criteria)
        try:
            api_url = '/V1/orders?%s' % query_string
            response = req(instance, api_url)
        except Exception as error:
            raise Warning(_("Error while requesting products {}".format(error)))
        return response

    def import_specific_order(
            self,
            instance,
            order_reference_lists
    ):
        """
        Creates order queues when import sale orders from Magento.
        :param instance: current instance of Magento
        :param order_reference_lists:  Dictionary of Order References
        :return:
        """
        order_data_queue_line = self.env["magento.order.data.queue.line.ept"]
        order_queue_data = {
            'order_queue': False,
            'count': 0
        }
        for order_reference in order_reference_lists:
            filters = {
                'increment_id': order_reference
            }
            filters.setdefault('state', {})
            filters['state']['in'] = instance.import_magento_order_status_ids.mapped('status')
            search_criteria = create_search_criteria(filters)
            query_string = Php.http_build_query(search_criteria)
            try:
                api_url = '/V1/orders?%s' % query_string
                response = req(instance, api_url)
            except Exception as error:
                raise Warning(_("Error while requesting Orders"))
            if response.get('items'):
                order_queue_data = order_data_queue_line.create_import_order_queue_line(
                    response.get('items'),
                    instance,
                    order_queue_data
                )

        #instance.last_order_import_date = datetime.now()
        return True

    def create_search_criteria_for_import_order(self, filter, magento_order_status):
        """
        Create Search Criteria to import orders from Magento.
        :param filter: Dictionary for filters
        :param magento_order_status: order status to be imported
        :return: Dictionary of filters
        """
        filters = {}
        if filter.get('from_date') is not None:
            from_date = filter.get('from_date')
            filters.setdefault('updated_at', {})
            filters['updated_at']['from'] = {} if not filter.get('from_date') else from_date.strftime(
                MAGENTO_DATETIME_FORMAT)
        if filter.get('to_date'):
            to_date = filter.get('to_date')
            filters.setdefault('updated_at', {})
            filters['updated_at']['to'] = to_date.strftime(MAGENTO_DATETIME_FORMAT)
        filters.setdefault('state', {})
        filters['state']['in'] = magento_order_status
        filters = create_search_criteria(filters)
        return filters

    def _compute_order_queue_line_record(self):
        """
        This will calculate total, draft, failed and done orders from ebay.
        """
        for order_queue in self:
            order_queue.order_queue_line_total_record = len(order_queue.order_data_queue_line_ids)
            order_queue.order_queue_line_draft_record = len(
                order_queue.order_data_queue_line_ids.filtered(lambda x: x.state == 'draft')
            )
            order_queue.order_queue_line_fail_record = len(
                order_queue.order_data_queue_line_ids.filtered(lambda x: x.state == 'failed')
            )
            order_queue.order_queue_line_done_record = len(
                order_queue.order_data_queue_line_ids.filtered(lambda x: x.state == 'done')
            )

    def action_order_queue_record_count(self):
        """
        This method used to display the order queue records. you can see the record here: Ebay
        => Sales => Order Queue Data
        :return:
        """
        return True

    def create(self, vals):
        """
        Creates a sequence for Ordered Data Queue
        :param vals: values to create Ordered Data Queue
        :return: MagentoOrderDataQueueEpt Object
        """
        sequence_id = self.env.ref('odoo_magento2_ept.seq_order_queue_data').ids
        if sequence_id:
            record_name = self.env['ir.sequence'].browse(sequence_id).next_by_id()
        else:
            record_name = '/'
        vals.update({'name': record_name or ''})
        return super(MagentoOrderDataQueueEpt, self).create(vals)

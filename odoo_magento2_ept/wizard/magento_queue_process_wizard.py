#!/usr/bin/python3
"""
Describes Wizard for processing order queue
"""
from odoo.exceptions import Warning
from odoo import models, api, _


class MagentoQueueProcessEpt(models.TransientModel):
    """
    Describes Wizard for processing order queue
    """
    _name = 'magento.queue.process.ept'
    _description = 'Magento Queue Process Ept'

    def magento_manual_queue_process(self):
        """
        Process order manually
        """
        queue_process = self._context.get('queue_process')
        if queue_process == "process_order_queue_manually":
            self.process_magento_order_queue_manually()
        if queue_process == "process_product_queue_manually":
            self.process_magento_product_queue_manually()
        if queue_process == "process_customer_queue_manually":
            self.process_magento_customer_queue_manually()

    @api.model
    def process_magento_order_queue_manually(self):
        """
        Process queued orders manually
        """
        magento_order_queue_line_obj = self.env["magento.order.data.queue.line.ept"]
        order_queue_ids = self._context.get('active_ids')
        order_queue_cron = self.env.ref(
            "odoo_magento2_ept.magento_ir_cron_child_to_process_order_queue"
        )
        self.check_running_cron_scheduler(order_queue_cron)
        for order_queue_id in order_queue_ids:
            order_queue_line_batch = magento_order_queue_line_obj.search([
                ("magento_order_data_queue_id", "=", order_queue_id),
                ("state", "in", ('draft', 'failed'))
            ])
            order_queue_line_batch.process_import_magento_order_queue_data()
        return True

    @api.model
    def process_magento_customer_queue_manually(self):
        """
        Process queued customers manually
        """
        magento_customer_queue_line_obj = self.env["magento.customer.data.queue.line.ept"]
        customer_queue_ids = self._context.get('active_ids')
        customer_queue_cron = self.env.ref(
            "odoo_magento2_ept.magento_ir_cron_child_to_process_customer_queue"
        )
        self.check_running_cron_scheduler(customer_queue_cron)
        for customer_queue_id in customer_queue_ids:
            customer_queue_line_batch = magento_customer_queue_line_obj.search([
                ("magento_customer_data_queue_id", "=", customer_queue_id),
                ("state", "in", ('draft', 'failed'))
            ])
            customer_queue_line_batch.process_import_customer_queue_data()
        return True

    @api.model
    def process_magento_product_queue_manually(self):
        """
        Process queued products manually
        """
        import_product_queue_line_obj = self.env["sync.import.magento.product.queue.line"]
        product_queue_ids = self._context.get('active_ids')
        product_queue_cron = self.env.ref(
            "odoo_magento2_ept.ir_cron_child_to_process_magento_product_queue"
        )
        self.check_running_cron_scheduler(product_queue_cron)
        product_queue_lines = import_product_queue_line_obj.search([
            ("sync_import_magento_product_queue_id", "in", product_queue_ids),
            ("state", "in", ('draft', 'failed'))])
        import_product_queue_line_obj.process_import_magento_product_queue_data_ept(product_queue_lines.ids)
        return True

    @api.model
    def check_running_cron_scheduler(self, order_queue_cron):
        """
        Check if Queue cron is active, then user can not process manually
        :param order_queue_cron: External Id of Order queue
        :return: Gives error if Child Cron is active
        """
        if order_queue_cron and order_queue_cron.active:
            child_cron = order_queue_cron.try_cron_lock()
            if child_cron and child_cron.get('result'):
                message = "This process executed using scheduler, " \
                          "Next Scheduler execute for this process will " \
                          "run in %s Minutes" % child_cron.get('result')
                raise Warning(_(message))
            elif child_cron and child_cron.get('reason'):
                raise Warning(_(child_cron.get('reason')))

    def magento_action_archive(self):
        """
        This method is used to call a child of the instance to active/inactive instance and its data.
        """
        instance_obj = self.env['magento.instance']
        instances = instance_obj.browse(self._context.get('active_ids'))
        for instance in instances:
            instance.magento_action_archive_unarchive()

#!/usr/bin/python3
"""
Describes methods to store sync/ Import product queue line
"""
import json
from datetime import timedelta, datetime
from odoo import models, fields


class SyncImportMagentoProductQueueLine(models.Model):
    """
    Describes sync/ Import product Queue Line
    """
    _name = "sync.import.magento.product.queue.line"
    _description = "Sync/ Import Product Queue Line"
    _rec_name = "product_sku"
    sync_import_magento_product_queue_id = fields.Many2one("sync.import.magento.product.queue", ondelete="cascade", required=True)
    magento_instance_id = fields.Many2one('magento.instance', string='Instance',
                                          help="Products imported from or Synced to this Magento Instance.")
    state = fields.Selection([("draft", "Draft"), ("failed", "Failed"),
                              ("done", "Done")], default="draft", copy=False)
    product_sku = fields.Char(string="Product Sku", help="SKU of imported product.", copy=False)
    product_data = fields.Text(string="Product Data", help="Product Data imported from magento.", copy=False)
    processed_at = fields.Datetime(string="Processing Time",
                                   help="Shows Date and Time, When the data is processed", copy=False)
    import_product_common_log_lines_ids = fields.One2many("common.log.lines.ept", "import_product_queue_line_id",
                                                          help="Log lines created against which line.")
    do_not_update_existing_product = fields.Boolean(
        string="Do not update existing Products?",
        help="If checked and Product(s) found in odoo/magento layer, then not update the Product(s)"
    )

    def create_import_magento_product_queue_line(self, items, instance, is_update):
        """
        Creates a product data queue line.
        :param items: product data received from magento
        :param instance: instance of magento
        """
        product_queue = self.magento_create_product_queue(instance)
        for item in items:
            data = json.dumps(item)
            line_vals = self.prepare_magento_product_queue_line_vals(
                item.get('sku', False), instance, data, product_queue, is_update)
            self.create(line_vals)
        return product_queue

    @staticmethod
    def prepare_magento_product_queue_line_vals(sku, instance, data, product_queue, is_update):
        """
        Prepare queue line data for products..
        :param item:
        :param instance:
        :param data:
        :param product_queue:
        :return:
        """
        return {
            'product_sku': sku,
            'magento_instance_id': instance and instance.id or False,
            'product_data': data,
            'sync_import_magento_product_queue_id': product_queue and product_queue.id or False,
            'state': 'draft',
            'do_not_update_existing_product': is_update
        }

    def create_import_specific_product_queue_line(self, items, instance, product_queue_data, is_update=True):
        """
        Creates a product data queue line and splits product queue line after 200 orders.
        :param items: product data received from magento
        :param instance: instance of magento
        :param product_queue_data: If True, product queue is already there.
        """
        product_queue = product_queue_data.get('product_queue')
        count = product_queue_data.get('count')
        if not product_queue:
            product_queue = self.magento_create_product_queue(instance)
            product_queue_data.update({'product_queue': product_queue})
        data = json.dumps(items)
        product_queue_line_values = self.prepare_magento_product_queue_line_vals(
            items.get('sku', False), instance, data, product_queue, is_update)
        self.create(product_queue_line_values)
        count = count + 1
        if count > 200:
            count = 0
            product_queue = False
            product_queue_data.update({'product_queue': product_queue, 'count': count})
        product_queue_data.update({'count': count})
        return product_queue_data

    def magento_create_product_queue(self, instance):
        """
        This method used to create a product queue as per the split requirement of the
        queue. It is used for process the queue manually.
        :param instance: instance of Magento
        """
        product_queue_vals = {
            'magento_instance_id': instance and instance.id or False,
            'state': 'draft',
        }
        product_queue_data_id = self.env["sync.import.magento.product.queue"].create(product_queue_vals)
        return product_queue_data_id

    def auto_start_child_process_for_magento_product_queue(self):
        """
        This method used to start the child process cron for processing the product queue line data.
        """
        child_product_queue_cron = self.env.ref('odoo_magento2_ept.ir_cron_child_to_process_magento_product_queue')
        if child_product_queue_cron and not child_product_queue_cron.active:
            results = self.search([('state', '=', 'draft')], limit=100)
            if not results:
                return True
            child_product_queue_cron.write({
                'active': True, 'numbercall': 1, 'nextcall': datetime.now() + timedelta(seconds=10)
            })
        return True

    def auto_import_magento_product_queue_data(self):
        """
        This method used to process synced Magento product data in batch of 50 queue lines.
        This method is called from cron job.
        """
        results = self.search([('state', '=', 'draft')], limit=100)
        if results:
            self.process_import_magento_product_queue_data_ept(results.ids)

    def process_import_magento_product_queue_data_ept(self, queue_line_ids):
        """
        This method processes product queue lines.
        """
        magento_product_obj = self.env['magento.product.product']
        product_queue_dict = {}
        magento_pr_sku = {}
        product_count = 1
        for queue_line_id in queue_line_ids:
            product_queue_line = self.browse(queue_line_id)
            magento_pr_sku, product_count = magento_product_obj.create_magento_product_in_odoo(
                product_queue_line.magento_instance_id,
                product_queue_line,
                magento_pr_sku,
                product_count
            )
            mage_pro_common_log_lines = product_queue_line.import_product_common_log_lines_ids.ids
            sync_prod_que_id = product_queue_line.sync_import_magento_product_queue_id.id
            if sync_prod_que_id:
                if sync_prod_que_id not in product_queue_dict.keys():
                    product_queue_dict.update({sync_prod_que_id: mage_pro_common_log_lines})
                else:
                    product_queue_dict[sync_prod_que_id] += mage_pro_common_log_lines
        for queue, log_lines in product_queue_dict.items():
            queue_id = self.env['sync.import.magento.product.queue'].browse(queue)
            if log_lines:
                if queue_id.import_product_common_log_book_id:
                    existing_lines = queue_id.import_product_common_log_book_id.log_lines.ids
                    queue_id.import_product_common_log_book_id.write({
                        "log_lines": [(6, 0, existing_lines + log_lines)]
                    })
                else:
                    comman_log_id = self.env["common.log.book.ept"].create({
                        'type': 'import',
                        'module': 'magento_ept',
                        'magento_instance_id': queue_id.magento_instance_id.id,
                        'active': True,
                        "log_lines": [(6, 0, log_lines)]
                    })
                    queue_id.import_product_common_log_book_id = comman_log_id
            query = """SELECT id FROM sync_import_magento_product_queue_line WHERE
             sync_import_magento_product_queue_id = %s and state in ('draft','failed');""" % queue
            self._cr.execute(query)
            order_queue_line_ids = self._cr.fetchone()
            if order_queue_line_ids:
                queue_id.write({'state': "partially_completed"})
            else:
                queue_id.write({'state': "completed"})
            self._cr.commit()
        return True

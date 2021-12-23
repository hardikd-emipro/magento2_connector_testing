#!/usr/bin/python3
"""
Describes methods to store Order Data queue line
"""
import json
from datetime import timedelta, datetime
from odoo import models, fields


class MagentoOrderDataQueueLineEpt(models.Model):
    """
    Describes Order Data Queue Line
    """
    _name = "magento.order.data.queue.line.ept"
    _description = "Magento Order Data Queue Line EPT"
    _rec_name = "magento_order_id"
    magento_order_data_queue_id = fields.Many2one("magento.order.data.queue.ept", ondelete="cascade")
    magento_instance_id = fields.Many2one(
        'magento.instance',
        string='Magento Instance',
        help="Order imported from this Magento Instance."
    )
    state = fields.Selection([
        ("draft", "Draft"),
        ("failed", "Failed"),
        ("done", "Done")
    ], default="draft", copy=False)
    magento_order_id = fields.Char(help="Id of imported order.", copy=False)
    sale_order_id = fields.Many2one(
        "sale.order",
        copy=False,
        help="Order created in Odoo."
    )
    order_data = fields.Text(help="Data imported from Magento of current order.", copy=False)
    processed_at = fields.Datetime(
        help="Shows Date and Time, When the data is processed",
        copy=False
    )
    magento_order_common_log_lines_ids = fields.One2many(
        "common.log.lines.ept",
        "magento_order_data_queue_line_id",
        help="Log lines created against which line."
    )

    def open_sale_order(self):
        """
        call this method while click on > Order Data Queue line > Sale Order smart button
        :return: Tree view of the odoo sale order
        """
        return {
            'name': 'Sale Order',
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'domain': [('id', '=', self.sale_order_id.id)]
        }

    def create_import_order_queue_line(self, items, magento_instance, order_queue_data):
        """
        Creates an imported orders queue line
        :param items: Items received from Magento
        :param magento_instance: Instance of Magento
        :return: True
        """
        order_queue = order_queue_data.get('order_queue')
        count = order_queue_data.get('count')
        for order_id in items:
            magento_order_ref = order_id.get('increment_id', False)
            if not order_queue:
                order_queue = self.magento_create_order_queue(magento_instance)
            order_queue_line_vals = {}
            data = json.dumps(order_id)
            order_queue_line_vals.update({
                'magento_order_id': magento_order_ref,
                'magento_instance_id': magento_instance and magento_instance.id or False,
                'order_data': data,
                'magento_order_data_queue_id': order_queue and order_queue.id or False,
                'state': 'draft',
            })
            self.create(order_queue_line_vals)
            count = count + 1
            if count == 50:
                count = 0
                order_queue = False
        order_queue_data.update({
            'order_queue': order_queue,
            'count': count
        })
        return order_queue_data

    def magento_create_order_queue(self, magento_instance):
        """
        Creates Imported Magento Orders queue
        :param magento_instance: Instance of Magento
        :return: Magento Order Data queue object
        """
        order_queue_vals = {
            'magento_instance_id': magento_instance and magento_instance.id or False,
            'state': 'draft',
        }
        order_queue_data_id = self.env["magento.order.data.queue.ept"].create(order_queue_vals)
        return order_queue_data_id

    def auto_start_child_process_for_order_queue(self):
        """
        This method used to start the child process cron for process the order queue line data.
        """
        child_order_queue_cron = self.env.ref(
            'odoo_magento2_ept.magento_ir_cron_child_to_process_order_queue'
        )
        if child_order_queue_cron and not child_order_queue_cron.active:
            results = self.search([('state', '=', 'draft')], limit=100)
            if not results:
                return True
            child_order_queue_cron.write({
                'active': True,
                'numbercall': 1,
                'nextcall': datetime.now() + timedelta(seconds=10)
            })
        return True

    def auto_import_order_queue_data(self):
        """
        This method used to process synced magento order data in batch of 50 queue lines.
        This method is called from cron job.
        """
        results = self.search([('state', '=', 'draft')], limit=50)
        results.process_import_magento_order_queue_data()

    def process_import_magento_order_queue_data(self):
        """
        This method processes order queue lines.
        """
        sale_order_obj = self.env['sale.order']
        order_queue_dict = {}
        magento_prod = {}
        inv_cust = {}
        del_cust = {}
        order = 1
        #order_total_queue = self.magento_order_data_queue_id.order_queue_line_total_record
        order_total_queue = sum(self.magento_order_data_queue_id.mapped('order_queue_line_total_record'))
        for order_queue_line in self:
            magento_prod, inv_cust, del_cust, order, order_total_queue = sale_order_obj.create_magento_sales_order_ept(
                order_queue_line.magento_instance_id,
                order_queue_line,
                magento_prod,
                inv_cust,
                del_cust,
                order,
                order_total_queue
            )
            magento_order_common_log_lines = order_queue_line.magento_order_common_log_lines_ids.ids
            order_que_id = order_queue_line.magento_order_data_queue_id.id
            if order_que_id:
                if order_que_id not in order_queue_dict.keys():
                    order_queue_dict.update({order_que_id: magento_order_common_log_lines})
                else:
                    order_queue_dict[order_que_id] += magento_order_common_log_lines

        for queue, log_lines in order_queue_dict.items():
            queue_id = self.env['magento.order.data.queue.ept'].browse(queue)
            if log_lines:
                if queue_id.order_common_log_book_id:
                    existing = queue_id.order_common_log_book_id.log_lines.ids
                    queue_id.order_common_log_book_id.write({
                        "log_lines": [(6, 0, existing + log_lines)]
                    })
                else:
                    comman_log_id = self.env["common.log.book.ept"].create({
                        'type': 'import',
                        'module': 'magento_ept',
                        'magento_instance_id': queue_id.magento_instance_id.id,
                        'active': True,
                        'model_id': self.env["common.log.lines.ept"].get_model_id("sale.order"),
                        "log_lines": [(6, 0, log_lines)]
                    })
                    queue_id.order_common_log_book_id = comman_log_id
            query = """SELECT id FROM magento_order_data_queue_line_ept WHERE
             magento_order_data_queue_id = %s and state in ('draft','failed');""" % queue
            self._cr.execute(query)
            order_queue_line_ids = self._cr.fetchone()
            if order_queue_line_ids:
                queue_id.write({'state': "partially_completed"})
            else:
                queue_id.write({'state': "completed"})
        return True

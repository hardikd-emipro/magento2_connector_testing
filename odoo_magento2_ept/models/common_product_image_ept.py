#!/usr/bin/python3
"""
Describes methods to store images from Magento.
"""
from odoo import models, fields


class CommonProductImageEpt(models.Model):
    """
    store image from Magento
    Upload product images to ebay
    """
    _inherit = 'common.product.image.ept'

    magento_image_ids = fields.One2many(
        "magento.product.image",
        "odoo_image_id",
        'Magento Product Images',
        help="Magento Product Images"
    )

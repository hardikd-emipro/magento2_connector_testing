<?php
/**
 * Copyright © Magento, Inc. All rights reserved.
 * See COPYING.txt for license details.
 */

namespace Emipro\ApiChange\Api\Data;

/**
 * Finacial Status info interface.
 */
interface FinancialStatusInterface
{
    const IS_INVOICE = 'is_invoice';
    const IS_SHIPMENT = 'is_shipment';

    /**
     * Return is_invoice.
     *
     * @return boolean
     */
    public function getIsInvoice();

    /**
     * Set is_invoice.
     *
     * @param boolean $is_invoice
     * @return $boolean
     */
    public function setIsInvoice($is_invoice);

    /**
     * Return is_shipment.
     *
     * @return boolean
     */
    public function getIsShipment();

    /**
     * Set is_shipment.
     *
     * @param boolean $is_shipment
     * @return $boolean
     */
    public function setIsShipment($is_shipment);
}

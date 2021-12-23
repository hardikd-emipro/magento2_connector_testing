<?php
/**
 * Copyright © Magento, Inc. All rights reserved.
 * See COPYING.txt for license details.
 */

namespace Emipro\Apichange\Model;

use Emipro\Apichange\Api\Data\FinancialStatusInterface;

/**
 * Custom Option info .
 */
class FinancialStatus implements FinancialStatusInterface
{
    /**
     * {@inheritdoc}
     */
    public function getIsInvoice()
    {
        return $this->getData(self::IS_INVOICE);
    }

    /**
     * {@inheritdoc}
     */
    public function setIsInvoice($is_invoice)
    {
        return $this->setData(self::IS_INVOICE, $is_invoice);
    }

    /**
     * {@inheritdoc}
     */
    public function getIsShipment()
    {
        return $this->getData(self::IS_SHIPMENT);
    }

    /**
     * {@inheritdoc}
     */
    public function setIsShipment($is_shipment)
    {
        return $this->setData(self::IS_SHIPMENT, $is_shipment);
    }
}

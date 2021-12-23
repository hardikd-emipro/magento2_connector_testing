<?php
/**
 * Copyright © Magento, Inc. All rights reserved.
 * See COPYING.txt for license details.
 */

namespace Emipro\Apichange\Model;

use Emipro\Apichange\Api\Data\ApplyDiscountInfoInterface;

/**
 * Custom Option info .
 */
class ApplyDiscountInfo implements ApplyDiscountInfoInterface
{
    /**
     * {@inheritdoc}
     */
    public function getApplyDiscountOnPrices()
    {
        return $this->getData(self::APPLY_DISCOUNT_ON_PRICES);
    }

    /**
     * {@inheritdoc}
     */
    public function setApplyDiscountOnPrices($apply_discount_on_prices)
    {
        return $this->setData(self::APPLY_DISCOUNT_ON_PRICES, $apply_discount_on_prices);
    }
}

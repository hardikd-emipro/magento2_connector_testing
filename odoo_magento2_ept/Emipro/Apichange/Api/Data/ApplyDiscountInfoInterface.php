<?php
/**
 * Copyright © Magento, Inc. All rights reserved.
 * See COPYING.txt for license details.
 */

namespace Emipro\Apichange\Api\Data;

/**
 * Custom Option info interface.
 */
interface ApplyDiscountInfoInterface
{
    const APPLY_DISCOUNT_ON_PRICES = 'apply_discount_on_prices';

    /**
     * Return apply_discount_on_prices.
     *
     * @return string|null
     */
    public function getApplyDiscountOnPrices();

    /**
     * Set apply_discount_on_prices.
     *
     * @param string $apply_discount_on_prices
     * @return $string
     */
    public function setApplyDiscountOnPrices($apply_discount_on_prices);
}

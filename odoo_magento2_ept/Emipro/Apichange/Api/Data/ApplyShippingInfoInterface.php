<?php
/**
 * Copyright © Magento, Inc. All rights reserved.
 * See COPYING.txt for license details.
 */

namespace Emipro\Apichange\Api\Data;

/**
 * Custom Option info interface.
 */
interface ApplyShippingInfoInterface
{
    const APPLY_DISCOUNT_ON_PRICES = 'apply_shipping_on_prices';

    /**
     * Return apply_shipping_on_prices.
     *
     * @return string|null
     */
    public function getApplyShippingOnPrices();

    /**
     * Set apply_shipping_on_prices.
     *
     * @param string $apply_shipping_on_prices
     * @return $string
     */
    public function setApplyShippingOnPrices($apply_shipping_on_prices);
}

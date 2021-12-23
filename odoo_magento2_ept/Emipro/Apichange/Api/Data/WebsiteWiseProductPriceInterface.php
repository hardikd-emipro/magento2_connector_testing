<?php
/**
 * Copyright © Magento, Inc. All rights reserved.
 * See COPYING.txt for license details.
 */

namespace Emipro\Apichange\Api\Data;

/**
 * Custom Option info interface.
 */
interface WebsiteWiseProductPriceInterface
{
    const WEBSITE_WISE_PRODUCT_PRICE_DATA = 'website_wise_product_price_data';

    /**
     * Return website_wise_product_price_data.
     *
     * @return string|null
     */
    public function getWebsiteWiseProductPriceData();

    /**
     * Set website_wise_product_price_data.
     *
     * @param string $website_wise_product_price_data
     * @return $string
     */
    public function setWebsiteWiseProductPriceData($website_wise_product_price_data);
}

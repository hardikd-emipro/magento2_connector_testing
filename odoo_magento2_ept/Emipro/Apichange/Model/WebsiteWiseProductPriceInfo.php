<?php
/**
 * Copyright © Magento, Inc. All rights reserved.
 * See COPYING.txt for license details.
 */

namespace Emipro\Apichange\Model;

use Emipro\Apichange\Api\Data\WebsiteWiseProductPriceInterface;

/**
 * Custom Option info .
 */
class WebsiteWiseProductPriceInfo implements WebsiteWiseProductPriceInterface
{
    /**
     * {@inheritdoc}
     */
    public function getWebsiteWiseProductPriceData()
    {
        return $this->getData(self::WEBSITE_WISE_PRODUCT_PRICE_DATA);
    }

    /**
     * {@inheritdoc}
     */
    public function setWebsiteWiseProductPriceData($website_wise_product_price_data)
    {
        return $this->setData(self::WEBSITE_WISE_PRODUCT_PRICE_DATA, $website_wise_product_price_data);
    }
}

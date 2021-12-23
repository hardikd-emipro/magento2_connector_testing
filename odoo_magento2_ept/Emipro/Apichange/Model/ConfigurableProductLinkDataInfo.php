<?php
/**
 * Copyright © Magento, Inc. All rights reserved.
 * See COPYING.txt for license details.
 */

namespace Emipro\Apichange\Model;

use Emipro\Apichange\Api\Data\ConfigurableProductLinkDataInterface;

/**
 * Custom Option info .
 */
class ConfigurableProductLinkDataInfo extends \Magento\Framework\Model\AbstractExtensibleModel implements ConfigurableProductLinkDataInterface
{
    /**
     * {@inheritdoc}
     */
    public function getConfigurableProductLinkData()
    {
        return $this->getData(self::CONFIGURABLE_PRODUCT_LINK_DATA);
    }

    /**
     * {@inheritdoc}
     */
    public function setConfigurableProductLinkData($configurable_product_link_data)
    {
        return $this->setData(self::CONFIGURABLE_PRODUCT_LINK_DATA, $configurable_product_link_data);
    }
}

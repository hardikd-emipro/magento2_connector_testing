<?php
/**
 * Copyright © Magento, Inc. All rights reserved.
 * See COPYING.txt for license details.
 */

namespace Emipro\Apichange\Model;

use Emipro\Apichange\Api\Data\ConfigurableProductOptionsInterface;

/**
 * Custom Option info .
 */
class ConfigurableProductOptionsInfo implements ConfigurableProductOptionsInterface
{
    /**
     * {@inheritdoc}
     */
    public function getConfigurableProductOptionsData()
    {
        return $this->getData(self::CONFIGURABLE_PRODUCT_OPTIONS_DATA);
    }

    /**
     * {@inheritdoc}
     */
    public function setConfigurableProductOptionsData($configurable_product_options_data)
    {
        return $this->setData(self::CONFIGURABLE_PRODUCT_OPTIONS_DATA, $configurable_product_options_data);
    }
}

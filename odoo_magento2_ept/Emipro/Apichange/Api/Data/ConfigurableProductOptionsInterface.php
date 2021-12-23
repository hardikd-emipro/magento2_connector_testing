<?php
/**
 * Copyright © Magento, Inc. All rights reserved.
 * See COPYING.txt for license details.
 */

namespace Emipro\Apichange\Api\Data;

/**
 * Custom Option info interface.
 */
interface ConfigurableProductOptionsInterface
{
    const CONFIGURABLE_PRODUCT_OPTIONS_DATA = 'configurable_product_options_data';

    /**
     * Return configurable_product_options_data.
     *
     * @return string|null
     */
    public function getConfigurableProductOptionsData();

    /**
     * Set configurable_product_options_data.
     *
     * @param string $configurable_product_options_data
     * @return $string
     */
    public function setConfigurableProductOptionsData($configurable_product_options_data);
}

<?php
/**
 * Copyright © Magento, Inc. All rights reserved.
 * See COPYING.txt for license details.
 */

namespace Emipro\Apichange\Api\Data;

use Magento\Framework\Api\ExtensibleDataInterface;

/**
 * Custom Option info interface.
 * @api
 * @since 102.0.0
 */
interface ConfigurableProductLinkDataInterface extends ExtensibleDataInterface
{
    const CONFIGURABLE_PRODUCT_LINK_DATA = 'configurable_product_link_data';

    /**
     * Return configurable_product_link_data.
     *
     * @return string|null
     */
    public function getConfigurableProductLinkData();

    /**
     * Set configurable_product_link_data.
     *
     * @param string $configurable_product_link_data
     * @return $string
     */
    public function setConfigurableProductLinkData($configurable_product_link_data);
}

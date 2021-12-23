<?php
/**
 * Copyright © Magento, Inc. All rights reserved.
 * See COPYING.txt for license details.
 */

namespace Emipro\Apichange\Api\Data;

/**
 * Custom Option info interface.
 */
interface EptCustomOptionInfoInterface
{
    const EPT_OPTION_TITLE = 'ept_option_value';

    /**
     * Return ept_option_value.
     *
     * @return string|null
     */
    public function getEptOptionTitle();

    /**
     * Set ept_option_value.
     *
     * @param string $ept_option_value
     * @return $string
     */
    public function setEptOptionTitle($ept_option_value);
}

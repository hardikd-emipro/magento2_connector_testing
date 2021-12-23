<?php
/**
 * Copyright © Magento, Inc. All rights reserved.
 * See COPYING.txt for license details.
 */

namespace Emipro\Apichange\Model;

use Emipro\Apichange\Api\Data\EptCustomOptionInfoInterface;

/**
 * Custom Option info .
 */
class EptCustomOptionInfo implements EptCustomOptionInfoInterface
{
    /**
     * {@inheritdoc}
     */
    public function getEptOptionTitle()
    {
        return $this->getData(self::EPT_OPTION_TITLE);
    }

    /**
     * {@inheritdoc}
     */
    public function setEptOptionTitle($ept_option_value)
    {
        return $this->setData(self::EPT_OPTION_TITLE, $ept_option_value);
    }
}

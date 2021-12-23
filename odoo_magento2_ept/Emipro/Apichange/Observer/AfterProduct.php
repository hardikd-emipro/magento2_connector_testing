<?php
namespace Emipro\Apichange\Observer;

use Emipro\Apichange\Helper\Data as HelperData;
use Magento\Framework\Event\ObserverInterface;

class AfterProduct implements ObserverInterface
{
    public function __construct(HelperData $helper)
    {
        $this->helper = $helper;
    }
    public function execute(\Magento\Framework\Event\Observer $observer)
    {
        $product = $observer->getProduct();
        $api = 'web_magento_create_product';
        $this->helper->send($product, $api);
    }
}

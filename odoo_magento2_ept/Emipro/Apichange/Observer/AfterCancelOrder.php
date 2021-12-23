<?php
namespace Emipro\Apichange\Observer;

use Emipro\Apichange\Helper\Data as HelperData;
use Magento\Framework\Event\ObserverInterface;

class AfterCancelOrder implements ObserverInterface
{
    public function __construct(HelperData $helper)
    {
        $this->helper = $helper;
    }
    public function execute(\Magento\Framework\Event\Observer $observer)
    {
        $order = $observer->getOrder();
        $api = 'web_magento_order_cancel';
        $this->helper->send($order, $api);
    }
}

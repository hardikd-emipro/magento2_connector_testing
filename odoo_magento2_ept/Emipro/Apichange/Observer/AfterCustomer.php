<?php
namespace Emipro\Apichange\Observer;

use Emipro\Apichange\Helper\Data as HelperData;
use Magento\Framework\Event\ObserverInterface;

class AfterCustomer implements ObserverInterface
{
    public function __construct(HelperData $helper)
    {
        $this->helper = $helper;
    }

    public function execute(\Magento\Framework\Event\Observer $observer)
    {
        $customer = $observer->getCustomer();
        $api = 'web_magento_create_customer';
        $this->helper->send($customer, $api);
    }
}

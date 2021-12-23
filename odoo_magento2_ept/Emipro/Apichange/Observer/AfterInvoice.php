<?php
namespace Emipro\Apichange\Observer;

use Emipro\Apichange\Helper\Data as HelperData;
use Magento\Framework\Event\ObserverInterface;

class AfterInvoice implements ObserverInterface
{
    public function __construct(HelperData $helper)
    {
        $this->helper = $helper;
    }
    public function execute(\Magento\Framework\Event\Observer $observer)
    {
        $invoice = $observer->getInvoice();
        $api = 'web_magento_create_invoice';
        $this->helper->send($invoice, $api);
    }
}

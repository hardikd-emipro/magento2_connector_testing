<?php

namespace Emipro\Apichange\Helper;

class Data extends \Magento\Framework\App\Helper\AbstractHelper
{

    protected $scopeConfig;
    protected $storeManager;

    public function __construct(
        \Magento\Framework\App\Config\ScopeConfigInterface $scopeConfig,
        \Magento\Store\Model\StoreManagerInterface $storeManager
    ) {
        $this->scopeConfig = $scopeConfig;
        $this->storeManager = $storeManager;
    }

    public function send($data, $api)
    {
        /*echo "<pre>";
        print_r($data->getOrderId());
        exit;*/
        $enable = $this->getConfig('apichange/general/enabled');
        if ($enable == 0) {
            return;
        }

        $erpurl = $this->getConfig('apichange/urlconfig/url');
        $createcustomer = $this->getConfig('apichange/urlconfig/createcustomer');
        $placeorder = $this->getConfig('apichange/urlconfig/placeorder');
        $createproduct = $this->getConfig('apichange/urlconfig/createproduct');
        $createinvoice = $this->getConfig('apichange/urlconfig/createinvoice');
        $cancelorder = $this->getConfig('apichange/urlconfig/cancelorder');
        $url = $this->storeManager->getStore()->getBaseUrl(\Magento\Framework\UrlInterface::URL_TYPE_WEB);

        $parameter = array();
        if ($api == 'web_magento_create_customer' && $createcustomer) {
            $parameter = array('customer_id' => $data->getId(), 'url' => $url);
        }

        if ($api == 'web_magento_place_order' && $placeorder) {
            $parameter = array('order_id' => $data->getIncrementId(), 'url' => $url);
        }

        if ($api == 'web_magento_create_product' && $createproduct) {
            $parameter = array('product_id' => $data->getId(), 'sku' => $data->getSku(), 'url' => $url);
        }

        if ($api == 'web_magento_create_invoice' && $createinvoice) {
            $parameter = array('invoice_id' => $data->getId(), 'order_id' => $data->getOrderId(), 'url' => $url);
        }

        if ($api == 'web_magento_order_cancel' && $cancelorder) {
            $parameter = array('order_id' => $data->getId(), 'url' => $url);
        }

        if (!empty($parameter)) {
            $erpcontroller = $erpurl . '/' . $api;
            $ch = curl_init();
            curl_setopt($ch, CURLOPT_URL, $erpcontroller);
            curl_setopt($ch, CURLOPT_RETURNTRANSFER, 1);
            curl_setopt($ch, CURLOPT_POST, 1);
            curl_setopt($ch, CURLOPT_POSTFIELDS, $parameter);
            $result = curl_exec($ch);
            curl_close($ch);
        }
        return true;
    }
    public function getConfig($config_path)
    {
        return $this->scopeConfig->getValue(
            $config_path,
            \Magento\Store\Model\ScopeInterface::SCOPE_STORE
        );
    }
}

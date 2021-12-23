<?php

namespace Emipro\Apichange\Plugin\Api;

use Magento\Sales\Api\Data\OrderExtensionFactory;
use Magento\Sales\Api\Data\OrderSearchResultInterface;
use Magento\Sales\Api\OrderRepositoryInterface;

class OrderRepository
{
    const FIELD_EPT_OPTION_TITLE = 'ept_option_title';
    protected $scopeConfig;
    const XML_PATH_TAX_CALCULATION = 'tax/calculation/discount_tax';
    const XML_PATH_SHIPPING_TAX_CALCULATION = 'tax/calculation/shipping_includes_tax';
    /**
     * Order Extension Attributes Factory
     *
     * @var OrderExtensionFactory
     */
    protected $extensionFactory;

    /**
     * OrderRepositoryPlugin constructor
     *
     * @param OrderExtensionFactory $extensionFactory
     */
    public function __construct(
        OrderExtensionFactory $extensionFactory,
        \Magento\Framework\App\Config\ScopeConfigInterface $scopeConfig
    ) {
        $this->extensionFactory = $extensionFactory;
        $this->scopeConfig = $scopeConfig;
    }

    /**
     * Add "ept_option_title" extension attribute to order data object to make it accessible in API data
     *
     * @param OrderRepositoryInterface $subject
     * @param OrderSearchResultInterface $searchResult
     *
     * @return OrderSearchResultInterface
     */
    public function afterGetList(OrderRepositoryInterface $subject, OrderSearchResultInterface $searchResult)
    {
        foreach ($searchResult->getItems() as $order) {
            $itm = $order->getItems();
            $tax_calculation = null;
            $shipping_tax_calculation = null;
            if ($order->getBaseDiscountAmount() > 0 or $order->getBaseDiscountAmount() < 0) {
                if ($order->getBaseDiscountAmount()) {
                    $storeScope = \Magento\Store\Model\ScopeInterface::SCOPE_STORE;
                    $tax_calculation = $this->scopeConfig->getValue(self::XML_PATH_TAX_CALCULATION, $storeScope);
                    if ($tax_calculation == 0) {
                        $tax_calculation = 'excluding_tax';
                    } else {
                        $tax_calculation = 'including_tax';
                    }
                }
            }
            if ($order->getBaseShippingAmount() > 0 or $order->getBaseShippingAmount() < 0) {
                if ($order->getBaseShippingAmount()) {
                    $storeScope = \Magento\Store\Model\ScopeInterface::SCOPE_STORE;
                    $shipping_tax_calculation = $this->scopeConfig->getValue(self::XML_PATH_SHIPPING_TAX_CALCULATION, $storeScope);
                    if ($shipping_tax_calculation == 0) {
                        $shipping_tax_calculation = 'excluding_tax';
                    } else {
                        $shipping_tax_calculation = 'including_tax';
                    }
                }
            }
            $itm_custom_opt = [];
            foreach ($itm as $value) {
                if ($value->getProductType() == 'simple') {
                    if ($value->getParentItem()) {
                        $options = $value->getParentItem()->getProductOptions();
                    } else {
                        $options = $value->getProductOptions();
                    }
                    if (isset($options['options']) && !empty($options['options'])) {
                        $custom_opt = [];
                        $custom_opt['product_id'] = $value->getProductId();
                        $custom_opt['name'] = $value->getName();
                        $custom_opt['option_data'] = $options['options'];
                        array_push($itm_custom_opt, $custom_opt);
                    }
                }
            }
            $extensionAttributes = $order->getExtensionAttributes();
            $extensionAttributes = $extensionAttributes ? $extensionAttributes : $this->extensionFactory->create();
            $extensionAttributes->setEptOptionTitle($itm_custom_opt);
            if ($order->hasInvoices()) {
                $is_invoices = true;
            } else {
                $is_invoices = false;
            }
            if ($order->hasShipments()) {
                $is_shipments = true;
            } else {
                $is_shipments = false;
            }
            $extensionAttributes->setIsInvoice($is_invoices);
            $extensionAttributes->setIsShipment($is_shipments);
            $extensionAttributes->setApplyDiscountOnPrices($tax_calculation);
            $extensionAttributes->setApplyShippingOnPrices($shipping_tax_calculation);
            $order->setExtensionAttributes($extensionAttributes);
        }

        return $searchResult;
    }
}

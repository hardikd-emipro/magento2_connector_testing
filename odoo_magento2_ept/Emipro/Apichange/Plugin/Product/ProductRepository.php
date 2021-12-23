<?php
namespace Emipro\Apichange\Plugin\Product;

use Magento\Catalog\Api\ProductAttributeRepositoryInterface;
use Magento\Store\Model\StoreManagerInterface;

class ProductRepository
{
    private $productRepository;
    private $attribute;
    private $attributecollection;
    private $storeManager;
    private $product;
    protected $_scopeConfig;

    public function __construct(
        \Magento\Catalog\Api\ProductRepositoryInterface $productRepository,
        \Magento\Catalog\Model\ResourceModel\Eav\Attribute $attribute,
        \Magento\Eav\Model\ResourceModel\Entity\Attribute\Option\Collection $attributecollection,
        ProductAttributeRepositoryInterface $attributeRepository,
        StoreManagerInterface $storeManager,
        \Magento\Catalog\Model\Product $product,
        \Magento\Framework\App\Config\ScopeConfigInterface $scopeConfig
    ) {
        $this->productRepository = $productRepository;
        $this->attribute = $attribute;
        $this->attributecollection = $attributecollection;
        $this->attributeRepository = $attributeRepository;
        $this->storeManager = $storeManager;
        $this->product = $product;
        $this->_scopeConfig = $scopeConfig;
    }

    public function afterGet(\Magento\Catalog\Model\ProductRepository $subject, $result)
    {
        $extensionAttributes = $result->getExtensionAttributes();
        $extensionAttributes->setWebsiteIds($result->getWebsiteIds());
        $objectManager = \Magento\Framework\App\ObjectManager::getInstance();
        /*$writer = new \Zend\Log\Writer\Stream(BP . '/var/log/EMIPROTEST-web.log');
        $logger = new \Zend\Log\Logger();
        $logger->addWriter($writer);*/
        $all_website_price = [];
        foreach ($result->getWebsiteIds() as $web) {
            $website_price = [];
            $storeId = $this->storeManager->getWebsite($web)->getDefaultStore()->getId();
            $default_store_currency = $this->storeManager->getStore($storeId)->getDefaultCurrencyCode();
            $product = $this->product->setStoreId($storeId)->load($result->getId());
            $pro_final_price = $product->getFinalPrice();
            $website_price['website_id'] = $web;
            $website_price['product_price'] = $pro_final_price;
            $website_price['default_store_currency'] = $default_store_currency;
            array_push($all_website_price, $website_price);
            /*$logger->info(print_r($DEFAULT_CURRENCY, true));*/

        }
        $extensionAttributes->setWebsiteWiseProductPriceData($all_website_price);

        /*Add simple product's sku and product id*/
        $simple_product = [];
        $configurable_product_options = [];
        $all_opt_data = [];
        if ($result->getTypeId() == 'configurable') {
            $ConfigurableProductLinks = $extensionAttributes->getConfigurableProductLinks();
            if (count($ConfigurableProductLinks) > 0) {
                foreach ($ConfigurableProductLinks as $key => $value) {
                    $product = $this->productRepository->getById($value);
                    $product_data = [];
                    $product_data['simple_product_id'] = $value;
                    $product_data['simple_product_sku'] = $product->getSku();
                    $product_data['simple_product_list_price'] = $product->getPrice();
                    /*$product = $this->productRepository->getById($value);*/
                    $product_data['simple_product_attribute'] = [];
                    $_attributes = $result->getTypeInstance(true)->getConfigurableAttributes($result);
                    $simple_product_att = [];
                    foreach ($_attributes as $_attribute) {
                        $attributesPair = [];
                        $attributeId = (int) $_attribute->getAttributeId();
                        $attributeCode = $this->attributeRepository->get($attributeId);
                        if ($product->getCustomAttribute($attributeCode->getAttributeCode())) {
                            $att_value = $product->getCustomAttribute($attributeCode->getAttributeCode())->getValue();
                            $attr = $product->getResource()->getAttribute($attributeCode->getAttributeCode());
                            if ($attr->usesSource()) {
                                $optionText = $attr->getSource()->getOptionText($att_value);
                                $attributesPair['label'] = $attributeCode->getFrontendLabel();
                                $attributesPair['value'] = $optionText;
                                /*$logger->info(print_r($optionText, true));*/
                                array_push($simple_product_att, $attributesPair);
                            }
                        }
                    }
                    $product_data['simple_product_attribute'] = $simple_product_att;
                    if ($product_data['simple_product_attribute']) {
                        /*$logger->info(print_r($simple_product_att, true));*/
                        array_push($simple_product, $product_data);
                    }
                }
            }

            $ConfigurableProductOptions = $extensionAttributes->getConfigurableProductOptions();
            if (count($ConfigurableProductOptions) > 0) {
                foreach ($ConfigurableProductOptions as $key => $ProductOptions) {
                    $product_opt_data = [];
                    $product_opt_data['attribute_id'] = $ProductOptions->getAttributeId();
                    $attr = $this->attribute->load($ProductOptions->getAttributeId());
                    $product_opt_data['frontend_label'] = $attr->getFrontendLabel();
                    $product_opt_data['attribute_code'] = $attr->getAttributeCode();
                    $attribute = $result->getResource()->getAttribute($attr->getAttributeCode());
                    $product_option_value = [];
                    foreach ($ProductOptions->getValues() as $OptionValue) {
                        $optionId = $OptionValue->getValueIndex();
                        $attData = $result->getResource()->getAttribute($attr->getAttributeCode());
                        if ($attData->usesSource()) {
                            $optionText = $attData->getSource()->getOptionText($optionId);
                            if ($optionText) {
                                array_push($product_option_value, $optionText);
                            }
                        }
                    }
                    $product_opt_data['opt_values'] = $product_option_value;
                    /*$logger->info(print_r($product_opt_data, true));*/
                    array_push($all_opt_data, $product_opt_data);
                }
            }
        }
        $extensionAttributes->setConfigurableProductOptionsData($all_opt_data);
        $extensionAttributes->setConfigurableProductLinkData($simple_product);
        $result->setExtensionAttributes($extensionAttributes);
        return $result;
    }

    public function afterGetList(
        \Magento\Catalog\Api\ProductRepositoryInterface $subject,
        $products
    ) {
        foreach ($products->getItems() as $key => $product) {
            $this->afterGet($subject, $product);
        }
        return $products;
    }
}

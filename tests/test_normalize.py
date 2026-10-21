from pricechecker.normalize import edition_of, model_id, storage_of
from pricechecker.stores.webpage import parse
from pricechecker import affiliate


def test_model_id_strips_store_noise():
    assert model_id("Vivo X500 Pro Max 5G (Global Version) Dual SIM") == "vivo-x500-pro-max"
    assert model_id("Samsung Galaxy S26 Ultra 5G SM-S9480 Dual SIM") == "samsung-galaxy-s26-ultra"
    assert model_id("Samsung Galaxy S26+ 5G SM-S9470 Dual SIM") == "samsung-galaxy-s26-plus"
    assert model_id("HW Pura 80 Ultra (Global Version) Dual SIM") == "huawei-pura-80-ultra"
    assert model_id("Xiaomi 17 Ultra 5G (Leica Edition) Dual SIM") == "xiaomi-17-ultra-leica-edition"
    assert model_id("Xiaomi 17 Pro Max 16GB+512GB") == "xiaomi-17-pro-max"


def test_mobile_marvel_titles():
    assert model_id("Vivo X500 Pro Max Global Version") == "vivo-x500-pro-max"
    assert model_id("Honor Magic 9 Pro Max Chinese Version") == "honor-magic-9-pro-max"
    assert model_id("OPPO FIND X10 PRO MAX GLOBAL EDITION") == "oppo-find-x10-pro-max"
    assert edition_of("Honor Magic 9 Chinese Version") == "china"


def test_edition():
    assert edition_of("Oneplus 15 5G (Global Rom) Dual SIM") == "china"          # China phone, global software
    assert edition_of("Huawei Pura 80 Ultra (GLOBAL) - Black / 16GB/1TB (China Version)") == "china"
    assert edition_of("Xiaomi 17 Ultra 5G (Global Version) Dual SIM - 16+512GB") == "global"
    assert edition_of("HUAWEI Mate 90 Pro Dual SIM") == "china"


def test_storage():
    assert storage_of("12GB+256GB") == "12/256"
    assert storage_of("16GB + 1TB / Black") == "16/1024"
    assert storage_of("Black") == "base"
    assert storage_of("12+512GB") == "12/512"          # Wonda's format
    assert storage_of("16+1TB / White") == "16/1024"
    assert model_id("Xiaomi 17 Pro Max 12+512GB") == "xiaomi-17-pro-max"


def test_parse_jsonld_and_meta():
    ld = '<script type="application/ld+json">{"@type":"Product","name":"X","offers":{"price":"999.00","priceCurrency":"USD","availability":"https://schema.org/InStock"}}</script>'
    assert parse(ld) == {"name": "X", "price": 999.0, "currency": "USD", "available": True}
    meta = '<meta property="product:price:amount" content="1,049.50"><meta property="product:price:currency" content="EUR">'
    assert parse(meta)["price"] == 1049.5 and parse(meta)["currency"] == "EUR"


def test_affiliate_link():
    cfg = {"affiliate_link": "{url}{sep}ref={id}", "affiliate_id": "abc"}
    assert affiliate.link("https://s.com/p?variant=1", cfg) == "https://s.com/p?variant=1&ref=abc"
    assert affiliate.link("https://s.com/p", {**cfg, "affiliate_id": "YOUR_ID"}) == "https://s.com/p"


def test_giztop_titles():
    from pricechecker.stores.magento import split_title
    assert model_id("Vivo X300 Ultra Global") == "vivo-x300-ultra"
    assert edition_of("OPPO Find X9 Ultra Global") == "global"
    assert model_id("Motorola Moto Razr 70 Ultra") == "motorola-razr-70-ultra"
    assert storage_of("12GB - 256GB") == "12/256" and storage_of("16GB - 1TB") == "16/1024"
    assert split_title("OPPO Find X9 Ultra Global-Black-16GB - 1TB") == ("OPPO Find X9 Ultra Global", "16/1024")
    assert split_title("Honor Magic 8 Pro") == ("Honor Magic 8 Pro", None)


def test_tradingshenzhen_affiliate_link():
    import yaml
    from pathlib import Path
    cfg = yaml.safe_load((Path(__file__).parent.parent / "config/stores.yaml").read_text())["stores"]["tradingshenzhen"]
    assert affiliate.link("https://tradingshenzhen.com/en/gift-coupon/10-voucher", cfg) == \
        "https://tradingshenzhen.com/en/gift-coupon/10-voucher?affp=313618"
    assert affiliate.link("https://tradingshenzhen.com/en/p/123?id_product_attribute=7", cfg).endswith("?id_product_attribute=7&affp=313618")
    assert affiliate.link("https://tradingshenzhen.com/en/p/123#/color-black", cfg) == "https://tradingshenzhen.com/en/p/123?affp=313618#/color-black"


def test_wonda_affiliate_link():
    import yaml
    from pathlib import Path
    cfg = yaml.safe_load((Path(__file__).parent.parent / "config/stores.yaml").read_text())["stores"]["wonda"]
    assert affiliate.link("https://wondamobile.com/products/vivo-x300-ultra?variant=123", cfg) == \
        "https://wondamobile.com/products/vivo-x300-ultra?variant=123&ref=ivaylo_kirov"


def test_tradingshenzhen_titles():
    from pricechecker.stores.sitemap import slug_model, title_model
    assert model_id(title_model("Oppo Find N5 - 16GB/512GB - Foldable")) == "oppo-find-n5"
    assert model_id(title_model("Xiaomi 17 ULTRA - 16GB/512GB - 200 MP Leica Kamera")) == "xiaomi-17-ultra"
    assert model_id(title_model("Vivo X300 FE - 12GB/512GB - Global HK Edition - EU Warehouse")) == "vivo-x300-fe"
    assert edition_of("Vivo X300 FE - 12GB/512GB - Global HK Edition - EU Warehouse") == "global"
    assert slug_model("https://tradingshenzhen.com/en/oneplus-15-series/oneplus-15-16gb512gb-eu-warehouse") == "oneplus-15"


def test_pixels_are_never_china_editions():
    from pricechecker.normalize import edition_of, model_id
    assert edition_of("Google Pixel 11 Pro XL 16GB 512GB") == "global"
    assert edition_of("Pixel 11 Pro Fold 16GB/256GB (JP version)") == "global"
    assert model_id("Google Pixel 11 Pro XL 16GB 512GB") == "google-pixel-11-pro-xl"
    assert edition_of("Xiaomi 17 Ultra 16GB 512GB") == "china"          # unchanged for brands with China editions


def test_sub_brands_and_realme_gt_match_across_stores():
    from pricechecker.normalize import model_id
    assert model_id("vivo iQOO 15") == model_id("iQOO 15") == "iqoo-15"
    assert model_id("Xiaomi Redmi K90 Pro Max") == model_id("Redmi K90 Pro Max") == "redmi-k90-pro-max"
    assert model_id("Realme GT8 Pro") == model_id("Realme GT 8 Pro") == "realme-gt-8-pro"


def test_gomibo_urls():
    import re
    import yaml
    from pricechecker.stores.sitemap import variant_storage
    cfg = yaml.safe_load(open("config/stores.yaml"))["stores"]["gomibo"]
    match, model = re.compile(cfg["url_match"], re.I), re.compile(cfg["model_from_url"], re.I)
    assert match.search("https://www.gomibo.de/google-pixel-11-pro-eu/256gb-gruen")
    assert match.search("https://www.gomibo.de/samsung-galaxy-z-fold-8-eu/1tb-blau")
    assert not match.search("https://www.gomibo.de/google-pixel-11-pro-eu/vodafone")      # contract offers
    assert not match.search("https://www.gomibo.de/google-pixel-11-pro-eu")
    assert model_id(model.search("https://www.gomibo.de/google-pixel-11-pro-eu/256gb-gruen").group(1).replace("-", " ")) == "google-pixel-11-pro"
    assert model_id(model.search("https://www.gomibo.de/xiaomi-17-ultra/512gb-weiss").group(1).replace("-", " ")) == "xiaomi-17-ultra"
    assert variant_storage("https://www.gomibo.de/google-pixel-11-pro-eu/256gb-gruen", 12288) == "12/256"
    assert variant_storage("https://www.gomibo.de/google-pixel-11-pro-xl-eu/1tb-schwarz", 16384) == "16/1024"
    assert variant_storage("https://www.gomibo.de/google-pixel-11-pro-xl-eu/1tb-schwarz", None) == "base"
    assert re.search(cfg["ram_pattern"], r'{\"icon_type\":\"processor\",\"title\":\"12288 MB RAM\"}').group(1) == "12288"

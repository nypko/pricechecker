from . import feed, magento, official_api, shopify, sitemap, webpage

ADAPTERS = {
    "shopify": lambda name, cfg, catalog: shopify.fetch(name, cfg),
    "magento": lambda name, cfg, catalog: magento.fetch(name, cfg, catalog),
    "sitemap": lambda name, cfg, catalog: sitemap.fetch(name, cfg, catalog),
    "webpage": lambda name, cfg, catalog: webpage.fetch(name, cfg, catalog),
    "feed": lambda name, cfg, catalog: feed.fetch(name, cfg),
    "official_api": lambda name, cfg, catalog: official_api.fetch(name, cfg),
}

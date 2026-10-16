from dataclasses import dataclass, asdict


@dataclass
class Offer:
    """One price for one phone configuration at one store, as seen in one check."""
    store: str
    model_id: str      # normalized model key, e.g. "xiaomi-17-pro-max"
    edition: str       # "global" or "china"
    storage: str       # e.g. "16/512", or "base" when the store doesn't say
    title: str         # the store's own product title
    price: float
    currency: str      # ISO code as listed by the store
    available: bool
    url: str           # plain product URL; affiliate links are added at build time
    prices: dict | None = None  # the store's OWN prices per currency, e.g. {"USD": 1129, "EUR": 1019.77},
                                # when it sets them (Shopify Markets); otherwise the site converts at ECB rates

    @property
    def key(self) -> tuple:
        return (self.store, self.model_id, self.edition, self.storage)

    def to_dict(self) -> dict:
        return asdict(self)


class StoreNotConfigured(Exception):
    """Raised by a store that needs credentials or a feed URL that hasn't been set yet."""

import pytest

from pricechecker import fx, run, site, terms


@pytest.fixture(scope="session")
def site_build(tmp_path_factory):
    """The real site built once per session from the saved config and prices, offline, into a temp dir."""
    out = tmp_path_factory.mktemp("site") / "build"
    stores, catalog = run.load_config()
    mp = pytest.MonkeyPatch()
    mp.setattr(site, "OUT", out)
    try:
        site.build(catalog, stores, fx.cached(), terms.saved_status())
    finally:
        mp.undo()
    return out


@pytest.fixture(autouse=True)
def _no_saved_telegram_state(request, monkeypatch):
    """Tests that aren't `live` must not depend on data/telegram.json, which the hourly Telegram step rewrites: the
    drops list ("Posted to Telegram" marks) sees an empty state. A test checking the mark sets its own state."""
    if request.node.get_closest_marker("live") is None:
        from pricechecker.site.pages import drops
        monkeypatch.setattr(drops, "_telegram_state", dict)
